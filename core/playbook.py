"""
Playbook okuyucu ve doğrulayıcı.

`kurallar.yaml` "neyi asla yapma" der. Playbook "bir işlemin geçerli sayılması
için ne görmüş olman gerekir" der. İkisi birlikte kalite karnesini üretir
(core/karne.py).

core/kurallar.py ile aynı ilkeler — o dosyanın kardeşi:
- Deterministik. LLM'e sorulmaz.
- Geçersiz değer düşer, dosyanın kalanı ayakta kalır.
- Bozuk dosya Venüs'ü açılmaz yapmaz; sorunlar `playbook` komutunda görünür.
- Önbellek yok: setup'ı değiştirmek dosyayı düzenlemektir.
- Aynı sonuç tekrar tekrar loglanmaz (olay günlüğünü boğardı).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import log
from .denetci import KURAL_ADLARI

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_DOSYA = KOK / "playbook.yaml"

AD_KALIBI = re.compile(r"^[a-z0-9_]+$")
VARSAYILAN_CEZA = 10          # playbook'ta ağırlığı yazılmamış ihlalin maliyeti

_SON_IZ: str | None = None


@dataclass(frozen=True)
class Madde:
    ad: str
    soru: str
    agirlik: int


@dataclass(frozen=True)
class Setup:
    ad: str                    # anahtar: sweep_mss_fvg
    baslik: str                # görünen ad
    kontrol: tuple[Madde, ...]
    min_rr: float | None = None


@dataclass(frozen=True)
class Playbook:
    dosya: Path
    setuplar: dict[str, Setup] = field(default_factory=dict)
    etiketler: tuple[str, ...] = ()
    ceza: dict[str, int] = field(default_factory=dict)
    sorunlar: tuple[str, ...] = ()
    okundu: bool = False

    def setup(self, ad: str) -> Setup | None:
        return self.setuplar.get((ad or "").strip().lower())

    def cezasi(self, kural: str) -> int:
        return self.ceza.get(kural, VARSAYILAN_CEZA)


def _dosya(dosya=None) -> Path:
    if dosya is not None:
        return Path(dosya)
    return Path(os.environ.get("VENUS_PLAYBOOK", VARSAYILAN_DOSYA))


def _tam_sayi(d: Any, alan: str, sorunlar: list[str], en_az=0, en_cok=100):
    if isinstance(d, bool) or not isinstance(d, int):
        sorunlar.append(f"{alan}: tam sayı olmalı")
        return None
    if not (en_az <= d <= en_cok):
        sorunlar.append(f"{alan}: {en_az}–{en_cok} arasında olmalı (bulunan: {d})")
        return None
    return d


def yukle(dosya=None, kurallar=None) -> Playbook:
    """Playbook'u okur ve doğrular.

    `kurallar`: verilirse setup'ın `min_rr`'si ona karşı denetlenir — playbook
    global disiplini SIKILAŞTIRABİLİR, gevşetemez.
    """
    yol = _dosya(dosya)
    sorunlar: list[str] = []

    if not yol.exists():
        return _bitir(yol, {}, (), {}, [f"playbook dosyası bulunamadı: {yol.name}"],
                      okundu=False)
    try:
        ham = yaml.safe_load(yol.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as e:
        neden = " ".join(str(e).split())
        return _bitir(yol, {}, (), {}, [f"okunamadı: {neden}"], okundu=False)

    if ham is None:
        ham = {}
    if not isinstance(ham, dict):
        return _bitir(yol, {}, (), {}, ["kök seviye anahtar/değer olmalı"], okundu=False)

    for bolum in ham:
        if bolum not in ("setuplar", "etiketler", "ceza"):
            sorunlar.append(f"bilinmeyen bölüm: {bolum}")

    kurallar_min_rr = kurallar.deger("trading.min_rr") if kurallar is not None else None

    # ---- setuplar ----
    setuplar: dict[str, Setup] = {}
    for anahtar, giris in (ham.get("setuplar") or {}).items():
        ad = str(anahtar).strip().lower()
        if not AD_KALIBI.match(ad):
            sorunlar.append(f"setuplar.{anahtar}: ad yalnızca a-z, 0-9 ve _ içerebilir")
            continue
        if not isinstance(giris, dict):
            sorunlar.append(f"setuplar.{ad}: anahtar/değer bloğu olmalı")
            continue

        maddeler: list[Madde] = []
        gorulen: set[str] = set()
        ham_kontrol = giris.get("kontrol")
        if not isinstance(ham_kontrol, (list, tuple)) or not ham_kontrol:
            sorunlar.append(f"setuplar.{ad}: 'kontrol' boş olmayan liste olmalı")
            continue
        for i, m in enumerate(ham_kontrol, 1):
            yer = f"setuplar.{ad}.kontrol[{i}]"
            if not isinstance(m, dict):
                sorunlar.append(f"{yer}: anahtar/değer olmalı")
                continue
            m_ad = str(m.get("ad", "")).strip().lower()
            if not AD_KALIBI.match(m_ad):
                sorunlar.append(f"{yer}: 'ad' yalnızca a-z, 0-9 ve _ içerebilir")
                continue
            if m_ad in gorulen:
                sorunlar.append(f"{yer}: yinelenen madde '{m_ad}'")
                continue
            agirlik = _tam_sayi(m.get("agirlik"), f"{yer}.agirlik", sorunlar)
            if agirlik is None:
                continue
            gorulen.add(m_ad)
            maddeler.append(Madde(ad=m_ad, soru=str(m.get("soru", m_ad)), agirlik=agirlik))

        if not maddeler:
            sorunlar.append(f"setuplar.{ad}: geçerli kontrol maddesi kalmadı")
            continue

        min_rr = None
        ham_rr = giris.get("min_rr")
        if ham_rr is not None:
            if isinstance(ham_rr, bool) or not isinstance(ham_rr, (int, float)):
                sorunlar.append(f"setuplar.{ad}.min_rr: sayı olmalı")
            elif ham_rr <= 0:
                sorunlar.append(f"setuplar.{ad}.min_rr: 0'dan büyük olmalı")
            elif kurallar_min_rr is not None and ham_rr < kurallar_min_rr:
                # Setup tanımı global disiplini gevşetemez (bkz. modül başlığı).
                sorunlar.append(
                    f"setuplar.{ad}.min_rr: {ham_rr:g}, kurallar.yaml'daki "
                    f"{kurallar_min_rr:g} değerinden gevşek — yok sayıldı")
            else:
                min_rr = float(ham_rr)

        setuplar[ad] = Setup(ad=ad, baslik=str(giris.get("ad", ad)),
                             kontrol=tuple(maddeler), min_rr=min_rr)

    # ---- etiketler ----
    etiketler: list[str] = []
    ham_etiket = ham.get("etiketler")
    if ham_etiket is not None:
        if not isinstance(ham_etiket, (list, tuple)):
            sorunlar.append("etiketler: liste olmalı")
        else:
            for e in ham_etiket:
                ad = str(e).strip().lower()
                if not AD_KALIBI.match(ad):
                    sorunlar.append(f"etiketler: geçersiz etiket '{e}'")
                elif ad in etiketler:
                    sorunlar.append(f"etiketler: yinelenen '{ad}'")
                else:
                    etiketler.append(ad)

    # ---- ceza ----
    ceza: dict[str, int] = {}
    ham_ceza = ham.get("ceza")
    if ham_ceza is not None:
        if not isinstance(ham_ceza, dict):
            sorunlar.append("ceza: anahtar/değer olmalı")
        else:
            for kural, puan in ham_ceza.items():
                k = str(kural).strip()
                if k not in KURAL_ADLARI:
                    sorunlar.append(f"ceza.{k}: böyle bir kural yok — hiçbir şey yapmaz")
                    continue
                p = _tam_sayi(puan, f"ceza.{k}", sorunlar)
                if p is not None:
                    ceza[k] = p

    return _bitir(yol, setuplar, tuple(etiketler), ceza, sorunlar, okundu=True)


def _bitir(yol, setuplar, etiketler, ceza, sorunlar, *, okundu) -> Playbook:
    global _SON_IZ
    iz = f"{okundu}|{sorted(setuplar)}|{sorted(ceza.items())}|{sorunlar}"
    if iz != _SON_IZ:
        _SON_IZ = iz
        log.yaz("playbook", olay="yuklendi", dosya=str(yol), okundu=okundu,
                setup=len(setuplar), sorun=sorunlar)
    return Playbook(dosya=yol, setuplar=setuplar, etiketler=etiketler,
                    ceza=ceza, sorunlar=tuple(sorunlar), okundu=okundu)
