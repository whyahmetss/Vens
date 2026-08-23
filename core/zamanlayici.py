"""
Periyodik kontrol çalıştırıcısı.

Venüs komut beklemeden konuşabilir (Bölüm 12) — birinin saate bakması
gerekiyor. Bu dosya saate bakar, ne yapılacağını bilmez: kontrolün kendisi
onu ilgilendiren katmanda yaşar.

Kayıt, yetenek kayıt defteriyle aynı mantıkta: kontrol kendini beyan eder,
merkezi bir liste elle güncellenmez.
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Callable

from . import log

_GOREVLER: list[asyncio.Task] = []


@dataclass(frozen=True)
class Kontrol:
    ad: str
    saniye: int
    fn: Callable


KONTROLLER: list[Kontrol] = []


def periyodik(saniye: int, ad: str = ""):
    """`@periyodik(60)` — fonksiyonu her N saniyede bir çalıştırır."""
    def deco(fn):
        KONTROLLER.append(Kontrol(ad=ad or fn.__name__, saniye=saniye, fn=fn))
        return fn
    return deco


async def _dongu(k: Kontrol) -> None:
    while True:
        await asyncio.sleep(k.saniye)
        try:
            sonuc = k.fn()
            if inspect.isawaitable(sonuc):
                await sonuc
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # Bir kontrolün hatası diğerlerini ve sunucuyu düşürmemeli.
            log.yaz("zamanlayici", kontrol=k.ad, sonuc="hata", hata=repr(e))


def baslat() -> int:
    if _GOREVLER:
        return len(_GOREVLER)
    for k in KONTROLLER:
        _GOREVLER.append(asyncio.create_task(_dongu(k), name=f"kontrol:{k.ad}"))
    log.yaz("zamanlayici", olay="baslatildi",
            kontrol=[k.ad for k in KONTROLLER])
    return len(_GOREVLER)


def durdur() -> None:
    for g in _GOREVLER:
        g.cancel()
    _GOREVLER.clear()
