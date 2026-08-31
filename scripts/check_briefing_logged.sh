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
# working tree now carries them or the follow-up commit does. Three escapes stop
# it firing at a session that has already complied:
#   1. Both files in the live change set — the ordinary case.
#   2. Both files in the LAST COMMIT. Committing them is what removes them from
#      the uncommitted set, so without this the guard punishes the fix.
#   3. Ten-minute cooldown, plus one nag per distinct change set.
# 2 and 3 were added 31 Aug after this fired four times running at a session
# whose work was committed and logged. Two sessions shared the checkout, the
# other one touched a file between every turn, and "one nag per change set" quietly
# stopped meaning anything because the set was never the same twice. None of the
# three weakens the 19 Aug case below: worklog-only commits leave the briefing
# files out of the working tree AND out of HEAD, so the block still lands.
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

# ALREADY LOGGED, AND THE COMMIT IS THE PROOF.
# Committing the briefing files is what moves them OUT of the uncommitted set
# this check reads, so a session that did exactly what the block asks looks
# identical to one that ignored it. If the last commit carries both files, the
# logging happened; whatever is still uncommitted is the next task, or another
# session's. The 19 Aug failure this guard was built for is untouched by this:
# four worklog-only commits in a row would leave HEAD without either file.
if [ "$scope" = "the uncommitted changes" ]; then
  head_files="$(git show --name-only --format= HEAD 2>/dev/null)"
  if printf '%s\n' "$head_files" | grep -qxF 'CONTEXT.md' &&
     printf '%s\n' "$head_files" | grep -qxF 'HANDOVER.md'; then
    exit 0
  fi
fi

# One nag per distinct change set. Without this, a turn that only answers a
# question would be blocked again by a commit that was already flagged.
marker="$(git rev-parse --git-dir)/briefing-nagged"
fingerprint="$(printf '%s' "$scope$changed" | git hash-object --stdin 2>/dev/null)"
if [ -n "$fingerprint" ] && [ -f "$marker" ] && grep -qxF "$fingerprint" "$marker" 2>/dev/null; then
  exit 0
fi

# AND ONE NAG PER TEN MINUTES, WHATEVER THE SET.
# The fingerprint above assumes the working tree only moves when this session
# moves it. On 31 Aug two sessions shared one checkout and that stopped being
# true: the other one added or committed a file between every turn, so the file
# list — and therefore the fingerprint — was new each time, and this fired four
# times running at a session whose own work was already committed and logged.
# A change set that keeps changing underneath you is not evidence that you failed
# to log anything, and a block you cannot satisfy is not a guard, it is a wall.
# The cost of being wrong in this direction is one late reminder. The cost in the
# other direction is a wall, and the model works around walls.
if [ -f "$marker" ]; then
  now="$(date +%s 2>/dev/null || echo 0)"
  last="$(stat -c %Y "$marker" 2>/dev/null || echo 0)"
  if [ "$now" -gt 0 ] && [ "$last" -gt 0 ] && [ "$((now - last))" -lt 600 ]; then
    exit 0
  fi
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
