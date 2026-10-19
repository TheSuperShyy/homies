# -*- coding: utf-8 -*-
r"""Prove the Omni SIP address from a PC, the way Omni's PBX reaches it.

    python scripts/vapi_sip_probe.py --no-call    # safe: the right password is never sent
    python scripts/vapi_sip_probe.py              # PLACES A REAL CALL (seconds long); the owner's to run

Both talk SIP to sip.vapi.ai over UDP (then TCP, then TLS if UDP is silent) and
print status lines, X-Reason headers and the realm only. The login is
VAPI_SIP_USERNAME / VAPI_SIP_PASSWORD from .env, the same values
`vapi_sip.py --apply` put on the address and the reply to Omni carries. Nothing
here prints either value.

--no-call (four INVITEs, none can connect):
  1. an unknown address, no credentials     Vapi's 401 challenge, with the realm
  2. an unknown address, a wrong password   what Omni got on 19 Oct before the
                                            address existed: 403, "Invalid credentials"
  3. the real address, no credentials       the same challenge
  4. the real address, a wrong password     the same 403
  Vapi says "Invalid credentials" alike for a missing address and a wrong
  password, so this mode proves the SIP side is reachable and challenging; it
  cannot prove the password.

default (three INVITEs, the last one connects):
  1. an unknown address, no credentials
  2. the real address, a wrong password     expect the 403
  3. the real address, the .env login       the agent answers; BYE at once.
  A 200 on the third line is the proof of the password. Only this mode gives it,
  because Vapi never returns the password on a read.

Measured 19 Oct (--no-call): sip.vapi.ai is 44.229.228.186, UDP 5060 answers,
realm `sip.vapi.ai`, Digest MD5 with qop=auth.
"""

import hashlib
import io
import os
import random
import re
import socket
import ssl
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
HOST = "sip.vapi.ai"
REAL = "sip:homies-omni-208@sip.vapi.ai"
FAKE = "sip:homies-no-such-address-%s@sip.vapi.ai"


def env_value(name):
    m = re.search(r"^%s=(.*)$" % re.escape(name), io.open(ENV, encoding="utf-8").read(), re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def rnd(n=12):
    return "".join(random.choice("abcdef0123456789") for _ in range(n))


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 53))
    ip = s.getsockname()[0]
    s.close()
    return ip


COMPACT = {"v": "via", "f": "from", "t": "to", "i": "call-id", "m": "contact",
           "l": "content-length", "c": "content-type", "k": "supported"}


def parse(head, body):
    lines = head.split("\r\n")
    h = {}
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            k = k.strip().lower()
            h.setdefault(COMPACT.get(k, k), []).append(v.strip())
    return {"line": lines[0], "h": h, "body": body}


def h1(msg, name):
    v = msg["h"].get(name.lower())
    return v[0] if v else ""


class Link:
    """One transport to Vapi's SIP side; `recv` hands back one SIP message at a time."""

    def __init__(self, proto, port):
        self.proto, self.buf = proto, b""
        self.ip = socket.gethostbyname(HOST)
        if proto == "UDP":
            self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.s.bind(("0.0.0.0", 0))
            self.dst = (self.ip, port)
        else:
            raw = socket.create_connection((self.ip, port), timeout=8)
            if proto == "TLS":
                raw = ssl.create_default_context().wrap_socket(raw, server_hostname=HOST)
            self.s = raw
        self.lport = self.s.getsockname()[1]

    def send(self, text):
        data = text.encode("utf-8")
        if self.proto == "UDP":
            self.s.sendto(data, self.dst)
        else:
            self.s.sendall(data)

    def recv(self, timeout):
        end = time.time() + timeout
        while True:
            m = self._pop()
            if m:
                return m
            left = end - time.time()
            if left <= 0:
                return None
            self.s.settimeout(left)
            try:
                chunk = self.s.recvfrom(65535)[0] if self.proto == "UDP" else self.s.recv(65535)
            except (socket.timeout, TimeoutError):
                return None
            if not chunk:
                return None
            self.buf += chunk

    def _pop(self):
        if self.buf.strip() == b"":
            self.buf = b""
            return None
        i = self.buf.find(b"\r\n\r\n")
        if i < 0:
            return None
        head = self.buf[:i].decode("utf-8", "replace")
        m = re.search(r"^(?:Content-Length|l)\s*:\s*(\d+)", head, re.M | re.I)
        n = int(m.group(1)) if m else 0
        if len(self.buf) < i + 4 + n:
            return None
        body = self.buf[i + 4:i + 4 + n]
        self.buf = self.buf[i + 4 + n:]
        return parse(head, body)


