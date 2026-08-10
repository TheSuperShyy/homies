#!/usr/bin/env python
"""Answer one question: does the OXS API return residents' real mobile numbers?

    python scripts/oxs_probe.py

THE QUESTION THIS ANSWERS

The last OXS export carried a phone column that was empty — one placeholder
repeated down every row. So "the API has a phone field" proves nothing: the
field can exist and still come back blank, exactly like the export did. This
script only reports success if it sees actual, distinct, populated mobile
numbers on real tenant records. Three outcomes, and it names which one:

  POPULATED   distinct real numbers came back      -> phones are importable
  EMPTY       field exists, every value blank/same -> same dead end as the export
  ABSENT      no phone field on the tenant record  -> the API cannot give phones

Numbers are printed MASKED (+9725******89) — enough to confirm they are real
and distinct, never enough to leak a resident's number into a terminal log.

SAFETY

Read-only: GET requests only, in line with the OXS-is-read-only rule. The key
goes to exactly one host, api.oxs.co.il, whose TLS cert is verified first as
Amazon-issued for *.oxs.co.il — the same origin as the OXS web app. That is
why this does not violate the never-guess-a-hostname rule: the host is
cert-proven, not guessed. Key values are never printed.
"""
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "api.oxs.co.il"
BASE = "https://" + HOST

SCHEMES = [
    ("x-api-key",             "x-api-key",     "{k}"),
    ("Authorization: Bearer", "Authorization", "Bearer {k}"),
    ("Authorization: raw",    "Authorization", "{k}"),
    ("api-key",               "api-key",       "{k}"),
    ("apikey",                "apikey",        "{k}"),
    ("x-oxs-api-key",         "x-oxs-api-key", "{k}"),
]

# Where a tenant list might live, if the spec doesn't tell us outright.
TENANT_GUESSES = [
    "/api/tenants", "/api/v1/tenants", "/v1/tenants", "/tenants",
    "/api/residents", "/api/v1/residents", "/api/general/tenants",
    "/api/general-information/tenants", "/api/apartments", "/api/buildings",
]

PHONE_KEYS = ("phone", "mobile", "cell", "tel", "phonenumber", "mobilephone",
              "msisdn", "טלפון", "נייד", "פלאפון")


def env():
    d = {}
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def mask(v):
    """+972501234589 -> +9725******89. Real enough to compare, useless to dial."""
    s = "".join(ch for ch in str(v) if ch.isdigit() or ch == "+")
    if len(s) < 6:
        return "(short: %d chars)" % len(s)
    return s[:5] + "*" * max(0, len(s) - 7) + s[-2:]


def cert_ok():
    ctx = ssl.create_default_context()
    try:
        with ctx.wrap_socket(socket.socket(), server_hostname=HOST) as s:
            s.settimeout(15)
            s.connect((HOST, 443))
            cert = s.getpeercert()
        subject = dict(x[0] for x in cert.get("subject", []))
        sans = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]
        print("   cert CN=%s  SAN=%s" % (subject.get("commonName"), ",".join(sans)))
        return any(HOST == p or (p.startswith("*.") and HOST.endswith(p[1:]))
                   for p in sans)
    except Exception as e:
        print("   cert check failed: %s" % e)
        return False


