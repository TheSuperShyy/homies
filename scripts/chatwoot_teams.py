# -*- coding: utf-8 -*-
"""Who a department mention reaches in Chatwoot, and seating people in a department.

    python scripts/chatwoot_teams.py                              # read only: each department, who is in it, who a mention reaches
    python scripts/chatwoot_teams.py --add management 2           # dry run: seat agent 2 in Management
    python scripts/chatwoot_teams.py --add management 2 --apply   # write it, then read it back
    python scripts/chatwoot_teams.py --remove management 2 --apply

Exits 1 when a department's mention reaches nobody on WhatsApp, so a health check
can run it.

WHY
A request for a manager, and every other matter past the bot, becomes a private
note in Chatwoot that @mentions a department's TEAM ("Homies — Hand to a person",
scripts/n8n_handover.py). The mention is the only alert: assigning the team
notifies nobody. Chatwoot expands a team mention to the team's members, and its
MentionService then keeps only the account's administrators and the members of
the conversation's inbox. So a mention reaches nobody, in silence, when

  - the team is empty, or
  - its people are seats that were never added to the inbox.

11 Nov, the owner: "make sure when a manager is requested ... it should mention
the people on the right department. but the bot is still the same just the
chatwoot side changes". Read that day: the bot sent a manager request to
Management in 5 real runs of 6 (the tester's chats of 8 and 10 Nov), and
Management, Collections and Operations had no members at all. Only Service had
one, the owner's own login, put there for the 3 Sep alert test. So the note was
written and nobody was told.

This script is the Chatwoot side of that: it shows who each department's mention
reaches, per inbox, and seats or unseats an agent. The bot and the sub-workflow
are not touched. The department ids here must equal the TEAMS table in
n8n_handover.py's "Decide the routing"; chatwoot_teams_test.py holds them
together.

Nothing here invites anybody. A new person is created in Chatwoot itself
(Settings, Agents), which emails them, and that is the owner's to do. Then:
add them to the WhatsApp inbox, and `--add <department> <their id> --apply`.

Admin token: CHATWOOT_API_TOKEN in .env. No email address is ever printed.
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import n8n_whatsapp as W  # noqa: E402

CW = "https://chat.srv1879140.hstgr.cloud"
ACCOUNT = 2
# The same four, with the same ids, as TEAMS in n8n_handover.py ("Decide the routing").
DEPARTMENTS = {"collections": 1, "operations": 2, "management": 3, "service": 4}
HEBREW = {"collections": "גבייה", "operations": "תפעול", "management": "הנהלה", "service": "שירות"}


# --------------------------------------------------------------------------
# The rule, with no network in it (chatwoot_teams_test.py).
# --------------------------------------------------------------------------
def reach(members, inbox_ids):
    """The members a team mention notifies on a conversation in one inbox.

    Chatwoot's MentionService intersects the mentioned users with the account's
    administrators plus that inbox's members (read in its source on 3 Sep, when
    administrators always worked and the first real seat got nothing).
    """
    return [m for m in members if m.get("role") == "administrator" or m.get("id") in inbox_ids]


def summary(members_by_department, inbox_ids):
    """One row per department, in the workflow's order, whatever Chatwoot returned."""
    rows = []
    for name in DEPARTMENTS:
        members = list(members_by_department.get(name) or [])
        reached = reach(members, inbox_ids)
        rows.append({"department": name, "members": members, "reached": reached,
                     "silent": not reached})
    return rows


def silent(rows):
    """The departments whose mention nobody hears."""
    return [r["department"] for r in rows if r["silent"]]


def plan(action, member_ids, agent_ids):
    """Which of `agent_ids` a write would really add or remove: each once, in order."""
    have, out = set(member_ids), []
    for a in agent_ids:
        if a in out:
            continue
        if (action == "add") != (a in have):
            out.append(a)
    return out