def chal_params(chal):
    chal = re.sub(r"^\s*Digest\s+", "", chal, flags=re.I)
    p = {}
    for k, v in re.findall(r'(\w+)=("[^"]*"|[^,]+)', chal):
        p[k.lower()] = v.strip().strip('"')
    return p


def chal_line(chal):
    p = chal_params(chal)
    return "challenge: realm=%r algorithm=%s qop=%r" % (p.get("realm", ""), p.get("algorithm", "MD5").upper(), p.get("qop", ""))


def digest(chal, method, uri, user, pw):
    """The Authorization value for a Digest challenge (MD5, MD5-sess, qop=auth or none)."""
    p = chal_params(chal)
    realm, nonce = p.get("realm", ""), p.get("nonce", "")
    alg, qop = p.get("algorithm", "MD5").upper(), p.get("qop", "")
    cnonce, nc = rnd(16), "00000001"
    ha1 = md5("%s:%s:%s" % (user, realm, pw))
    if alg == "MD5-SESS":
        ha1 = md5("%s:%s:%s" % (ha1, nonce, cnonce))
    ha2 = md5("%s:%s" % (method, uri))
    if "auth" in [q.strip() for q in qop.split(",")]:
        resp = md5("%s:%s:%s:%s:auth:%s" % (ha1, nonce, nc, cnonce, ha2))
        tail = ', qop=auth, nc=%s, cnonce="%s"' % (nc, cnonce)
    else:
        resp = md5("%s:%s:%s" % (ha1, nonce, ha2))
        tail = ""
    out = ('Digest username="%s", realm="%s", nonce="%s", uri="%s", response="%s", algorithm=%s%s'
           % (user, realm, nonce, uri, resp, alg, tail))
    if p.get("opaque"):
        out += ', opaque="%s"' % p["opaque"]
    return out


class Call:
    def __init__(self, link, lip, uri):
        self.link, self.lip, self.uri = link, lip, uri
        self.callid = rnd(16) + "@" + lip
        self.ftag, self.cseq, self.branch = rnd(8), 0, None
        self.ttag, self.rcontact, self.routes = None, None, []

    def hdrs(self, method, ruri, branch, cseq, extra, to_tag):
        to = "<%s>" % self.uri + (";tag=" + to_tag if to_tag else "")
        lines = ["%s %s SIP/2.0" % (method, ruri),
                 "Via: SIP/2.0/%s %s:%d;branch=z9hG4bK%s;rport"
                 % (self.link.proto, self.lip, self.link.lport, branch),
                 "Max-Forwards: 70",
                 'From: "Homies probe" <sip:probe@%s>;tag=%s' % (self.lip, self.ftag),
                 "To: " + to,
                 "Call-ID: " + self.callid,
                 "CSeq: %d %s" % (cseq, method)]
        lines += ["Route: <%s>" % r for r in self.routes]
        lines += ["Contact: <sip:probe@%s:%d;transport=%s>"
                  % (self.lip, self.link.lport, self.link.proto.lower()),
                  "User-Agent: homies-sip-probe/1"] + list(extra)
        return "\r\n".join(lines) + "\r\n\r\n"

    def invite(self, auth=None):
        self.cseq += 1
        self.branch = rnd()
        now = int(time.time())
        sdp = ("v=0\r\no=- %d %d IN IP4 %s\r\ns=-\r\nc=IN IP4 %s\r\nt=0 0\r\n"
               "m=audio 4000 RTP/AVP 0 8 101\r\na=rtpmap:0 PCMU/8000\r\na=rtpmap:8 PCMA/8000\r\n"
               "a=rtpmap:101 telephone-event/8000\r\na=fmtp:101 0-16\r\na=sendrecv\r\n"
               % (now, now, self.lip, self.lip))
        extra = ["Allow: INVITE, ACK, CANCEL, BYE, OPTIONS",
                 "Content-Type: application/sdp", "Content-Length: %d" % len(sdp)]
        if auth:
            extra.insert(0, auth)
        self.link.send(self.hdrs("INVITE", self.uri, self.branch, self.cseq, extra, None) + sdp)

    def ack_fail(self, to_tag):
        self.link.send(self.hdrs("ACK", self.uri, self.branch, self.cseq, ["Content-Length: 0"], to_tag))

    def ack_ok(self):
        self.link.send(self.hdrs("ACK", self.rcontact or self.uri, rnd(), self.cseq,
                                 ["Content-Length: 0"], self.ttag))

    def bye(self):
        self.cseq += 1
        self.link.send(self.hdrs("BYE", self.rcontact or self.uri, rnd(), self.cseq,
                                 ["Content-Length: 0"], self.ttag))

    def cancel(self):
        self.link.send(self.hdrs("CANCEL", self.uri, self.branch, self.cseq, ["Content-Length: 0"], None))


