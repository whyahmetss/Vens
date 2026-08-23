"""
Konuşma tanıma sembol düzeltmesi.

Şartname Bölüm 8, ismen sayılan sorun: "Türkçe konuşma tanıma sembolleri
bozar (BTC → 'bitisi')." Tanıyıcı "BTC" duyduğunda Türkçe kelime arar ve
bulur; sonuç sembol değil, ona benzeyen bir kelimedir.

Bu katman DETERMİNİSTİKTİR. Modele "bu ne demek istedi" sorulmaz — yanlış
sembolle çalışan bir komut, hiç çalışmayan komuttan kötüdür.

Yalnızca SESTEN gelen metne uygulanır. Klavyeden "bitisi" yazan kullanıcı
onu kastetmiştir; düzeltilmez.

Liste kapalıdır ve elle büyütülür. Tanınmayan bir söyleyiş sessizce
düzeltilmez — niyet çözücüye ham hâliyle gider, o da anlamazsa
`anlasilmadi` döner. Yanlış tahmin etmektense anlamamak yeğdir.
"""

from __future__ import annotations

import re
import unicodedata

# kanonik sembol -> duyulabilecek söyleyişler (küçük harf, sadeleştirilmiş)
SOYLEYISLER: dict[str, tuple[str, ...]] = {
    "BTC":    ("bitcoin", "bit coin", "bitisi", "bitkoin", "bitci", "bi ti si",
               "bitkoyin", "bitcoyin"),
    "ETH":    ("ethereum", "etherium", "eterium", "iterium", "etheryum", "i ti eyc"),
    "SOL":    ("solana", "sol ana"),
    "XRP":    ("ripple", "eks ar pi", "ripıl"),
    "XAUUSD": ("altin", "ons altin", "gold", "altin ons", "sari maden"),
    "XAGUSD": ("gumus", "silver", "ons gumus"),
    "EURUSD": ("euro dolar", "eurodolar", "avro dolar", "yuro dolar"),
    "GBPUSD": ("pound dolar", "sterlin dolar", "gbp usd", "kablo"),
    "USDJPY": ("dolar yen", "usd yen"),
    "USDTRY": ("dolar tl", "dolar turk lirasi", "dolar lira", "usd try"),
    "NAS100": ("nasdak", "nasdaq", "nas dak", "nas yuz"),
    "US30":   ("dow jones", "dovcones", "dau cones", "us otuz"),
    "SPX500": ("es and pi", "sp bes yuz", "es ve pe", "spx"),
}


def _sade(t: str) -> str:
    """Aksan ve noktalama dışarı. 'ALTIN,' ile 'altın' aynı şeydir."""
    t = t.lower().replace("ı", "i").replace("İ", "i")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w\s]", " ", t)


# Uzun söyleyiş önce denenir: "ons altin", "altin"den önce eşleşmeli.
_ESLEME: list[tuple[str, str]] = sorted(
    ((s, kanonik) for kanonik, liste in SOYLEYISLER.items() for s in liste),
    key=lambda p: -len(p[0]),
)


def duzelt(metin: str) -> tuple[str, list[tuple[str, str]]]:
    """Sesten gelen metindeki sembol söyleyişlerini kanonik hâline çevirir.

    Döner: (düzeltilmiş metin, [(bulunan, yerine konan), ...])
    """
    if not metin.strip():
        return metin, []

    kelimeler = metin.split()
    sade = [_sade(k) for k in kelimeler]
    cikti: list[str] = []
    degisiklikler: list[tuple[str, str]] = []
    i = 0

    while i < len(kelimeler):
        eslesti = False
        # En uzun söyleyişten başlayarak, i'den itibaren kaç kelime tutuyor bak.
        for soyleyis, kanonik in _ESLEME:
            n = len(soyleyis.split())
            if i + n > len(kelimeler):
                continue
            if " ".join(sade[i:i + n]).strip() == soyleyis:
                cikti.append(kanonik)
                degisiklikler.append((" ".join(kelimeler[i:i + n]), kanonik))
                i += n
                eslesti = True
                break
        if not eslesti:
            cikti.append(kelimeler[i])
            i += 1

    return " ".join(cikti), degisiklikler