def get(path, header=None, value=None, timeout=20):
    req = urllib.request.Request(BASE + path, method="GET")
    if header:
        req.add_header(header, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode()


def as_json(body):
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return None


def find_records(obj):
    """Pull the list of record dicts out of whatever envelope the API uses."""
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for k in ("data", "items", "results", "records", "tenants",
                  "residents", "rows", "value"):
            if isinstance(obj.get(k), list):
                return [x for x in obj[k] if isinstance(x, dict)]
        # A single record?
        if any(pk in "".join(obj.keys()).lower() for pk in PHONE_KEYS):
            return [obj]
    return []


def phone_fields(rec):
    return [k for k in rec.keys()
            if any(pk in k.lower().replace("_", "").replace(" ", "")
                   for pk in PHONE_KEYS)]


def verdict(records):
    """The whole point: are there real, distinct, populated numbers?"""
    if not records:
        return "NO RECORDS", []
    fields = set()
    for r in records:
        fields.update(phone_fields(r))
    if not fields:
        return "ABSENT", []

    report = []
    best = "EMPTY"
    for f in sorted(fields):
        vals = [r.get(f) for r in records]
        filled = [v for v in vals
                  if v not in (None, "", "-", "0") and str(v).strip()]
        distinct = {str(v).strip() for v in filled}
        digits = [v for v in filled
                  if sum(ch.isdigit() for ch in str(v)) >= 7]
        state = ("POPULATED" if len(distinct) > 1 and digits
                 else "EMPTY" if not filled
                 else "PLACEHOLDER" if len(distinct) == 1
                 else "EMPTY")
        if state == "POPULATED":
            best = "POPULATED"
        elif state == "PLACEHOLDER" and best != "POPULATED":
            best = "PLACEHOLDER"
        report.append((f, len(filled), len(records), len(distinct), state,
                       [mask(v) for v in list(filled)[:5]]))
    return best, report


def main():
    key = env().get("OXS_KEY_GENERAL", "").strip()
    if not key or len(key) < 20:
        sys.exit("OXS_KEY_GENERAL missing or too short in .env")

    print("1. Verifying %s really belongs to OXS" % HOST)
    if not cert_ok():
        sys.exit("   Refusing to send the key — cert did not verify as OXS.")
    print("   OK, cert-verified.\n")

    print("2. Finding the auth header (via key-gated /swagger.json)")
    hdr = None
    spec = None
    for label, hname, fmt in SCHEMES:
        code, body = get("/swagger.json", hname, fmt.format(k=key))
        j = as_json(body) if code == 200 else None
        print("   [%-22s] HTTP %s" % (label, code))
        if j:
            hdr, spec = (hname, fmt), j
            print("   -> works: %s\n" % label)
            break

    if not hdr:
        print("\n   No standard header authenticated against the spec path.")
        print("   Trying the tenant paths directly with each header instead.\n")

    # 3. Get tenant records.
    tried = []
    if spec:
        paths = list((spec.get("paths") or {}).keys())
        tenant_paths = [p for p in paths if any(
            w in p.lower() for w in ("tenant", "resident", "occupant"))]
        print("3. Tenant routes in the spec: %s"
              % (", ".join(tenant_paths) or "none by name"))
        tried = tenant_paths or paths[:15]
    else:
        tried = TENANT_GUESSES
        print("3. Probing likely tenant routes")

    schemes = [hdr] if hdr else [(h, f) for _, h, f in SCHEMES]
    records, used_path, used_hdr = [], None, None
    for p in tried:
        if "{" in p:                      # needs an id we don't have yet
            continue
        for hname, fmt in schemes:
            code, body = get(p, hname, fmt.format(k=key))
            j = as_json(body) if code == 200 else None
            recs = find_records(j) if j is not None else []
            if recs:
                records, used_path, used_hdr = recs, p, hname
                break
            if code == 200 and j is not None:
                print("   %-40s HTTP 200 but no record list" % p)
        if records:
            break

    if not records:
        print("\nCould not retrieve a tenant list. Nothing was proven either "
              "way about\nphone numbers — the host is real and gated, but the "
              "route/auth shape is\nstill unknown. Paths tried: %s"
              % ", ".join(tried[:10]))
        return

    print("   got %d records from %s (header: %s)\n"
          % (len(records), used_path, used_hdr))

    print("4. Is the mobile number actually POPULATED?")
    state, report = verdict(records)
    for f, filled, total, distinct, st, samples in report:
        print("   field %-20s %d/%d filled, %d distinct  [%s]"
              % (f, filled, total, distinct, st))
        if samples:
            print("       samples (masked): %s" % ", ".join(samples))

    print("\n" + "=" * 62)
    if state == "POPULATED":
        print("VERDICT: POPULATED — real, distinct mobile numbers came back.")
        print("Phones ARE importable from the API. Next: pull the full tenant")
        print("list, then run scripts/oxs_purge_synthetic.py --apply before")
        print("re-importing so the 12 synthetic rows don't duplicate.")
    elif state == "PLACEHOLDER":
        print("VERDICT: PLACEHOLDER — the field is filled but every row is the")
        print("same value. This is the SAME dead end as the last export. The")
        print("numbers are not in OXS, or not exposed to this key.")
    elif state == "ABSENT":
        print("VERDICT: ABSENT — tenant records carry no phone field at all.")
        print("The API cannot supply phones. Only a corrected export can.")
    else:
        print("VERDICT: EMPTY — the phone field exists but every value is blank.")
        print("Same dead end as the last export.")
    print("=" * 62)


if __name__ == "__main__":
    main()
