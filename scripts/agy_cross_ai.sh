#!/usr/bin/env bash
# Adapter for GSD's workflow.cross_ai_command: executes a mechanical GSD plan with an
# Antigravity (agy) agent and hands the result back as SUMMARY.md-compatible markdown.
#
# Contract (GSD execute-phase, step cross_ai_delegation): the plan prompt arrives on
# stdin, the command runs from the repo root, stdout is taken as the plan SUMMARY.md,
# any non-zero exit makes GSD offer retry / skip (Claude executor) / abort.
#
# Why it never commits: agy is observed to report SUCCESS on incomplete work
# (2026-10-09: 1 of 8 files), so its result is never trusted. The patch is applied to
# the WORKING TREE ONLY (new files as intent-to-add so `git diff` shows them), checked by
# sentinels and the quality gate, and left uncommitted for the Claude orchestrator to
# review and commit. agy itself is only ever run through scripts/agy_task.sh (systemd-run jail).
#
# Usage: scripts/agy_cross_ai.sh [--repo PATH] < prompt
# Env:   AGY_JOBS_DIR               job directory (same default as agy_task.sh)
#        AGY_CROSS_AI_AGENT_TIMEOUT per-attempt agent timeout, seconds (default 300)
#        AGY_GATE_CMD               TEST-ONLY: executable replacing `python3 scripts/gate.py`
#
# Exit codes: 0 ok; 2 usage/empty prompt/not a git repo; 1,3,4,5,6 propagated from
# agy_task.sh; 10 dirty tree outside .planning/; 11 no valid AGY_RESULT / not SUCCESS /
# no changes / patch missing; 12 patch touches a protected path; 13 a path declared in
# the prompt's files elements is not touched; 14 patch does not apply; 15 gate red (patch
# reverted); 16 revert failed (manual intervention); 143 SIGTERM/SIGINT/SIGHUP.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOBS_DIR="${AGY_JOBS_DIR:-/var/tmp/agy-jobs}"
AGENT_TIMEOUT="${AGY_CROSS_AI_AGENT_TIMEOUT:-300}"

say() { echo "agy_cross_ai: $*" >&2; }
fail() { local rc="$1"; shift; say "$*"; exit "$rc"; }

usage() {
  cat >&2 <<'EOF'
Использование: agy_cross_ai.sh [--repo PATH] < prompt
Адаптер workflow.cross_ai_command: план GSD со stdin выполняет агент Antigravity
в изоляции (scripts/agy_task.sh). Правки применяются только в рабочее дерево и
НЕ коммитятся; stdout — SUMMARY в markdown.
EOF
}

