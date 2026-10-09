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
# the WORKING TREE ONLY (new files marked with `git add -N` so `git diff` shows them), checked by
# sentinels and the quality gate, and left uncommitted for the Claude orchestrator to
# review and commit. agy itself is only ever run through scripts/agy_task.sh (systemd-run jail).
#
# Usage: scripts/agy_cross_ai.sh [--repo PATH] < prompt
# Env:   AGY_JOBS_DIR               job directory (same default as agy_task.sh)
#        AGY_CROSS_AI_AGENT_TIMEOUT per-attempt agent timeout, seconds (default 300)
#        AGY_GATE_CMD               TEST-ONLY: executable replacing `python3 scripts/gate.py`
#
# Quality gate selection (GATE-05, D-15), first match wins:
#   1) AGY_GATE_CMD (tests only), run from the adapter's own repo root;
#   2) scripts/gate.py in the root of the --repo target: the target repository's own gate,
#      run with python3 from that root (assistant-core has one since its phase 1);
#   3) otherwise the chat-app gate next to this adapter, run from the chat-app root.
# Why the target's gate can be trusted: scripts/gate.py is in PROTECTED, so a patch that
# creates, changes or deletes it is refused with exit 12 before it is applied.
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

# ---------- python helper (path analysis) ----------
cat > "$WORK/helper.py" <<'PY'
import posixpath, re, subprocess, sys

PROTECTED = (".planning/", ".agents/", ".claude/", ".agy/", ".githooks/", ".git/", ".importlinter",
             "scripts/gate.py", "scripts/agy_task.sh", "scripts/agy_cross_ai.sh", "scripts/security_shield.py")


def git_bytes(top, *args):
    return subprocess.run(["git", "-C", top, *args], capture_output=True, check=True).stdout


def dirty(top):
    """Paths with changes outside .planning/ (tracked or untracked)."""
    parts = git_bytes(top, "status", "--porcelain=v1", "-z", "--untracked-files=all").split(b"\0")
    i, out = 0, []
    while i < len(parts):
        rec = parts[i]
        i += 1
        if len(rec) < 4:
            continue
        paths = [rec[3:].decode(errors="replace")]
        if rec[0:1] in (b"R", b"C") or rec[1:2] in (b"R", b"C"):
            paths.append(parts[i].decode(errors="replace"))
            i += 1
        if any(not p.startswith(".planning/") for p in paths):
            out += paths
    return out


def touched(top, patch):
    parts = git_bytes(top, "apply", "--numstat", "-z", patch).split(b"\0")
    i, out = 0, []
    while i < len(parts):
        rec = parts[i]
        i += 1
        f = rec.split(b"\t", 2)
        if len(f) < 3:
            continue
        if f[2] == b"":
            out += [parts[i].decode(), parts[i + 1].decode()]
            i += 2
        else:
            out.append(f[2].decode())
    return [posixpath.normpath(p) for p in dict.fromkeys(out)]


def is_protected(path):
    for pref in PROTECTED:
        if pref.endswith("/"):
            if path == pref[:-1] or path.startswith(pref):
                return True
        elif path == pref or path.startswith(pref + "/"):
            return True
    return False


def declared(prompt_file, top):
    text = open(prompt_file, errors="replace").read()
    blocks = re.findall(r"<files>(.*?)</files>", text, re.DOTALL)
    if not blocks:
        return None
    result = []
    for block in blocks:
        for tok in re.split(r"[,\n]", block):
            tok = tok.strip().strip("`").strip()
            tok = re.sub(r"^[-*]\s+", "", tok).strip().strip("`").strip()
            tok = re.sub(r"\s*\(.*\)\s*$", "", tok).strip().strip("`").strip()
            if not tok or "*" in tok or ("/" not in tok and "." not in tok):
                continue
            if tok.startswith("/"):
                if tok == top or tok.startswith(top + "/"):
                    tok = tok[len(top):].lstrip("/")
                else:
                    print(f"предупреждение: путь {tok} вне репозитория — не проверяется", file=sys.stderr)
                    continue
            keep_dir = tok.endswith("/")
            tok = posixpath.normpath(tok) + ("/" if keep_dir else "")
            result.append(tok)
    return list(dict.fromkeys(result))


cmd = sys.argv[1]
if cmd == "dirty":
    sys.stdout.write("\n".join(dirty(sys.argv[2])))
elif cmd == "protected":
    sys.stdout.write("\n".join(p for p in touched(sys.argv[2], sys.argv[3]) if is_protected(p)))
elif cmd == "missing":
    top, patch, prompt = sys.argv[2:5]
    decl = declared(prompt, top)
    if decl is None:
        print("предупреждение: в плане нет элементов files — полнота правок не проверяется", file=sys.stderr)
    else:
        t = touched(top, patch)
        miss = [d for d in decl if not any(p == d.rstrip("/") or p.startswith(d if d.endswith("/") else d + "/")
                                            for p in t)]
        sys.stdout.write("\n".join(miss))
PY

list_dirty() { python3 "$WORK/helper.py" dirty "$TOP"; }

DIRTY="$(list_dirty)"
if [ -n "$DIRTY" ]; then
  say "рабочее дерево изменено вне .planning/ — патч агента не должен смешиваться с чужими правками. Закоммить или убери:"
  sed 's/^/  /' <<<"$DIRTY" >&2
  fail 10 "отказ: грязное дерево; после коммита GSD предложит повторить"
