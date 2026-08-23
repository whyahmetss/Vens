"""
Hedefler — ne, ne zamana kadar, nasıl ölçülecek.

Üçü birden olmayan bir hedef dilektir. Bu dosya dilek takip etmez: her
hedefin bir bitiş tarihi ve ölçülebilir bir ilerleme tanımı olmak zorunda.

Tempo hesabı tamamen aritmetiktir. "İyi gidiyorsun" demez; **gereken hız
ile fiili hızı** yan yana koyar ve aradaki farkı söyler. Bu, koç katmanının
trading tarafında yaptığının aynısı.

Dosya deseni core/playbook.py ile aynı: geçersiz değer düşer, dosyanın
kalanı ayakta kalır, aynı sonuç tekrar tekrar loglanmaz.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from . import log
from .log import VERI

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_DOSYA = KOK / "hedefler.yaml"
ILERLEME = VERI / "ilerleme.jsonl"

AD_KALIBI = re.compile(r"^[a-z0-9_]+$")
TURLER = ("unite", "aliskanlik")

_SON_IZ: str | None = None


@dataclass(frozen=True)
class Hedef:
    ad: str                       # anahtar
    baslik: str
    tur: str
    bitis: date | None = None
    uniteler: tuple[str, ...] = ()
    gunluk_kart: int = 0
    gunluk_dakika: int = 0
    # Kart üreticisine iletilen serbest yönerge. "Soru Türkçe, cevap İngilizce"
    # gibi şeyler hedefin adından TAHMİN EDİLMEZ; burada yazılıysa geçer.
    dil_notu: str = ""

    @property
    def kalan_gun(self) -> int | None:
        if self.bitis is None:
            return None
        return (self.bitis - date.today()).days


@dataclass(frozen=True)
class Tempo:
    hedef: Hedef
    biten: int
    toplam: int
    kalan_gun: int | None
    gereken_hiz: float | None     # gün başına ünite
    fiili_hiz: float | None
    seri: int = 0                 # alışkanlık hedefleri için

    @property
    def yuzde(self) -> float:
        return 100 * self.biten / self.toplam if self.toplam else 0.0

    @property
    def tempoda(self) -> bool | None:
        if self.gereken_hiz is None or self.fiili_hiz is None:
            return None
        return self.fiili_hiz >= self.gereken_hiz


def _dosya(dosya=None) -> Path:
    if dosya is not None:
        return Path(dosya)
    return Path(os.environ.get("VENUS_HEDEFLER", VARSAYILAN_DOSYA))


def yukle(dosya=None) -> tuple[dict[str, Hedef], list[str]]:
    """Hedefleri okur ve doğrular. Döner: (hedefler, sorunlar)."""
    global _SON_IZ
    yol = _dosya(dosya)
    sorunlar: list[str] = []
    hedefler: dict[str, Hedef] = {}

    if not yol.exists():
        sorunlar.append(f"hedef dosyası bulunamadı: {yol.name}")
    else:
        try:
            ham = yaml.safe_load(yol.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, OSError) as e:
            ham = {}
            sorunlar.append(f"okunamadı: {' '.join(str(e).split())}")

        if not isinstance(ham, dict):
            sorunlar.append("kök seviye anahtar/değer olmalı")
            ham = {}

        for anahtar, giris in (ham.get("hedefler") or {}).items():
            ad = str(anahtar).strip().lower()
            yer = f"hedefler.{ad}"
            if not AD_KALIBI.match(ad):
                sorunlar.append(f"{yer}: ad yalnızca a-z, 0-9 ve _ içerebilir")
                continue
            if not isinstance(giris, dict):
                sorunlar.append(f"{yer}: anahtar/değer bloğu olmalı")
                continue

            tur = str(giris.get("tur", "")).strip().lower()
            if tur not in TURLER:
                sorunlar.append(f"{yer}.tur: {' | '.join(TURLER)} olmalı")
                continue

            bitis = None
            ham_bitis = giris.get("bitis")
            if ham_bitis is not None:
                try:
                    bitis = (ham_bitis if isinstance(ham_bitis, date)
                             else datetime.strptime(str(ham_bitis), "%Y-%m-%d").date())
                except ValueError:
                    sorunlar.append(f"{yer}.bitis: YYYY-AA-GG olmalı")

            uniteler: list[str] = []
            if tur == "unite":
                ham_u = giris.get("unite")
                if not isinstance(ham_u, (list, tuple)) or not ham_u:
                    sorunlar.append(f"{yer}: 'unite' boş olmayan liste olmalı")
                    continue
                for u in ham_u:
                    u_ad = str(u).strip().lower()
                    if not AD_KALIBI.match(u_ad):
                        sorunlar.append(f"{yer}.unite: geçersiz ünite '{u}'")
                    elif u_ad in uniteler:
                        sorunlar.append(f"{yer}.unite: yinelenen '{u_ad}'")
                    else:
                        uniteler.append(u_ad)
                if not uniteler:
                    continue

            def _tam(alan, en_az=0):
                d = giris.get(alan)
                if d is None:
                    return 0
                if isinstance(d, bool) or not isinstance(d, int) or d < en_az:
                    sorunlar.append(f"{yer}.{alan}: {en_az} ve üzeri tam sayı olmalı")
                    return 0
                return d

            hedefler[ad] = Hedef(ad=ad, baslik=str(giris.get("ad", ad)), tur=tur,
                                 bitis=bitis, uniteler=tuple(uniteler),
                                 gunluk_kart=_tam("gunluk_kart"),
                                 gunluk_dakika=_tam("gunluk_dakika"),
                                 dil_notu=str(giris.get("dil_notu", "") or "").strip())

    iz = f"{sorted(hedefler)}|{sorunlar}"
    if iz != _SON_IZ:
        _SON_IZ = iz
        log.yaz("hedef", olay="yuklendi", hedef=len(hedefler), sorun=sorunlar)
    return hedefler, sorunlar


# ---- ilerleme ------------------------------------------------------------

def _ilerleme_satirlari() -> list[dict]:
    if not ILERLEME.exists():
        return []
    out = []
    with ILERLEME.open(encoding="utf-8") as f:
        for s in f:
            s = s.strip()
            if s:
                try:
                    out.append(json.loads(s))
                except json.JSONDecodeError:
                    continue
    return out


def bitenler(hedef: str) -> dict[str, str]:
    """Ünite → bitirme tarihi. Geri alma 'geri' satırıyla yapılır."""
    out: dict[str, str] = {}
    for k in _ilerleme_satirlari():
        if k.get("hedef") != hedef:
            continue
        if "geri" in k:
            out.pop(k["geri"], None)
        elif "unite" in k:
            out[k["unite"]] = k.get("t", "")[:10]
    return out


def bitir(hedef: str, unite: str) -> None:
    with ILERLEME.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"hedef": hedef, "unite": unite,
                            "t": datetime.now().isoformat(timespec="seconds")},
                           ensure_ascii=False) + "\n")


def geri_al(hedef: str, unite: str) -> None:
    with ILERLEME.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"hedef": hedef, "geri": unite,
                            "t": datetime.now().isoformat(timespec="seconds")},
                           ensure_ascii=False) + "\n")


def tempo(h: Hedef, calisilan_gunler: set[str] | None = None) -> Tempo:
    """Gereken hız ile fiili hızı yan yana koyar. Yorum yok, aritmetik."""
    kalan = h.kalan_gun

    if h.tur == "unite":
        biten_map = bitenler(h.ad)
        biten, toplam = len(biten_map), len(h.uniteler)
        kalan_unite = max(0, toplam - biten)
        gereken = (kalan_unite / kalan) if (kalan and kalan > 0) else None

        fiili = None
        if biten_map:
            ilk = min(biten_map.values())
            try:
                gecen = (date.today() - datetime.strptime(ilk, "%Y-%m-%d").date()).days + 1
                fiili = biten / max(1, gecen)
            except ValueError:
                pass
        return Tempo(h, biten, toplam, kalan, gereken, fiili)

    # alışkanlık: ilerleme = kaç gün hedefi tutturdun
    gunler = calisilan_gunler or set()
    seri = 0
    g = date.today()
    while g.isoformat() in gunler:
        seri += 1
        g -= timedelta(days=1)
    return Tempo(h, len(gunler), len(gunler), kalan, None, None, seri)