REPO=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) [ $# -ge 2 ] || { usage; exit 2; }; REPO="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage; fail 2 "неизвестный аргумент $1" ;;
  esac
done

WORK="$(mktemp -d)"
APPLIED=0
CHILD_PID=""
PATCH=""
TOP=""
JOB_ID=""
CREATED=()

cleanup_work() { rm -rf "${WORK:-}"; }
trap cleanup_work EXIT

# ---------- prompt, repo ----------
cat > "$WORK/prompt"
grep -q '[^[:space:]]' "$WORK/prompt" || fail 2 "пустой промпт на stdin"

TOP="$(git -C "${REPO:-.}" rev-parse --show-toplevel 2>/dev/null)" || fail 2 "${REPO:-текущая папка} — не git-репозиторий"
TOP="$(realpath "$TOP")"

# ---------- revert / signals ----------
revert_patch() {
  [ "$APPLIED" = 1 ] || return 0
  if ! git -C "$TOP" apply -R "$PATCH" 2>/dev/null; then
    say "КРИТИЧНО: не удалось откатить патч $PATCH — нужно вмешательство вручную (git -C $TOP apply -R $PATCH)"
    return 1
  fi
  if [ "${#CREATED[@]}" -gt 0 ]; then
    git -C "$TOP" reset -q -- "${CREATED[@]}" 2>/dev/null || true
  fi
  APPLIED=0
  return 0
}

on_signal() {
  trap '' TERM INT HUP
  [ -n "$CHILD_PID" ] && kill "$CHILD_PID" 2>/dev/null || true
  if [ "$APPLIED" = 1 ]; then
    say "получен сигнал завершения — откатываю патч агента"
    revert_patch || exit 16
  else
    say "получен сигнал завершения"
  fi
  exit 143
}
trap on_signal TERM INT HUP

# Run a command in the background and wait, so signals are handled immediately.
# Sets RUN_RC. Args: outfile errfile cmd...
run_bg() {
  local out="$1" err="$2"; shift 2
  "$@" < /dev/null > "$out" 2> "$err" &
  CHILD_PID=$!
  set +e
  wait "$CHILD_PID"
  RUN_RC=$?
  set -e
  CHILD_PID=""
}

# ---------- agent task ----------
{
  cat <<'EOF'
Это план GSD. Выполни все задачи по порядку.
- Правь только файлы, перечисленные в элементе files каждой задачи.
- НЕ запускай команды из verify/automated: в изолированной копии нет окружения, проверки выполнит проверяющий.
- Если шаг неоднозначен — оставь это место без изменений и опиши в финальном ответе.

ПЛАН:
EOF
  cat "$WORK/prompt"
} > "$WORK/task.md"

run_bg "$WORK/agy.out" "$WORK/agy.err" \
  "$SCRIPT_DIR/agy_task.sh" run --repo "$TOP" --mode edit --agent gsd-executor \
  --timeout "$AGENT_TIMEOUT" --task-file "$WORK/task.md"
AGY_RC="$RUN_RC"
# Relay the agent answer and wrapper messages into GSD's error log.
cat "$WORK/agy.out" >&2 || true
cat "$WORK/agy.err" >&2 || true

# Only the LAST line starting with "AGY_RESULT " counts (an agent answer may forge one).
RESULT_LINE="$(grep '^AGY_RESULT ' "$WORK/agy.out" | tail -n 1 || true)"
declare -A R=()
for tok in ${RESULT_LINE#AGY_RESULT }; do
  [[ "$tok" == *=* ]] && R["${tok%%=*}"]="${tok#*=}"
done
JOB_ID_RAW="${R[job]:-}"
if [[ "$JOB_ID_RAW" =~ ^[0-9]{8}-[0-9]{6}-[0-9]+$ ]]; then JOB_ID="$JOB_ID_RAW"; fi

if [ "$AGY_RC" -ne 0 ]; then
  [ -n "$JOB_ID" ] && say "задание агента: $JOB_ID"
  say "agy_task.sh завершился с кодом $AGY_RC; GSD предложит повторить, передать план исполнителю Claude или прервать"
  exit "$AGY_RC"
fi

if [ -z "$JOB_ID" ] || [ "${R[status]:-}" != SUCCESS ] || [ "${R[changed]:-}" != 1 ]; then
  fail 11 "агент сообщил об успехе, но правок нет (задание ${JOB_ID:--}, статус ${R[status]:--}, changed=${R[changed]:--}); GSD предложит повторить, передать план исполнителю Claude или прервать"
fi

JOB_DIR="$JOBS_DIR/$JOB_ID"
PATCH="$JOB_DIR/changes.patch"
[ -s "$PATCH" ] || fail 11 "патч агента отсутствует или пуст: $PATCH (задание $JOB_ID)"

# ---------- apply (working tree only) ----------
mapfile -t CREATED < <(git -C "$TOP" apply --summary "$PATCH" | sed -n 's/^ create mode [0-7]* //p')
APPLIED=1
if ! git -C "$TOP" apply --intent-to-add --whitespace=nowarn "$PATCH"; then
  APPLIED=0
  fail 14 "патч не применяется (задание $JOB_ID, $PATCH)"
fi

# ---------- gate ----------
if [ -n "${AGY_GATE_CMD:-}" ]; then GATE=("$AGY_GATE_CMD"); else GATE=(python3 "$SCRIPT_DIR/gate.py"); fi
GATE_LOG="$JOB_DIR/gate.log"
set +e
( cd "$SCRIPT_DIR/.." && exec "${GATE[@]}" ) < /dev/null > "$GATE_LOG" 2>&1 &
CHILD_PID=$!
wait "$CHILD_PID"
GATE_RC=$?
CHILD_PID=""
set -e
if [ "$GATE_RC" -ne 0 ]; then
  say "гейт качества красный (код $GATE_RC), последние строки:"
  tail -n 40 "$GATE_LOG" >&2 || true
  revert_patch || exit 16
  fail 15 "патч откачен (задание $JOB_ID); GSD предложит повторить, передать план исполнителю Claude или прервать"
fi
APPLIED=0

# ---------- SUMMARY ----------
python3 - "$TOP" "$PATCH" "$JOB_DIR" "$JOB_ID" "$GATE_LOG" \
  "${R[model]:--}" "${R[input_tokens]:-0}" "${R[output_tokens]:-0}" <<'PY'
import json, subprocess, sys

top, patch, job_dir, job_id, gate_log, model, tok_in, tok_out = sys.argv[1:9]


def git(*args):
    return subprocess.run(["git", "-C", top, *args], capture_output=True, text=True, check=True).stdout


created = [l.split(" ", 4)[-1] for l in git("apply", "--summary", patch).splitlines() if l.startswith(" create mode ")]
numstat = subprocess.run(["git", "-C", top, "apply", "--numstat", "-z", patch],
                         capture_output=True, check=True).stdout.split(b"\0")
touched, i = [], 0
while i < len(numstat):
    rec = numstat[i]
    i += 1
    parts = rec.split(b"\t", 2)
    if len(parts) < 3:
        continue
    if parts[2] == b"":
        touched += [numstat[i].decode(), numstat[i + 1].decode()]
        i += 2
    else:
        touched.append(parts[2].decode())
modified = [p for p in dict.fromkeys(touched) if p not in created]
stat = git("apply", "--stat", patch).rstrip()
try:
    response = (json.load(open(f"{job_dir}/result.json")).get("response") or "").strip()
except Exception:
    response = ""
if len(response) > 4000:
    response = response[:4000] + "\n…[обрезано]"
quoted = "\n".join("> " + l for l in response.splitlines()) or "> (пусто)"
all_paths = " ".join(dict.fromkeys(created + modified))

out = ["---", "status: complete", "executor: agy-cross-ai", f"agy_job: {job_id}", f"agy_model: {model}",
       f"agy_input_tokens: {tok_in}", f"agy_output_tokens: {tok_out}", "uncommitted: true", "key-files:"]
out += ["  created:"] + [f"    - {p}" for p in created] if created else ["  created: []"]
out += ["  modified:"] + [f"    - {p}" for p in modified] if modified else ["  modified: []"]
out += ["---", "", "# Исполнение плана агентом Antigravity (cross-AI)", "",
        "План выполнен агентом Antigravity в изолированной копии репозитория; патч применён к рабочему дереву "
        "после проверок адаптера и зелёного гейта качества. Коммита нет.", "",
        "## Изменённые файлы", "", "```", stat, "```", "",
        "## Проверка", "",
        f"Гейт качества (`python3 scripts/gate.py`) завершился с кодом 0. Журнал: {gate_log}", "",
        "## Ответ агента", "", quoted, "",
        "## ВНИМАНИЕ: правки НЕ ЗАКОММИЧЕНЫ", "",
        "changes are UNCOMMITTED — Claude orchestrator must review the diff and commit", "",
        "Что сделать дальше:", "",
        f"1. `git -C {top} diff` — прочитать правки целиком (новые файлы видны благодаря intent-to-add);",
        f"2. `git -C {top} add {all_paths}` и коммит по правилам проекта;",
        f"3. `scripts/agy_task.sh clean {job_id}` — удалить задание (патч: {patch}).", ""]
print("\n".join(out))
PY
