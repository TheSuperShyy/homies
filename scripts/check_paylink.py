"""The payment link in chat -- the server half, without a handset.

    python scripts/check_paylink.py                       # the refusals, on test numbers
    python scripts/check_paylink.py --mint +972XXXXXXXXX  # ONE real debtor, named by the owner
    python scripts/check_paylink.py --mint +972... --expect several_apartments
    python scripts/check_paylink.py --mint +972... --keep # leave the rows for inspection

Posts straight to the Edge Function with the tool secret, the way the chat
bot's get_payment_link node does. The refusal set writes nothing and calls
OXS for nothing. The positive path needs a number that is on file, which no
test resident has -- so it is run once, with a debtor the owner names, and
never picks one itself.

WHAT --mint DOES, EXACTLY. One GET on OXS's finance read-only key, which mints
a link for that apartment (OXS mints one on every call; it is sent to nobody
and shows nothing the resident could not already see). One `interactions` row
under the TEST call id `wa:972599000002` -- the real number rides only in
variableValues.phone, which is the identity under test -- so the debtor's own
conversation is never touched. One `payment_links` row. Both deleted at the
end unless --keep. The link is never printed whole: host and length only.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n8n_whatsapp as W  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROBE_ID = "wa:972599000002"          # unallocated prefix; 032's purge pattern covers it
TEMP_PHONE = "+972599000004"         # a throwaway resident the probe creates and deletes
TEMP_BUILDING = "בדיקת-מערכת 1, תל אביב - יפו"
TEST_PREFIXES = ("+972599", "972599", "+972501234567", "972501234567")


def post(url, headers, body):
    req = urllib.request.Request(url, method="POST", data=json.dumps(body).encode("utf-8"),
                                 headers=dict(headers, **{"Content-Type": "application/json"}))
    try:
        raw = urllib.request.urlopen(req, timeout=90).read().decode("utf-8")
        return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        return {"__http": e.code, "__body": e.read().decode("utf-8")[:300]}


def masked(link):
    if not link:
        return "-"
    host = link.split("/")[2] if link.count("/") >= 2 else "?"
    return "%s/**** (%d chars)" % (host, len(link))


def main():
    e = W.env()
    base = e["SUPABASE_URL"].rstrip("/")
    fn = base + "/functions/v1/debt-tools"
    secret = e["TOOL_SECRET"].strip()
    key = e["SUPABASE_SERVICE_ROLE_KEY"].strip()
    rest = {"apikey": key, "Authorization": "Bearer " + key}
    args = sys.argv[1:]
    mint = args[args.index("--mint") + 1] if "--mint" in args else None
    expect = args[args.index("--expect") + 1] if "--expect" in args else None
    keep = "--keep" in args

    def tool(call_id, phone, fn_args, name="get_payment_link"):
        body = {"message": {"type": "tool-calls",
                            "call": {"id": call_id,
                                     "assistantOverrides": {"variableValues": {"phone": phone}}},
                            "toolCalls": [{"id": "probe-paylink", "type": "function",
                                           "function": {"name": name, "arguments": fn_args}}]}}
        r = post(fn, {"x-homies-secret": secret}, body)
        if "__http" in r:
            return r
        return json.loads(r["results"][0]["result"])

    def rest_get(path):
        req = urllib.request.Request(base + "/rest/v1/" + path, headers=dict(rest, Prefer="count=exact"))
        resp = urllib.request.urlopen(req, timeout=60)
        rows = json.loads(resp.read().decode("utf-8") or "[]")
        total = resp.headers.get("content-range", "/?").split("/")[-1]
        return rows, int(total) if total.isdigit() else None

    def count(path):
        return rest_get(path + ("&" if "?" in path else "?") + "limit=1")[1]

    def rest_del(path):
        req = urllib.request.Request(base + "/rest/v1/" + path, method="DELETE",
                                     headers=dict(rest, Prefer="return=representation"))
        try:
            return len(json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8") or "[]"))
        except urllib.error.HTTPError as ex:
            print("   cleanup", path.split("?")[0], "-> HTTP", ex.code, ex.read()[:120])
            return 0

    fails = 0

    def check(label, cond, got):
        nonlocal fails
        print(("  ok   " if cond else "  FAIL ") + label
              + ("" if cond else "  got: %s" % json.dumps(got, ensure_ascii=False)[:300]))
        if not cond:
            fails += 1

    links_before = count("payment_links?select=id")
    inter_before = count("interactions?select=id")

    # --- the refusals: nothing written, OXS never called ----------------------
    print("refusals:")
    r1 = tool("wa:972599000003", "972599000003", {"said": "בדיקה: רוצה לשלם"})
    check("1. unknown number -> number_not_on_file", r1.get("ok") and r1.get("found") is False
          and r1.get("reason") == "number_not_on_file", r1)
    # A resident whose building OXS has never heard of: on file, but no apartment
    # can be resolved, so no OXS call is made. Created here, deleted below.
    rest_del("residents?phone=eq.%s" % urllib.parse.quote(TEMP_PHONE, safe=""))
    post(base + "/rest/v1/residents", dict(rest, Prefer="return=minimal"),
         {"phone": TEMP_PHONE, "full_name": "בדיקת-מערכת", "building": TEMP_BUILDING, "unit": "1"})
    try:
        r2 = tool("wa:" + TEMP_PHONE.lstrip("+"), TEMP_PHONE.lstrip("+"), {"said": "בדיקה: רוצה לשלם"})
    finally:
        rest_del("residents?phone=eq.%s" % urllib.parse.quote(TEMP_PHONE, safe=""))
    check("2. on file but no OXS apartment -> apartment_unknown", r2.get("found") is False
          and r2.get("reason") == "apartment_unknown", r2)
    r3 = tool("probe-paylink-1", "972599000003", {"said": "x"})
    check("3. not a chat -> whatsapp only", r3.get("ok") is False and "whatsapp" in str(r3.get("error")), r3)
    r4 = tool("wa:972599000003", "972599000003",
              {"said": "x", "phone": "+972599000009", "apartment_id": "5f8d0a1b2c3d4e5f60718293"})
    check("4. arguments are never identity", r4.get("found") is False
          and r4.get("reason") == "number_not_on_file", r4)
    check("5. refusals wrote nothing", count("payment_links?select=id") == links_before
          and count("interactions?select=id") == inter_before, {})

    if not mint:
        print("\n%s (refusals only; --mint +972... for the positive path)"
              % ("all 5 passed" if not fails else "%d FAILED" % fails))
        sys.exit(1 if fails else 0)

    # --- the positive path, one real debtor --------------------------------------
    if mint.startswith(TEST_PREFIXES):
        sys.exit("--mint needs a real number on file; test prefixes are refused.")
    bare = mint.lstrip("+")
    print("\npositive path for %s...%s:" % (mint[:5], mint[-3:]))
    res, _ = rest_get("residents?select=id,building,unit,oxs_ref&phone=eq.%s" % urllib.parse.quote(mint, safe=""))
    if not res:
        sys.exit("that number is not in residents; nothing to mint")
    r = res[0]
    ch, _ = rest_get("charges?select=unit&status=eq.unpaid&resident_id=eq.%s" % r["id"])
    units = sorted({str(c["unit"] or "").strip() for c in ch} - {""})
    print("   resident %s  building %s  unpaid units %s" % (r["id"][:8], r["building"], units or [r["unit"]]))
    if len(units) > 1 and expect != "several_apartments":
        sys.exit("that resident owes on %d apartments; pass --expect several_apartments to test the refusal" % len(units))
    bld, _ = rest_get("buildings?select=id&address=eq.%s" % urllib.parse.quote(r["building"] or "", safe=""))
    unit = units[0] if units else str(r["unit"] or "").strip()
    apts, _ = rest_get("apartments?select=id,number&building_id=eq.%s&number=eq.%s"
                       % (bld[0]["id"] if bld else "-", urllib.parse.quote(unit, safe="")))
    print("   building rows %d, apartment rows for unit %r: %d" % (len(bld), unit, len(apts)))

    iid = None
    try:
        p1 = tool(PROBE_ID, bare, {"said": "בדיקה: רוצה לשלם את ועד הבית"})
        if expect:
            check("6. expected refusal %s" % expect, p1.get("found") is False and p1.get("reason") == expect, p1)
            check("7. refusal wrote nothing", count("payment_links?select=id") == links_before, {})
        else:
            link = p1.get("link") or ""
            check("6. found:true with an https link", p1.get("ok") and p1.get("found") is True
                  and link.startswith("https://"), dict(p1, link=masked(link)))
            check("7. building and unit match the record", p1.get("building") == r["building"]
                  and str(p1.get("apartment")) == unit, {"building": p1.get("building"), "apartment": p1.get("apartment")})
            rows, _ = rest_get("payment_links?select=id,interaction_id,channel,apartment_id,payer_id,link,status,note"
                               "&resident_id=eq.%s&channel=eq.whatsapp&order=created_at.desc&limit=2" % r["id"])
            row = rows[0] if rows else {}
            iid = row.get("interaction_id")
            check("8. one chat row, linked to the probe interaction, link stored verbatim",
                  len(rows) == 1 and row.get("status") == "sent" and row.get("link") == link
                  and row.get("apartment_id") == (apts[0]["id"] if apts else None)
                  and row.get("note") == "בדיקה: רוצה לשלם את ועד הבית",
                  {k: (masked(v) if k == "link" else v) for k, v in row.items()})
            inter, _ = rest_get("interactions?select=id,external_call_id,caller_phone&id=eq.%s" % (iid or "-"))
            check("9. the interaction is the probe's, not the debtor's",
                  inter and inter[0]["external_call_id"] == PROBE_ID, inter)
            p2 = tool(PROBE_ID, bare, {"said": "שוב"})
            rows2, _ = rest_get("payment_links?select=id&resident_id=eq.%s&channel=eq.whatsapp" % r["id"])
            check("10. asked again: reused, same link, still one row", p2.get("reused") is True
                  and p2.get("link") == link and len(rows2) == 1, dict(p2, link=masked(p2.get("link"))))
            print("   payer_id == residents.oxs_ref: %s   (link %s)"
                  % (row.get("payer_id") == r.get("oxs_ref"), masked(link)))
            check("11. nothing else was written", count("requests?select=id") is not None
                  and count("interactions?select=id") == inter_before + 1, {})
    finally:
        if keep:
            print("cleanup skipped (--keep)")
        else:
            print("cleanup:")
            n_links = rest_del("payment_links?interaction_id=eq.%s" % iid) if iid else 0
            n_int = rest_del("interactions?external_call_id=eq.%s" % urllib.parse.quote(PROBE_ID, safe=""))
            print("   payment_links %d, interactions %d" % (n_links, n_int))

    print("\n%s" % ("all passed" if not fails else "%d FAILED" % fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
