#!/usr/bin/env bash
#
# Refuse to call a task finished while the briefing files are stale.
#
# WHY THIS EXISTS
# The rule "log every task in CONTEXT.md and HANDOVER.md as well as the worklog"
# was given twice and broken anyway. On 19 Aug four tasks in a row went into
# docs/WORKLOG.md only, and one of them changed which Vapi account was live —
# both briefing files kept naming the retired account and its four retired
# assistant ids. A worklog entry records what happened; HANDOVER is what somebody
# acts on, and a stale one is worse than an empty one.
#
# A rule the model follows most of the time is not a guard. This is the guard.
#
# WHAT IT CHECKS
# Whichever change set is live — uncommitted work if there is any, otherwise the
# last commit — must touch CONTEXT.md and HANDOVER.md if it touches anything
# substantive. `.env` and the worklog do not count as substantive: the worklog is
# the thing that always gets updated, and .env is gitignored anyway.
#
# WHY IT CANNOT LOOP
# Every block is satisfiable in the same turn: edit the two files, and either the
# working tree now carries them or the follow-up commit does. And each distinct
# change set is only ever blocked ONCE — the fingerprint is remembered in
# .git/briefing-nagged — so a conversational turn after an already-flagged commit
# is never blocked a second time.
#
# Run it by hand any time:  bash scripts/check_briefing_logged.sh
set -u

cd "$(dirname "$0")/.." 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# Uncommitted work if there is any; otherwise the last commit. One path per
# line from all three commands, so paths containing spaces survive.
scope="the uncommitted changes"
changed="$( { git diff --name-only HEAD 2>/dev/null
              git ls-files --others --exclude-standard 2>/dev/null; } | sort -u )"
if [ -z "$changed" ]; then
  scope="the last commit"
  changed="$(git show --name-only --format= HEAD 2>/dev/null | sed '/^$/d')"
fi
[ -z "$changed" ] && exit 0

substantive=0
has_context=0
has_handover=0
has_worklog=0
first=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    CONTEXT.md)       has_context=1 ;;
    HANDOVER.md)      has_handover=1 ;;
    docs/WORKLOG.md)  has_worklog=1 ;;
    .env|.env.*)      ;;
    *) substantive=$((substantive + 1)); [ -z "$first" ] && first="$f" ;;
  esac
done <<CHANGED
$changed
CHANGED

# Nothing of consequence changed, or both briefing files are already in the set.
[ "$substantive" -eq 0 ] && exit 0
[ "$has_context" -eq 1 ] && [ "$has_handover" -eq 1 ] && exit 0

# One nag per distinct change set. Without this, a turn that only answers a
# question would be blocked again by a commit that was already flagged.
marker="$(git rev-parse --git-dir)/briefing-nagged"
fingerprint="$(printf '%s' "$scope$changed" | git hash-object --stdin 2>/dev/null)"
if [ -n "$fingerprint" ] && [ -f "$marker" ] && grep -qxF "$fingerprint" "$marker" 2>/dev/null; then
  exit 0
fi
[ -n "$fingerprint" ] && printf '%s\n' "$fingerprint" >> "$marker"

missing=""
[ "$has_context" -eq 0 ]  && missing="CONTEXT.md"
[ "$has_handover" -eq 0 ] && missing="${missing:+$missing and }HANDOVER.md"
worklog_note=""
[ "$has_worklog" -eq 0 ] && worklog_note=" docs/WORKLOG.md has no entry either."

more=""
[ "$substantive" -gt 1 ] && more=" and $((substantive - 1)) other file(s)"

# A Stop hook blocks by printing this JSON. The reason is read by the model.
cat <<JSON
{
  "decision": "block",
  "reason": "$missing not updated. $scope changed $first$more, and the briefing files were left behind.$worklog_note Before finishing: put the chronology in docs/WORKLOG.md, any standing decision in CONTEXT.md, and anything a fresh session would act on wrongly — ids, keys, which account is live, a defect opened or closed — in HANDOVER.md. Then commit all of them together. If one of the three genuinely needs nothing, still open it and say why in a line rather than skipping it. This is the rule that was given twice and missed anyway; see the note at the top of scripts/check_briefing_logged.sh.",
  "systemMessage": "Briefing files not updated - $missing"
}
JSON
