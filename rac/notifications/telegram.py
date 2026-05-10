import json
import logging
import urllib.error
import urllib.request

log = logging.getLogger("rac.notifications.telegram")


class TelegramClient:
    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id

    @property
    def configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def send(self, text: str) -> bool:
        if not self.configured:
            return False
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        body = json.dumps({"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            log.warning("telegram_send_error: %s", exc)
            return False
