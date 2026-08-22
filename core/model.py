"""
Görev başına model seçimi.

Şartname Bölüm 15, Açık Karar 1'in cevabı: tek bir "Venüs modeli" yok.
Her LLM görevi kendi modelini seçer, çünkü görevlerin gereksinimleri
birbirine benzemiyor — kapalı listeden yetenek seçmek ile gece raporu
yazmak aynı yeteneği istemez.

Tablo BURADA yaşar, çağrı yerlerinde değil. Model değiştirmek tek satır
düzenlemektir; kodun içinde model adı aramak gerekmez.

Öncelik sırası:
    VENUS_MODEL_<GOREV>   tek görevi değiştirir  (VENUS_MODEL_NIYET=...)
    VENUS_MODEL           hepsini birden değiştirir (deneme için pratik)
    tablo                 varsayılan
"""

from __future__ import annotations

import os

# Yalnızca gerçekten var olan görevler burada durur. Yazılmamış bir fazın
# görevi peşinen eklenmez — çalışmayan kod eklenmez (CLAUDE.md, "Yapma").
GOREVLER: dict[str, str] = {
    # Serbest cümleyi kapalı bir yetenek listesine eşler. Türkçe devrik cümle
    # ve yazım hatası isabeti doğrudan bu modelin işi.
    "niyet": "claude-opus-5",
}


def sec(gorev: str) -> str:
    ozel = os.environ.get(f"VENUS_MODEL_{gorev.upper()}", "").strip()
    if ozel:
        return ozel
    genel = os.environ.get("VENUS_MODEL", "").strip()
    if genel:
        return genel
    if gorev not in GOREVLER:
        raise KeyError(f"tanımsız model görevi: {gorev} "
                       f"(tanımlı: {', '.join(GOREVLER)})")
    return GOREVLER[gorev]
