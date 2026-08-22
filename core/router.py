"""
Yönlendirici — çekirdeğin karar veren parçası.

Şartname Bölüm 3: çekirdek karar verir ama iş yapmaz.
Hangi yetenek, hangi parametre, izin var mı, onay gerekir mi.
"""

from __future__ import annotations
import inspect, time

from . import log
from .registry import Risk, bul, satir, uyari, bilgi

# Bekleyen onaylar: oturum -> (yetenek, argüman)
_BEKLEYEN: dict[str, tuple] = {}


async def _cagir(s, arg: str):
    sonuc = s.fn(arg)
    if inspect.isawaitable(sonuc):
        sonuc = await sonuc
    return sonuc or []


async def yonlendir(girdi: str, oturum: str = "yerel") -> list[dict]:
    girdi = girdi.strip()
    if not girdi:
        return []

    # --- bekleyen onay var mı? ---
    if oturum in _BEKLEYEN:
        s, arg = _BEKLEYEN.pop(oturum)
        if girdi.lower() in ("e", "evet", "onayla", "y", "yes"):
            log.yaz("onay", yetenek=s.ad, arg=arg, sonuc="kabul")
            return await _calistir(s, arg)
        log.yaz("onay", yetenek=s.ad, arg=arg, sonuc="ret")
        return [bilgi("iptal edildi.")]

    komut, _, arg = girdi.partition(" ")
    s = bul(komut)

    if s is None:
        log.yaz("komut", girdi=girdi, sonuc="bilinmeyen")
        return [uyari(f'bilinmeyen komut: {komut}'), bilgi('"yardim" yazarak listeye bak.')]

    # --- risk kapısı (Bölüm 2) ---
    if s.risk is Risk.TURUNCU:
        _BEKLEYEN[oturum] = (s, arg)
        log.yaz("onay_istendi", yetenek=s.ad, arg=arg)
        return [uyari(f"'{s.ad}' geri alınması zor bir işlem."),
                satir("onaylıyor musun? (evet / hayır)")]

    return await _calistir(s, arg)


async def _calistir(s, arg: str) -> list[dict]:
    t0 = time.perf_counter()
    try:
        cikti = await _cagir(s, arg)
        ms = int((time.perf_counter() - t0) * 1000)
        log.yaz("komut", yetenek=s.ad, arg=arg, risk=s.risk.value,
                sonuc="basarili", ms=ms, satir_sayisi=len(cikti))
        return cikti
    except Exception as e:
        log.yaz("komut", yetenek=s.ad, arg=arg, risk=s.risk.value,
                sonuc="hata", hata=repr(e))
        return [uyari(f"hata: {e}")]