def tag_of(v):
    m = re.search(r";tag=([^;>\s]+)", v)
    return m.group(1) if m else None


def uri_of(v):
    m = re.search(r"<([^>]+)>", v)
    return m.group(1) if m else v.split(";")[0].strip()


def answer_request(link, m):
    """200 OK to a request from the far side (its own BYE, say)."""
    print("   <- request %s" % m["line"].split(" ")[0])
    via = "\r\n".join("Via: " + v for v in m["h"].get("via", []))
    link.send("SIP/2.0 200 OK\r\n%s\r\nFrom: %s\r\nTo: %s\r\nCall-ID: %s\r\nCSeq: %s\r\n"
              "Content-Length: 0\r\n\r\n"
              % (via, h1(m, "From"), h1(m, "To"), h1(m, "Call-ID"), h1(m, "CSeq")))


def challenge_only(link, lip, uri, label, wait=8):
    """INVITE with no credentials; ACK the final answer; never answer the challenge."""
    c = Call(link, lip, uri)
    print("\n== %s" % label)
    c.invite()
    while True:
        m = link.recv(wait)
        if m is None:
            print("   nothing back within %ds" % wait)
            return "silent"
        if not m["line"].startswith("SIP/2.0"):
            answer_request(link, m)
            continue
        parts = m["line"].split(" ", 2)
        code, reason = int(parts[1]), (parts[2] if len(parts) > 2 else "")
        cs = h1(m, "CSeq").split()
        if not cs or int(cs[0]) != c.cseq:
            continue
        xr = h1(m, "X-Reason")
        print("   <- %d %s%s" % (code, reason, ("   X-Reason: " + xr) if xr else ""))
        if code < 200:
            continue
        c.ack_fail(tag_of(h1(m, "To")))
        if code in (401, 407):
            print("   " + chal_line(h1(m, "WWW-Authenticate" if code == 401 else "Proxy-Authenticate")))
        return code


