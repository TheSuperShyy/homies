"""Offline checks for compare() in sandbox_fingerprint.py (feature 19)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox_fingerprint import compare, phone_forms

BASE = {"since": "2026-10-26T00:00:00+00:00",
        "n8n": {"a": {"hash": "1", "updatedAt": "t", "active": True, "name": "x"}},
        "function": {"slug": "debt-tools", "version": 130, "updated_at": 1},
        "chatwoot": {"account": {"name": "CLIX", "locale": "en"}, "inboxes": [], "agent_bots": [],
                     "labels": [], "teams": [], "attributes": []},
        "persona_rows_since": {"עידו": {"requests": 0, "messages": 0, "interactions": 0}}}

def clone(**over):
    import copy
    d = copy.deepcopy(BASE); d.update(over); return d

assert compare(BASE, clone()) == [], "identical snapshots must compare clean"
assert compare(BASE, clone(function={"slug": "debt-tools", "version": 131, "updated_at": 2})), "a new live version is a change"
after = clone(); after["n8n"]["a"]["hash"] = "2"
assert compare(BASE, after), "an edited live workflow is a change"
after = clone(); after["persona_rows_since"]["עידו"]["requests"] = 1
assert any("requests" in d for d in compare(BASE, after)), "a persona row in a live table is a change"
# interactions.caller_phone holds both "+972…" (since October) and "972…" (older rows): count both
assert phone_forms("+972545360353") == "(+972545360353,972545360353)"
print("check_sandbox_fingerprint: 5/5 ok")
