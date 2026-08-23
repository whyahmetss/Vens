"""
Kabuğa itme kanalı.

Bildirim tek itilen şey değil: bağlam da (açık killzone, sonuçsuz kayıt)
kullanıcı bir şey sormadan güncellenmeli. İkisi de aynı borudan geçer.

Çekirdek yayınlar, taşımayı bilmez — kim nasıl gösterecek köprünün işi
(Değişmez 6). Bir alıcı düşerse diğerleri etkilenmez.
"""

from __future__ import annotations

from typing import Any, Callable

from . import log

_ALICILAR: list[Callable[[dict], Any]] = []


def abone(fn: Callable[[dict], Any]) -> None:
    _ALICILAR.append(fn)


def cik(fn: Callable[[dict], Any]) -> None:
    if fn in _ALICILAR:
        _ALICILAR.remove(fn)


def acik() -> bool:
    """Dinleyen bir kabuk var mı. Bildirim bütçesi buna bakar."""
    return bool(_ALICILAR)


def yayinla(mesaj: dict) -> None:
    for fn in list(_ALICILAR):
        try:
            fn(mesaj)
        except Exception as e:
            log.yaz("kanal", olay="iletilemedi", hata=repr(e))
