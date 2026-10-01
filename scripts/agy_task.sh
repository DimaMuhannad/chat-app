#!/usr/bin/env bash
# Delegates a routine, token-heavy task to an Antigravity (agy) agent.
# The agent runs inside a systemd-run filesystem jail on a throwaway git worktree:
# agy's own --mode plan and --sandbox do NOT restrict reads/writes (verified 2026-10-01),
# so isolation is enforced here, at the OS level.
set -euo pipefail

CONF="${AGY_TASK_CONFIG:-/opt/chat-app/.agy/config}"
JOBS_DIR="${AGY_JOBS_DIR:-/var/tmp/agy-jobs}"
USAGE_LOG="$JOBS_DIR/usage.jsonl"
AGY_BIN="${AGY_BIN:-/root/.local/bin/agy}"
AGY_HOME="${AGY_HOME:-/root/.gemini/antigravity-cli}"

SECRET_RE='-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}|AIzaSy[A-Za-z0-9_-]{33}|AQ\.Ab[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|ntn_[A-Za-z0-9]{40,}|secret_[A-Za-z0-9]{40,}|\b[0-9]{8,10}:[A-Za-z0-9_-]{35}\b'
FORBIDDEN_FIND=( -name '.env' -o -name '.env.*' -o -name 'credentials.json' -o -name 'token.json'
                 -o -name '*.session' -o -name '*.session-journal' -o -name '*.pem' -o -name '*.key'
                 -o -name '*.pfx' -o -name '*.pkcs12' )

die() { echo "agy_task: $*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Использование:
  agy_task.sh run --repo PATH [--mode read|edit] [--model ID] [--timeout SEC]
                  [--max-chars N] [--task-file FILE | задача через stdin] [--keep]
  agy_task.sh diff JOB_ID     — сводка и путь к патчу правок агента
  agy_task.sh clean JOB_ID|--all
  agy_task.sh stats           — расход токенов Antigravity по журналу

Режимы:
  read  (по умолчанию) — агент только читает; любые его правки отбрасываются.
  edit  — агент правит изолированную копию; патч сохраняется в задании,
          в настоящий репозиторий его переносит проверяющий (git apply).
EOF
}

load_config() {
  [ -f "$CONF" ] || die "нет конфигурации $CONF (образец: .agy/config.example). Без неё запуск запрещён."
  RESTRICTED_PATHS=(); RESTRICTED_REMOTES=(); DEFAULT_MODEL="gemini-3.8-flash-high"
  while IFS='=' read -r k v; do
    [[ -z "$k" || "$k" == \#* ]] && continue
    case "$k" in
      restricted_path)   RESTRICTED_PATHS+=("$(realpath -m "$v")") ;;
      restricted_remote) RESTRICTED_REMOTES+=("$v") ;;
      default_model)     DEFAULT_MODEL="$v" ;;
    esac
  done < "$CONF"
}

