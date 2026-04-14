import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


GRIZZLY_API_KEY = os.getenv("GRIZZLY_API_KEY", "")
GRIZZLY_API_URL = os.getenv("GRIZZLY_API_URL", "https://api.grizzlysms.com/stori/v1/guest")

COUNTRY_MAP = {
    "usa": "usa",
    "can": "can",
    "vnm": "vnm",
}


@dataclass
class WarmupRecord:
    activation_id: str
    phone_number: str
    country: str
    status: str = "new"
    notes: str = ""
    created_at: int = int(time.time())


class WarmupStore:
    def __init__(self, path: str = "data/warmup_records.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load(self) -> List[Dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, rows: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, rec: WarmupRecord) -> None:
        rows = self._load()
        rows.append(asdict(rec))
        self._save(rows)

    def list(self) -> List[Dict[str, Any]]:
        return self._load()

    def update_status(self, activation_id: str, status: str, notes: str = "") -> bool:
        rows = self._load()
        changed = False
        for row in rows:
            if row["activation_id"] == activation_id:
                row["status"] = status
                row["notes"] = notes
                changed = True
                break
        if changed:
            self._save(rows)
        return changed


class GrizzlyBackend:
    """Безопасный backend для закупки номеров и контроля прогрева.

    ВАЖНО: класс не автоматизирует создание/взлом аккаунтов.
    Он только покупает номер и ведёт статус прогрева для ручной работы.
    """

    def __init__(self, api_key: str = GRIZZLY_API_KEY, api_url: str = GRIZZLY_API_URL):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.store = WarmupStore()

    def _request(self, path: str, timeout: int = 20) -> Any:
        if not self.api_key:
            raise RuntimeError("GRIZZLY_API_KEY не задан.")
        url = f"{self.api_url}{path}"
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        ctype = response.headers.get("content-type", "")
        if "json" in ctype:
            return response.json()
        return response.text

    def get_balance(self) -> str:
        data = self._request(f"/getBalance?api_key={self.api_key}")
        return str(data)

    def buy_number(self, country: str = "vnm", service: str = "tg") -> Dict[str, str]:
        if country not in COUNTRY_MAP:
            raise ValueError(f"Неизвестная страна: {country}")

        data = self._request(
            f"/getNumber/service/{service}/country/{COUNTRY_MAP[country]}?api_key={self.api_key}"
        )
        if not isinstance(data, dict) or "activationId" not in data or "phoneNumber" not in data:
            raise RuntimeError(f"Не удалось купить номер: {data}")

        record = WarmupRecord(
            activation_id=str(data["activationId"]),
            phone_number=str(data["phoneNumber"]),
            country=country,
        )
        self.store.add(record)
        return {
            "activation_id": record.activation_id,
            "phone_number": record.phone_number,
            "country": record.country,
            "status": record.status,
        }

    def list_warmup(self) -> List[Dict[str, Any]]:
        return self.store.list()

    def set_warmup_status(self, activation_id: str, status: str, notes: str = "") -> bool:
        return self.store.update_status(activation_id=activation_id, status=status, notes=notes)
