"""
Projeler — trading dışındaki işlerin.

Şartname Bölüm 7: "Proje bazlı ayrım (trading / projeler / finans / kişisel)."
Bu dosya "projeler" alanını açar.

Tek cümlelik hedef (Bölüm 0): "Kullanıcı bir uygulama açmaz — Venüs'ü
uyandırır." Bunun çalışması için Venüs'ün "dün nerede kaldın" sorusunu
cevaplayabilmesi gerekir. Cevabı üreten alan `sonraki`: işi bırakırken bir
sonraki adımı yazarsın, ertesi gün Venüs onu önüne koyar.

Depo append-only. Proje silinmez, durumu `arsiv` yapılır — bitirdiğin işin
kaydı da senin geçmişinin parçası.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .log import VERI

PROJELER = VERI / "projeler.jsonl"

DURUMLAR = ("aktif", "beklemede", "bitti", "arsiv")


@dataclass(frozen=True)
class Proje:
    ad: str
    aciklama: str = ""
    durum: str = "aktif"
    sonraki: str = ""
    guncelleme: str = ""

    @property
    def acik(self) -> bool:
        return self.durum in ("aktif", "beklemede")


def _satirlar() -> list[dict]:
    if not PROJELER.exists():
        return []
    out = []
    with PROJELER.open(encoding="utf-8") as f:
        for s in f:
            s = s.strip()
            if s:
                try:
                    out.append(json.loads(s))
                except json.JSONDecodeError:
                    continue
    return out


def _yaz(kayit: dict) -> None:
    with PROJELER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def hepsi() -> list[Proje]:
    """Projelerin güncel hâli. Sonraki satır öncekinin üstüne yazar."""
    havuz: dict[str, dict] = {}
    sira: list[str] = []
    for k in _satirlar():
        ad = k.get("proje")
        if not ad:
            continue
        if ad not in havuz:
            havuz[ad] = {"ad": ad}
            sira.append(ad)
        for alan in ("aciklama", "durum", "sonraki"):
            if alan in k:
                havuz[ad][alan] = k[alan]
        havuz[ad]["guncelleme"] = k.get("t", "")
    return [Proje(**{**{"aciklama": "", "durum": "aktif", "sonraki": "",
                        "guncelleme": ""}, **havuz[a]}) for a in sira]


def bul(ad: str) -> Proje | None:
    ad = (ad or "").strip().lower()
    for p in hepsi():
        if p.ad.lower() == ad:
            return p
    return None


def aktif() -> Proje | None:
    """Son 'aktif et' satırının işaret ettiği proje."""
    secili = None
    for k in _satirlar():
        if "aktif" in k:
            secili = k["aktif"]
    return bul(secili) if secili else None


def kaydet(ad: str, **alanlar: Any) -> Proje:
    kayit = {"proje": ad, "t": datetime.now().isoformat(timespec="seconds")}
    kayit.update({a: d for a, d in alanlar.items() if d is not None})
    _yaz(kayit)
    return bul(ad)


def aktif_et(ad: str) -> None:
    _yaz({"aktif": ad, "t": datetime.now().isoformat(timespec="seconds")})
