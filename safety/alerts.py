"""Critical-alert delivery channel (plan 4.5, v3).

Exists from Phase 1, not Phase 4: otherwise the most important safety net spends ~3 months
pushing "into the void" (MCP is pull-only, the client never initiates a conversation). A minimal
always-on channel:
  1) the log file data/alerts.log — always (zero dependencies, never crashes);
  2) macOS notification (osascript) — locally;
  3) optionally a bare Telegram sendMessage (no bot) — if token+chat_id is set.

Privacy (plan 8): Telegram is not E2E. So on Telegram — MINIMAL, non-specific text
("a critical value in today's test — check the system"), no numbers/diagnoses.
Full detail — only in the local log and the macOS notification (they don't leave the host).
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from core.config import settings

_LOG = Path(__file__).resolve().parent.parent / "data" / "alerts.log"
_TELEGRAM_GENERIC = ("⚠️ Health OS: a critical value in today's data — "
                     "check the system and call your doctor today.")


def _log(title: str, message: str) -> None:
    line = f"{datetime.now().isoformat()}\t{title}\t{message}"
    # stderr too: MCP clients keep the server's stderr in their logs, and in a `docker run --rm`
    # container the log file disappears with the container
    print(f"[health-os ALERT] {line}", file=sys.stderr, flush=True)
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        with _LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass  # read-only FS / permissions: must not break ingestion; stderr already has it


def _macos_notify(title: str, message: str) -> bool:
    # display notification has a length limit; take the first sentence
    short = message.split(";")[0][:200].replace('"', "'")
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{short}" with title "{title}" sound name "Basso"'],
            check=True, capture_output=True, timeout=5,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


def _telegram_send(text: str) -> bool:
    token = settings.alert_telegram_bot_token
    chat = settings.alert_telegram_chat_id
    if not token or not chat:
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            return json.load(resp).get("ok", False)
    except Exception:  # noqa: BLE001 — the delivery channel must not crash ingestion
        return False


def send_critical_alert(title: str, message: str) -> list[str]:
    """Delivers a critical alert through all available channels. Returns the list of channels."""
    delivered: list[str] = []
    _log(title, message)
    delivered.append("log")
    if _macos_notify(title, message):
        delivered.append("macos")
    if _telegram_send(_TELEGRAM_GENERIC):   # on Telegram — only generic (privacy)
        delivered.append("telegram")
    return delivered