def attempt(link, lip, uri, user, pw, label, wait=8):
    """One INVITE, answered to any Digest challenge once. Returns 'silent' or the final code."""
    c = Call(link, lip, uri)
    print("\n== %s" % label)
    c.invite()
    started = time.time()
    cancelled = False
    while True:
        m = link.recv(wait)
        if m is None:
            if cancelled:
                return "cancelled"
            print("   nothing back within %ds" % wait)
            return "silent"
        if not m["line"].startswith("SIP/2.0"):
            answer_request(link, m)
            continue
        parts = m["line"].split(" ", 2)
        code, reason = int(parts[1]), (parts[2] if len(parts) > 2 else "")
        cs = h1(m, "CSeq").split()
        if not cs or int(cs[0]) != c.cseq:
            continue  # a late or repeated answer to an earlier request
        method = cs[1] if len(cs) > 1 else "?"
        xr = h1(m, "X-Reason")
        print("   <- %d %s  (%s)%s" % (code, reason, method, ("   X-Reason: " + xr) if xr else ""))
        if method in ("BYE", "CANCEL"):
            if method == "BYE":
                return 200
            continue
        if code < 200:
            if time.time() - started > 12 and not cancelled:
                print("   still ringing after 12s: cancelling")
                c.cancel()
                cancelled = True
            continue
        to_tag = tag_of(h1(m, "To"))
        if code in (401, 407):
            c.ack_fail(to_tag)
            chal = h1(m, "WWW-Authenticate" if code == 401 else "Proxy-Authenticate")
            print("   " + chal_line(chal))
            c.invite(("Authorization: " if code == 401 else "Proxy-Authorization: ")
                     + digest(chal, "INVITE", uri, user, pw))
            started = time.time()
            continue
        if code >= 300:
            c.ack_fail(to_tag)
            return code
        # 200 OK to the INVITE: the agent answered. Hang up at once.
        c.ttag, c.rcontact = to_tag, uri_of(h1(m, "Contact"))
        c.routes = [uri_of(r) for r in reversed(m["h"].get("record-route", []))]
        c.ack_ok()
        print("   answered; hanging up")
        c.bye()
        t0 = time.time()
        while time.time() - t0 < 6:
            r = link.recv(3)
            if r and r["line"].startswith("SIP/2.0") and h1(r, "CSeq").endswith("BYE"):
                print("   <- %s  (BYE)" % r["line"][8:])
                break
        return 200


def main():
    args = sys.argv[1:]
    if args not in ([], ["--no-call"]):
        sys.exit("Usage: vapi_sip_probe.py [--no-call]")
    no_call = bool(args)
    user, pw = env_value("VAPI_SIP_USERNAME"), env_value("VAPI_SIP_PASSWORD")
    if not (user and pw):
        sys.exit("VAPI_SIP_USERNAME / VAPI_SIP_PASSWORD are not in .env (vapi_sip.py --apply makes them)")
    wrong = pw[:-1] + ("a" if pw[-1] != "a" else "b")   # same length, one character off

    lip = local_ip()
    print("local ip %s, %s -> %s" % (lip, HOST, socket.gethostbyname(HOST)))
    link = r1 = None
    for proto, port in (("UDP", 5060), ("TCP", 5060), ("TLS", 5061)):
        try:
            link = Link(proto, port)
        except OSError as e:
            print("%s %d: no connection (%s)" % (proto, port, e))
            continue
        print("\ntransport %s %d" % (proto, port))
        r1 = challenge_only(link, lip, FAKE % rnd(6), "1. an unknown address, no credentials")
        if r1 != "silent":
            break
        link = None
    if link is None:
        sys.exit("Vapi's SIP side did not answer on any transport; nothing proven.")

    if no_call:
        time.sleep(1)
        r2 = attempt(link, lip, FAKE % rnd(6), user, wrong, "2. an unknown address, a wrong password")
        time.sleep(1)
        r3 = challenge_only(link, lip, REAL, "3. the real address, no credentials")
        time.sleep(1)
        r4 = attempt(link, lip, REAL, user, wrong, "4. the real address, a wrong password")
        print("\nresult: unknown/no credentials -> %s | unknown/wrong -> %s | real/no credentials -> %s | real/wrong -> %s"
              % (r1, r2, r3, r4))
        print("No call was connected: the right password was never sent. Only the default mode proves it.")
        return 0

    time.sleep(1)
    r2 = attempt(link, lip, REAL, user, wrong, "2. the real address, a wrong password")
    time.sleep(1)
    r3 = attempt(link, lip, REAL, user, pw, "3. the real address, the .env login")
    print("\nresult: unknown address -> %s | wrong password -> %s | the .env login -> %s" % (r1, r2, r3))
    print("The .env login is proven only by a 200 on the third line (the agent answered).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
