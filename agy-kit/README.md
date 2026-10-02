# agy-kit: делегирование рутины агентам Antigravity

Перенос в новый проект: скопируйте содержимое папки в корень репозитория (структура сохранена).

- `scripts/agy_task.sh` — обёртка: запуск agy в изолированной копии, отказ для NDA-путей/remote, возврат правок патчем.
- `.agents/agents/{reader,gsd-executor,test-writer,docs}/agent.md` — профили агентов (промпты).
- `.claude/skills/agy-delegate/SKILL.md` — скилл для Claude Code: когда и как делегировать.
- `.agy/config.example` — скопируйте в `.agy/config` и заполните (сам `config` не коммитьте).

Нужны: установленный `agy`, `git`, `python3`, `systemd-run` (Linux). Не запускайте `agy` напрямую в репозитории.
