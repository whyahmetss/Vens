"""
Uyum karnesi ve işlem kalitesi skoru.

`core/denetci.py` "hangi kural çiğnendi" sorusunu cevaplar. Bu dosya onu
playbook kontrol listesiyle birleştirip tek bir karneye çevirir:

    ✓ risk limiti          ✗ killzone
    ✓ liquidity sweep      ✗ fvg
    kalite: 45/100

Denetçiyi TÜKETİR, değiştirmez — ihlal tespiti tek yerde kalsın.

Hesap tamamen deterministiktir. 100'den başlar, her ihlal ve her işaretlenmemiş
kontrol maddesi ağırlığı kadar düşürür. Modele hiçbir şey sorulmaz: aynı kayıt
her zaman aynı skoru verir, yoksa skor bir ölçü olmaz.

Kontrol maddeleri Venüs'ün doğrulaması değil KULLANICININ BEYANIDIR — Venüs
grafiği göremez. Beyanın değeri, sonuç bilinmeden verilmiş ve kilitlenmiş
olmasından gelir (bkz. core/jurnal.SONRADAN_BILINEBILIR).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .denetci import Ihlal
from .playbook import Playbook, Setup

TABAN = 100


@dataclass(frozen=True)
class Madde:
    ad: str
    gecti: bool
    agirlik: int
    kaynak: str           # "kural" | "playbook"
    aciklama: str = ""


@dataclass(frozen=True)
class Karne:
    maddeler: tuple[Madde, ...]
    skor: int
    setup_tanimli: bool

    @property
    def gecen(self) -> int:
        return sum(1 for m in self.maddeler if m.gecti)

    @property
    def toplam(self) -> int:
        return len(self.maddeler)

    @property
    def temiz(self) -> bool:
        return self.gecen == self.toplam


def cikar(kayit: dict[str, Any], ihlaller: list[Ihlal], pb: Playbook) -> Karne:
    """Kaydın karnesini üretir."""
    maddeler: list[Madde] = []
    dusen = 0

    # ---- kural maddeleri ----
    # Aynı kuraldan birden fazla ihlal (örn. üç boş zorunlu alan) tek madde
    # sayılır ve bir kez ceza keser; yoksa tek bir eksiklik skoru yerle bir eder.
    ihlal_kurallari: dict[str, list[str]] = {}
    for i in ihlaller:
        ihlal_kurallari.setdefault(i.kural, []).append(i.mesaj)

    from .denetci import KURAL_ADLARI
    for kural in KURAL_ADLARI:
        mesajlar = ihlal_kurallari.get(kural)
        agirlik = pb.cezasi(kural)
        gecti = mesajlar is None
        if not gecti:
            dusen += agirlik
        maddeler.append(Madde(
            ad=kural.split(".", 1)[-1], gecti=gecti, agirlik=agirlik,
            kaynak="kural", aciklama="" if gecti else "; ".join(mesajlar)))

    # ---- playbook maddeleri ----
    setup: Setup | None = pb.setup(kayit.get("setup", ""))
    if setup is not None:
        isaretli = {str(x).strip().lower() for x in (kayit.get("kontrol") or [])}
        for m in setup.kontrol:
            gecti = m.ad in isaretli
            if not gecti:
                dusen += m.agirlik
            maddeler.append(Madde(ad=m.ad, gecti=gecti, agirlik=m.agirlik,
                                  kaynak="playbook",
                                  aciklama="" if gecti else m.soru))

    return Karne(maddeler=tuple(maddeler), skor=max(0, TABAN - dusen),
                 setup_tanimli=setup is not None)


def setup_min_rr(kayit: dict[str, Any], pb: Playbook) -> float | None:
    """Setup'ın kendi asgari R:R'si. Playbook doğrulayıcısı zaten gevşek
    değerleri düşürdüğü için buradan dönen değer her zaman en az kadar sıkıdır."""
    setup = pb.setup(kayit.get("setup", ""))
    return setup.min_rr if setup else None