fi

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
  local left; left="$(list_dirty 2>/dev/null || true)"
  if [ -n "$left" ]; then
    say "предупреждение: после отката в дереве остались изменения вне .planning/:"
    sed 's/^/  /' <<<"$left" >&2
  fi
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
  [ -n "$JOB_ID" ] && say "задание агента: $JOB_ID (если сохранено: scripts/agy_task.sh diff $JOB_ID / clean $JOB_ID)"
  say "agy_task.sh завершился с кодом $AGY_RC; GSD предложит повторить, передать план исполнителю Claude или прервать"
  exit "$AGY_RC"
fi

if [ -z "$JOB_ID" ] || [ "${R[status]:-}" != SUCCESS ] || [ "${R[changed]:-}" != 1 ]; then
  fail 11 "агент сообщил об успехе, но правок нет (задание ${JOB_ID:--}, статус ${R[status]:--}, changed=${R[changed]:--}); GSD предложит повторить, передать план исполнителю Claude или прервать"
fi

JOB_DIR="$JOBS_DIR/$JOB_ID"
PATCH="$JOB_DIR/changes.patch"
[ -s "$PATCH" ] || fail 11 "патч агента отсутствует или пуст: $PATCH (задание $JOB_ID)"

HINT="GSD предложит повторить, передать план исполнителю Claude или прервать"
INSPECT="осмотр: scripts/agy_task.sh diff $JOB_ID ; удаление: scripts/agy_task.sh clean $JOB_ID"

# ---------- sentinels on the validated patch (nothing applied yet) ----------
PROTECTED_HIT="$(python3 "$WORK/helper.py" protected "$TOP" "$PATCH")"
if [ -n "$PROTECTED_HIT" ]; then
  say "патч агента трогает защищённые пути:"
  sed 's/^/  /' <<<"$PROTECTED_HIT" >&2
  fail 12 "отказ (задание $JOB_ID); $INSPECT; $HINT"
fi

MISSING="$(python3 "$WORK/helper.py" missing "$TOP" "$PATCH" "$WORK/prompt")"
if [ -n "$MISSING" ]; then
  say "агент не тронул объявленные в плане файлы (известный сбой: SUCCESS при неполной работе):"
  sed 's/^/  /' <<<"$MISSING" >&2
  fail 13 "неполное выполнение (задание $JOB_ID); $INSPECT; $HINT"
fi

if ! git -C "$TOP" apply --check --whitespace=nowarn "$PATCH" 2>"$WORK/check.err"; then
  cat "$WORK/check.err" >&2
  fail 14 "патч не применяется (задание $JOB_ID, $PATCH); $INSPECT; $HINT"
fi

# ---------- apply (working tree only) ----------
# Plain `git apply` + `git add -N` for created files. NOT `git apply --intent-to-add`:
# in git 2.43 it rewrites the index with only the patched files, dropping all other entries.
mapfile -t CREATED < <(git -C "$TOP" apply --summary "$PATCH" | sed -n 's/^ create mode [0-7]* //p')
APPLIED=1
if ! git -C "$TOP" apply --whitespace=nowarn "$PATCH"; then
  APPLIED=0  # git apply is atomic: nothing was changed
  fail 14 "патч не применился (задание $JOB_ID, $PATCH); $INSPECT; $HINT"
fi
if [ "${#CREATED[@]}" -gt 0 ]; then
  git -C "$TOP" add -N -- "${CREATED[@]}" || { revert_patch || exit 16; fail 14 "не удалось пометить новые файлы intent-to-add (задание $JOB_ID)"; }
fi

# ---------- gate ----------
if [ -n "${AGY_GATE_CMD:-}" ]; then
  GATE=("$AGY_GATE_CMD"); GATE_DIR="$SCRIPT_DIR/.."
elif [ -f "$TOP/scripts/gate.py" ]; then
  GATE=(python3 "$TOP/scripts/gate.py"); GATE_DIR="$TOP"
else
  GATE=(python3 "$SCRIPT_DIR/gate.py"); GATE_DIR="$SCRIPT_DIR/.."
fi
say "гейт качества: ${GATE[*]} (каталог $GATE_DIR)"
GATE_LOG="$JOB_DIR/gate.log"
set +e
( cd "$GATE_DIR" && exec "${GATE[@]}" ) < /dev/null > "$GATE_LOG" 2>&1 &
CHILD_PID=$!
wait "$CHILD_PID"
GATE_RC=$?
CHILD_PID=""
set -e
if [ "$GATE_RC" -ne 0 ]; then
  say "гейт качества красный (код $GATE_RC), последние строки:"
  tail -n 40 "$GATE_LOG" >&2 || true
  revert_patch || exit 16
  fail 15 "патч откачен (задание $JOB_ID); $INSPECT; $HINT"
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
        f"Гейт качества целевого репозитория завершился с кодом 0. Журнал: {gate_log}", "",
        "## Ответ агента", "", quoted, "",
        "## ВНИМАНИЕ: правки НЕ ЗАКОММИЧЕНЫ", "",
        "changes are UNCOMMITTED — Claude orchestrator must review the diff and commit", "",
        "Что сделать дальше:", "",
        f"1. `git -C {top} diff` — прочитать правки целиком (новые файлы видны благодаря intent-to-add);",
        f"2. `git -C {top} add {all_paths}` и коммит по правилам проекта;",
        f"3. `scripts/agy_task.sh clean {job_id}` — удалить задание (патч: {patch}).", ""]
print("\n".join(out))
PY
