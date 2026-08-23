"""
İzin denetimi.

Şartname Bölüm 9: "Her yetenek hangi izinlere ihtiyaç duyduğunu beyan eder.
Kullanıcı izinleri tek ekrandan görür ve **kapatabilir**."

Beyan kayıt defterinde (Perm), kapatma burada. Kapalı bir izin isteyen
yetenek çalışmaz — çekirdek reddeder, yetenek hiç çağrılmaz.

Kaynak `guard/izinler.yaml`: ajanın yazma alanı dışında (Değişmez 8).
Kendi iznini genişletebilen bir sistem, izin sistemi değildir.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from . import log
from .registry import Perm

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN = KOK / "guard" / "izinler.yaml"

_SON_IZ: str | None = None


def _dosya() -> Path:
    return Path(os.environ.get("VENUS_IZINLER", VARSAYILAN))


def kapali() -> set[str]:
    """Kapatılmış izinler. Dosya yoksa ya da bozuksa hiçbir izin kapalı değildir.

    Bozuk dosyada "her şeyi kapat" davranışı Venüs'ü tümüyle kullanılamaz
    yapardı; "hiçbirini kapatma" ise sessizce yetki genişletir. İkisi de kötü,
    ama ikincisi görülebilir: durum `izinler` komutunda ve logda söylenir.
    """
    global _SON_IZ
    yol = _dosya()
    sonuc: set[str] = set()
    sorun = ""

    if not yol.exists():
        sorun = "izin dosyası yok"
    else:
        try:
            ham = yaml.safe_load(yol.read_text(encoding="utf-8")) or {}
            liste = ham.get("kapali") or []
            if not isinstance(liste, (list, tuple)):
                sorun = "'kapali' liste olmalı"
            else:
                gecerli = {p.value for p in Perm}
                for oge in liste:
                    ad = str(oge).strip().lower()
                    if ad in gecerli:
                        sonuc.add(ad)
                    else:
                        sorun = f"tanınmayan izin: {ad}"
        except (yaml.YAMLError, OSError) as e:
            sorun = f"okunamadı: {' '.join(str(e).split())}"

    iz = f"{sorted(sonuc)}|{sorun}"
    if iz != _SON_IZ:
        _SON_IZ = iz
        log.yaz("izin", olay="yuklendi", kapali=sorted(sonuc), sorun=sorun or None)
    return sonuc


def engel(izinler) -> list[str]:
    """Yeteneğin istediği izinlerden kapatılmış olanlar."""
    k = kapali()
    return [i.value for i in izinler if i.value in k]
