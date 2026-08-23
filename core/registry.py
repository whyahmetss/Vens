"""
Yetenek kayıt defteri.

Şartname Bölüm 2 (risk sınıfları) ve Bölüm 6 (yetenek sözleşmesi).
Her yetenek risk sınıfını ve gerekli izinlerini BEYAN ETMEK ZORUNDADIR.
Beyansız yetenek kaydedilemez.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class Risk(str, Enum):
    """Bölüm 2 — yanlış çalıştığında ne kaybettirdiğine göre."""
    YESIL   = "yesil"     # geri dönülebilir / zararsız → onaysız
    SARI    = "sari"      # iz bırakır → çalışır, loglanır
    TURUNCU = "turuncu"   # zor geri alınır → her seferinde onay
    KIRMIZI = "kirmizi"   # geri alınamaz → v1'de YOK


class Perm(str, Enum):
    OKUMA      = "okuma"
    YAZMA      = "yazma"
    CALISTIRMA = "calistirma"
    SILME      = "silme"
    TARAYICI   = "tarayici"
    ILETISIM   = "iletisim"
    AG         = "ag"          # dış ağa okuma erişimi


@dataclass
class Skill:
    ad: str
    aciklama: str
    risk: Risk
    izinler: tuple[Perm, ...]
    fn: Callable
    kullanim: str = ""
    takma_adlar: tuple[str, ...] = field(default_factory=tuple)


REGISTRY: dict[str, Skill] = {}   # ad -> Skill
_INDEX: dict[str, Skill] = {}     # ad + takma adlar -> Skill


def skill(ad: str, aciklama: str, risk: Risk, izinler=(), kullanim="", takma_adlar=()):
    def deco(fn):
        if risk is Risk.KIRMIZI:
            raise ValueError(f"'{ad}': KIRMIZI sınıf yetenek v1'de kaydedilemez.")
        s = Skill(ad=ad, aciklama=aciklama, risk=risk, izinler=tuple(izinler),
                  fn=fn, kullanim=kullanim, takma_adlar=tuple(takma_adlar))
        REGISTRY[ad] = s
        _INDEX[ad] = s
        for t in takma_adlar:
            _INDEX[t] = s
        return fn
    return deco


def bul(ad: str) -> Skill | None:
    return _INDEX.get(ad.lower())


def hepsi() -> list[Skill]:
    return sorted(REGISTRY.values(), key=lambda s: s.ad)


# ---- çıktı yardımcıları -------------------------------------------------
def satir(text: str, cls: str = "") -> dict:
    return {"text": text, "cls": cls}


def bilgi(t):  return satir(t, "dim")
def uyari(t):  return satir(t, "warn")
def vurgu(t):  return satir(t, "hi")


def alan(etiket: str, deger, cls: str = "") -> dict:
    """İki sütunlu alan.

    Yetenek boşlukla hizalama YAPMAZ. `f"{etiket:<22}"` biçiminde bir çıktı,
    gösterim kararını yeteneğin içine kaçırır (Değişmez 6) ve kabuğu bir
    terminal dökümüne mahkûm eder. Hizayı ve düzeni kabuk kurar.
    """
    return {"etiket": etiket, "deger": "" if deger is None else str(deger), "cls": cls}


def baslik(t: str) -> dict:
    """Panel içi bölüm başlığı."""
    return {"baslik": t}


def bosluk() -> dict:
    return {"bosluk": True}


def ekran(ad: str) -> dict:
    """Bu yanıt akışa değil, çağrılınca açılan ayrı bir ekrana yazılsın.

    Sunum ipucudur, sunum kararı değil — `cls` gibi. Ekranın neye benzediğine
    kabuk karar verir (Bölüm 13: Command Center çağrılınca açılır).
    """
    return {"ekran": ad}
