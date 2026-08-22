"""
Olay günlüğü.

Şartname İ4: "Log önce, hafıza sonra."
Hafıza mimarisi baştan tasarlanmaz — buradan biriken kayıttan türetilir.
Bu yüzden bugünden itibaren HER ŞEY yazılır.
"""

from __future__ import annotations
import json, os
from datetime import datetime
from pathlib import Path

VERI = Path(os.environ.get("VENUS_VERI", Path.home() / ".venus"))
VERI.mkdir(parents=True, exist_ok=True)

OLAYLAR = VERI / "olaylar.jsonl"


def yaz(tur: str, **veri) -> None:
    kayit = {"t": datetime.now().isoformat(timespec="seconds"), "tur": tur, **veri}
    with OLAYLAR.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def oku(n: int = 50, tur: str | None = None) -> list[dict]:
    if not OLAYLAR.exists():
        return []
    kayitlar = []
    with OLAYLAR.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                k = json.loads(line)
            except json.JSONDecodeError:
                continue
            if tur is None or k.get("tur") == tur:
                kayitlar.append(k)
    return kayitlar[-n:]