check_not_restricted() {
  local top="$1" rp rr remotes
  for rp in "${RESTRICTED_PATHS[@]}"; do
    if [[ "$top" == "$rp" || "$top" == "$rp"/* ]]; then
      die "отказ: $top — закрытое NDA-пространство ($rp). Отправка его содержимого во внешнюю LLM запрещена (air-gap)."
    fi
  done
  remotes="$(git -C "$top" remote -v 2>/dev/null || true)"
  for rr in "${RESTRICTED_REMOTES[@]}"; do
    if grep -qiF -- "$rr" <<<"$remotes"; then
      die "отказ: remote репозитория содержит '$rr' (NDA). Air-gap."
    fi
  done
}

meta_get() { sed -n "s/^$2=//p" "$JOBS_DIR/$1/meta" 2>/dev/null; }

cmd_clean() {
  local id="$1" top ws
  [ -d "$JOBS_DIR/$id" ] || die "нет задания $id"
  top="$(meta_get "$id" repo)"; ws="$JOBS_DIR/$id/ws"
  if [ -n "$top" ] && [ -e "$ws" ]; then
    git -C "$top" worktree remove --force "$ws" 2>/dev/null || rm -rf "$ws"
    git -C "$top" worktree prune 2>/dev/null || true
  fi
  rm -rf "${JOBS_DIR:?}/$id"
  echo "удалено задание $id"
}

cmd_diff() {
  local id="$1" patch="$JOBS_DIR/$1/changes.patch"
  [ -f "$patch" ] || die "в задании $id нет правок"
  echo "Репозиторий: $(meta_get "$id" repo)"
  echo "Патч: $patch"
  git apply --stat "$patch"
  echo "Перенос: git -C $(meta_get "$id" repo) apply $patch"
}

cmd_stats() {
  [ -f "$USAGE_LOG" ] || { echo "журнал пуст"; return; }
  python3 - "$USAGE_LOG" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
inp = sum(r.get("input_tokens", 0) for r in rows)
out = sum(r.get("output_tokens", 0) for r in rows)
ok = sum(1 for r in rows if r.get("status") == "SUCCESS")
print(f"Заданий: {len(rows)} (успешных: {ok})")
print(f"Токены Antigravity: вход {inp:,}, выход {out:,}".replace(",", " "))
print(f"Ответов передано в Claude: {sum(r.get('response_chars', 0) for r in rows):,} символов".replace(",", " "))
PY
}

run_agent() {
  local ws="$1" prompt="$2" model="$3" timeout="$4" agent_mode="$5" out="$6"
  systemd-run --pipe --wait --collect --quiet \
    -p "WorkingDirectory=$ws" \
    -p "TemporaryFileSystem=/opt /root /home /srv /mnt /media /var/lib /var/log /var/tmp /var/backups /var/mail /var/spool" \
    -p "PrivateTmp=yes" \
    -p "BindPaths=$ws $AGY_HOME" \
    -p "BindReadOnlyPaths=$AGY_BIN" \
    -p "InaccessiblePaths=-/etc/systemd -/etc/ssh -/etc/shadow -/etc/gshadow -/run/user" \
    -p "ProtectProc=invisible" -p "ProcSubset=pid" -p "NoNewPrivileges=yes" \
    -p "MemoryMax=1G" -p "RuntimeMaxSec=$((timeout + 30))" \
    -p "Environment=HOME=/root" -p "Environment=PATH=/usr/local/bin:/usr/bin:/bin" \
    "$AGY_BIN" -p "$prompt" --model "$model" --mode "$agent_mode" \
      --output-format json --print-timeout "${timeout}s" > "$out" 2>"$out.stderr" || true
}

cmd_run() {
  local repo="" mode="read" model="" timeout=600 max_chars=6000 task_file="" keep=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --repo) repo="$2"; shift 2 ;;
      --mode) mode="$2"; shift 2 ;;
      --model) model="$2"; shift 2 ;;
      --timeout) timeout="$2"; shift 2 ;;
      --max-chars) max_chars="$2"; shift 2 ;;
      --task-file) task_file="$2"; shift 2 ;;
      --keep) keep=1; shift ;;
      *) die "неизвестный аргумент $1" ;;
    esac
  done
  [[ "$mode" == read || "$mode" == edit ]] || die "--mode должен быть read или edit"
  [ -n "$repo" ] || die "нужен --repo"
  load_config
  model="${model:-$DEFAULT_MODEL}"

  local task
  if [ -n "$task_file" ]; then task="$(cat "$task_file")"; else task="$(cat)"; fi
  [ -n "${task//[[:space:]]/}" ] || die "пустая задача"

  local top; top="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || die "$repo — не git-репозиторий"
  top="$(realpath "$top")"
  check_not_restricted "$top"

  mkdir -p "$JOBS_DIR"; chmod 700 "$JOBS_DIR"
  local id; id="$(date +%Y%m%d-%H%M%S)-$$"
  local job="$JOBS_DIR/$id" ws="$JOBS_DIR/$id/ws"
  mkdir -p "$job"
  printf 'repo=%s\nmode=%s\nmodel=%s\n' "$top" "$mode" "$model" > "$job/meta"

  git -C "$top" worktree add --detach --quiet "$ws" HEAD
  git -C "$top" diff HEAD --binary > "$job/uncommitted.patch"
  if [ -s "$job/uncommitted.patch" ]; then
    git -C "$ws" apply --whitespace=nowarn "$job/uncommitted.patch" || echo "предупреждение: незакоммиченные правки не перенесены в копию" >&2
  fi

  local found
  found="$(find "$ws" -path "$ws/.git" -prune -o \( "${FORBIDDEN_FIND[@]}" \) -print)"
  if [ -n "$found" ]; then
    echo "предупреждение: из копии удалены файлы с возможными секретами:" >&2
    sed "s|^$ws/|  |" <<<"$found" >&2
    xargs -r -d '\n' rm -f <<<"$found"
  fi
  found="$(grep -rIlE --exclude-dir=.git -- "$SECRET_RE" "$ws" 2>/dev/null || true)"
  if [ -n "$found" ]; then
    echo "agy_task: отказ — в копии найдены похожие на секреты строки (содержимое не показано):" >&2
    sed "s|^$ws/|  |" <<<"$found" >&2
    cmd_clean "$id" >/dev/null; exit 4
  fi

  git -C "$ws" add -A
  git -C "$ws" -c user.name=agy-baseline -c user.email=agy@localhost commit -q --allow-empty -m "agy baseline"
  echo "baseline=$(git -C "$ws" rev-parse HEAD)" >> "$job/meta"

  local rules
  if [ "$mode" = read ]; then
    rules="РЕЖИМ: ТОЛЬКО ЧТЕНИЕ. Не создавай, не изменяй и не удаляй файлы."
  else
    rules="РЕЖИМ: ПРАВКА. Вноси изменения прямо в файлы текущей папки. Тесты не запускай — их запустит проверяющий. В конце перечисли изменённые файлы и одной строкой суть правки по каждому."
  fi
  local prompt="Ты — исполнитель рутинной задачи для проверяющего инженера.
Правила:
- Работай ТОЛЬКО с файлами в текущей папке (это изолированная копия репозитория). Файлы вне неё не ищи.
- Не выполняй git-команды (commit, push, checkout, reset).
- Не ищи и не открывай файлы с ключами, токенами и паролями.
- Пиши по-русски. Идентификаторы, пути и код — как в исходниках.
- Финальный ответ краткий: только результат, без пересказа хода работы. Пути пиши простым текстом вида path/to/file.py:12 — без markdown-ссылок и без file://.
- $rules

ЗАДАЧА:
$task"

  local agent_mode=plan; [ "$mode" = edit ] && agent_mode=accept-edits
  local start; start=$(date +%s)
  run_agent "$ws" "$prompt" "$model" "$timeout" "$agent_mode" "$job/result.json"
  if ! python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get("response","").strip() else 1)' "$job/result.json" 2>/dev/null; then
    echo "предупреждение: пустой ответ, повтор…" >&2
    run_agent "$ws" "$prompt" "$model" "$timeout" "$agent_mode" "$job/result.json"
  fi

  git -C "$ws" add -A -N . 2>/dev/null || true
  git -C "$ws" diff --binary HEAD > "$job/changes.patch" || true
  local changed=0; [ -s "$job/changes.patch" ] && changed=1
  if [ "$mode" = read ] && [ "$changed" = 1 ]; then
    echo "предупреждение: агент изменил файлы в режиме чтения — правки отброшены" >&2
    rm -f "$job/changes.patch"; changed=0
  fi

  python3 - "$job/result.json" "$USAGE_LOG" "$id" "$top" "$mode" "$model" "$max_chars" "$(( $(date +%s) - start ))" <<'PY'
import json, sys, time
res, log, jid, repo, mode, model, max_chars, wall = sys.argv[1:9]
try:
    d = json.load(open(res))
except Exception:
    raw = open(res, errors="replace").read()[-1500:]
    d = {"status": "NO_JSON", "response": "", "error": raw or "агент не вернул результат (таймаут или сбой)"}
u = d.get("usage") or {}
resp = (d.get("response") or "").strip()
status = d.get("status", "?")
print(f"=== agy {status} | {model} | {wall} с | токены Antigravity: вход {u.get('input_tokens', 0)}, выход {u.get('output_tokens', 0)} ===")
if status != "SUCCESS" and resp:
    print("(статус не SUCCESS, но ответ есть — известная нестабильность agy; проверь ответ на полноту)")
if d.get("error") and not resp:
    print("Ошибка:", d["error"])
mc = int(max_chars)
print(resp if len(resp) <= mc else resp[:mc] + f"\n…[обрезано {len(resp) - mc} символов; полный ответ: {res}]")
with open(log, "a") as f:
    f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "job": jid, "repo": repo, "mode": mode,
                        "model": model, "status": status, "seconds": int(wall),
                        "input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0),
                        "response_chars": min(len(resp), mc)}, ensure_ascii=False) + "\n")
PY

  if [ "$changed" = 1 ]; then
    echo "=== правки агента (задание $id) ==="
    git apply --stat "$job/changes.patch"
    echo "Патч: $job/changes.patch"
    echo "Проверь патч, затем: git -C $top apply $job/changes.patch ; после — agy_task.sh clean $id"
  elif [ "$keep" = 0 ]; then
    cmd_clean "$id" >/dev/null
  else
    echo "Задание сохранено: $id"
  fi
}

case "${1:-}" in
  run) shift; cmd_run "$@" ;;
  diff) [ -n "${2:-}" ] || die "нужен JOB_ID"; cmd_diff "$2" ;;
  clean)
    [ -n "${2:-}" ] || die "нужен JOB_ID или --all"
    if [ "$2" = --all ]; then
      for d in "$JOBS_DIR"/*/; do [ -d "$d" ] && cmd_clean "$(basename "$d")"; done; true
    else cmd_clean "$2"; fi ;;
  stats) cmd_stats ;;
  -h|--help|"") usage ;;
  *) usage; exit 1 ;;
esac
