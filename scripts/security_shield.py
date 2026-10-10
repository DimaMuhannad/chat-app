#!/usr/bin/env python3
"""Security Shield: тонкий делегатор к общей обёртке assistant-core (SECF-01, D-18).

Общую обёртку shield держит assistant-core; chat-app только запускает её тем же интерпретатором
assistant-core (`<каталог>/.venv/bin/python <каталог>/scripts/security_shield.py`). Правила NDA
определяют данные рабочих пространств, а не этот файл: здесь нет констант слов NDA и нет импорта
общей библиотеки.

Каталог assistant-core берётся из переменной окружения ASSISTANT_CORE_DIR, иначе /opt/assistant-core.
Подмена переменной принимается как доверенная (так же, как PERSONA_CONFIG_PATH): окружение процесса
принадлежит владельцу.

Аргументы командной строки пробрасываются без изменений, код возврата наследуется (неизвестный флаг
даёт 2, как у argparse обёртки assistant-core). Рабочий каталог, stdout и stderr не меняются.
Fail-closed: нет каталога, обёртки или интерпретатора - строка «SECURITY SHIELD ERROR» в stderr и код 1;
молчаливого прохода нет.
"""

import os
import subprocess
import sys
from pathlib import Path

DEFAULT_CORE_DIR = "/opt/assistant-core"


def _fail(reason: str) -> int:
    print(f"❌ SECURITY SHIELD ERROR: {reason}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    core_dir = Path(os.environ.get("ASSISTANT_CORE_DIR") or DEFAULT_CORE_DIR)
    shield = core_dir / "scripts" / "security_shield.py"
    interpreter = core_dir / ".venv" / "bin" / "python"

    if not core_dir.is_dir():
        return _fail(f"каталог assistant-core не найден: {core_dir}")
    if not shield.is_file():
        return _fail(f"обёртка shield не найдена: {shield}")
    if not (interpreter.is_file() and os.access(interpreter, os.X_OK)):
        return _fail(f"интерпретатор assistant-core не найден или не исполняем: {interpreter}")

    try:
        # Потомок наследует cwd, stdout и stderr: вывод не перехватывается и не пересобирается
        proc = subprocess.run([str(interpreter), str(shield), *argv], check=False)
    except OSError as exc:
        return _fail(f"не удалось запустить обёртку assistant-core: {exc}")
    if proc.returncode < 0:
        return _fail(f"обёртка assistant-core завершена сигналом {-proc.returncode}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
