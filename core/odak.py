"""
Odak seansları — çalışma tarafının jurnali.

Şartname Bölüm 0: Venüs bir "kişisel AI çalışma ortamı". Trading disiplin
motoru zaten var; bu dosya aynı motoru zamana uyguluyor: ne zaman, ne kadar,
ne üzerinde çalıştın.

Jurnalle aynı ilkeler:
- Append-only. Seans kapatılır, silinmez.
- Venüs engellemez, kaydeder. "Üç saattir çalışıyorsun" bir gözlem;
  "dur" bir emirdir (kimlik.md: hatırlatır, sonra çekilir).
- Kurallar `kurallar.yaml`'ın `calisma` bölümünden gelir; boş bırakılan
  alan sessizce denetlenmez.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from .log import VERI

ODAK = VERI / "odak.jsonl"


@dataclass(frozen=True)
class Seans:
    id: str
    baslangic: str
    konu: str
    proje: str = ""
    bitis: str = ""
    notu: str = ""

    @property
    def acik(self) -> bool:
        return not self.bitis

    @property
    def dakika(self) -> int:
        try:
            bas = datetime.fromisoformat(self.baslangic)
            son = datetime.fromisoformat(self.bitis) if self.bitis else datetime.now()
        except ValueError:
            return 0
        return max(0, int((son - bas).total_seconds() // 60))


def _satirlar() -> list[dict]:
    if not ODAK.exists():
        return []
    out = []
    with ODAK.open(encoding="utf-8") as f:
        for s in f:
            s = s.strip()
            if s:
                try:
                    out.append(json.loads(s))
                except json.JSONDecodeError:
                    continue
    return out


def _yaz(kayit: dict) -> None:
    with ODAK.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def hepsi() -> list[Seans]:
    """Kapanışlar taban satırların üstüne uygulanır (jurnal deposuyla aynı desen)."""
    taban: dict[str, dict] = {}
    sira: list[str] = []
    for k in _satirlar():
        if "kapat" in k:
            hedef = taban.get(k["kapat"])
            if hedef is not None:
                hedef["bitis"] = k["t"]
                hedef["notu"] = k.get("notu", "")
        elif "id" in k:
            taban[k["id"]] = dict(k)
            sira.append(k["id"])
    return [Seans(id=taban[i]["id"], baslangic=taban[i]["baslangic"],
                  konu=taban[i].get("konu", ""), proje=taban[i].get("proje", ""),
                  bitis=taban[i].get("bitis", ""), notu=taban[i].get("notu", ""))
            for i in sira]


def acik_seans() -> Seans | None:
    for s in reversed(hepsi()):
        if s.acik:
            return s
    return None


def basla(konu: str, proje: str = "") -> Seans:
    kayit = {"id": uuid.uuid4().hex[:4],
             "baslangic": datetime.now().isoformat(timespec="seconds"),
             "konu": konu, "proje": proje}
    _yaz(kayit)
    return Seans(id=kayit["id"], baslangic=kayit["baslangic"], konu=konu, proje=proje)


def bitir(kimlik: str, notu: str = "") -> None:
    _yaz({"kapat": kimlik, "t": datetime.now().isoformat(timespec="seconds"),
          "notu": notu})


def gun(tarih: date | None = None) -> list[Seans]:
    ek = (tarih or date.today()).isoformat()
    return [s for s in hepsi() if s.baslangic.startswith(ek)]


def gunluk_dakika(tarih: date | None = None) -> int:
    return sum(s.dakika for s in gun(tarih))