# --------------------------------------------------------------------------
# Chatwoot
# --------------------------------------------------------------------------
def cw(method, path, body=None):
    e = W.env()
    req = urllib.request.Request(
        CW + "/api/v1/accounts/%d%s" % (ACCOUNT, path), method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"api_access_token": e["CHATWOOT_API_TOKEN"].strip(),
                 "Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "homies/1.0"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read() or b"null")
    except urllib.error.HTTPError as ex:
        sys.exit("Chatwoot answered HTTP %s on %s %s\n%s"
                 % (ex.code, method, path, ex.read().decode(errors="replace")[:300]))


def load():
    """Agents, the four teams' members and each inbox's members, read live."""
    teams = {t["id"]: t for t in cw("GET", "/teams")}
    for name, tid in DEPARTMENTS.items():
        got = (teams.get(tid) or {}).get("name")
        if got != name:
            sys.exit("Team %d is %r in Chatwoot, and the workflow mentions it as %r. "
                     "Refusing to report on the wrong team." % (tid, got, name))
    agents = {a["id"]: a for a in cw("GET", "/agents")}
    members = {name: cw("GET", "/teams/%d/team_members" % tid) for name, tid in DEPARTMENTS.items()}
    voice = str(W.env().get("CHATWOOT_VOICE_INBOX_ID", "")).strip()
    inboxes = []
    for ib in (cw("GET", "/inboxes").get("payload") or []):
        ids = {m["id"] for m in (cw("GET", "/inbox_members/%d" % ib["id"]).get("payload") or [])}
        kind = ("WhatsApp" if ib.get("channel_type") == "Channel::Whatsapp"
                else "Voice" if str(ib["id"]) == voice else ib.get("name") or str(ib["id"]))
        inboxes.append({"id": ib["id"], "kind": kind, "member_ids": ids})
    inboxes.sort(key=lambda x: (x["kind"] != "WhatsApp", x["id"]))
    return agents, members, inboxes


def who(m):
    extra = [m.get("role") or "?"]
    if m.get("confirmed") is False:
        extra.append("has not confirmed the invite")
    return "%s (#%s, %s)" % (m.get("available_name") or m.get("name"), m.get("id"), ", ".join(extra))


def names(people):
    return ", ".join(who(m) for m in people) if people else "nobody"


def show(agents, members, inboxes):
    """Print every department and return the ones that are silent on WhatsApp."""
    print("Chatwoot account %d: %d people can log in." % (ACCOUNT, len(agents)))
    quiet = []
    for ib in inboxes:
        rows = summary(members, ib["member_ids"])
        if ib["kind"] == "WhatsApp":
            quiet = silent(rows)
        print("\nA mention on a %s conversation (inbox %d) reaches:" % (ib["kind"], ib["id"]))
        for r in rows:
            dropped = [m for m in r["members"] if m not in r["reached"]]
            line = "  %-12s %-6s %s" % (r["department"], HEBREW[r["department"]], names(r["reached"]))
            if r["silent"]:
                line += "   <-- the note is written and nobody is told"
            print(line)
            if dropped:
                print("  %-12s %-6s in the team but not in this inbox, so dropped: %s"
                      % ("", "", names(dropped)))
    return quiet


def change(action, department, agent_ids, apply):
    if department not in DEPARTMENTS:
        sys.exit("Unknown department %r. One of: %s." % (department, ", ".join(DEPARTMENTS)))
    agents, members, inboxes = load()
    for a in agent_ids:
        if a not in agents:
            sys.exit("No agent #%d on the account. People who can log in: %s."
                     % (a, names(list(agents.values()))))
    tid = DEPARTMENTS[department]
    todo = plan(action, [m["id"] for m in members[department]], agent_ids)
    verb = "seat in" if action == "add" else "take out of"
    if not todo:
        print("Nothing to do: %s is already as asked (%s)." % (department, names(members[department])))
        return
    print("%s %s: %s" % (verb, department, names([agents[a] for a in todo])))
    if action == "add":
        whatsapp = next((ib for ib in inboxes if ib["kind"] == "WhatsApp"), None)
        for a in todo:
            if whatsapp and not reach([agents[a]], whatsapp["member_ids"]):
                print("  NOTE: %s is not in the WhatsApp inbox, so a mention will not reach them "
                      "until they are added to it." % who(agents[a]))
    if not apply:
        print("Dry run. Re-run with --apply to write it.")
        return
    cw("POST" if action == "add" else "DELETE", "/teams/%d/team_members" % tid, {"user_ids": todo})
    back = cw("GET", "/teams/%d/team_members" % tid)
    print("read back: %s now has %s." % (department, names(back)))
    want = set(todo)
    got = {m["id"] for m in back}
    if (action == "add" and not want <= got) or (action == "remove" and want & got):
        sys.exit("The write did not hold. Look at the team in Chatwoot.")


def ids(args):
    try:
        return [int(a) for a in args]
    except ValueError:
        sys.exit("Agent ids are numbers, as the read-only run prints them (#2).")


def main():
    argv = [a for a in sys.argv[1:] if a != "--apply"]
    apply = "--apply" in sys.argv
    for action, flag in (("add", "--add"), ("remove", "--remove")):
        if flag in argv:
            rest = argv[argv.index(flag) + 1:]
            if len(rest) < 2:
                sys.exit("Usage: %s <department> <agent id> [<agent id> ...] [--apply]" % flag)
            return change(action, rest[0], ids(rest[1:]), apply)
    if argv:
        sys.exit("Unknown argument %r. See the top of this file." % argv[0])
    quiet = show(*load())
    if quiet:
        print("\nSILENT on WhatsApp: %s. A note that mentions them reaches nobody." % ", ".join(quiet))
        sys.exit(1)
    print("\nEvery department's mention reaches somebody on WhatsApp.")


if __name__ == "__main__":
    main()
