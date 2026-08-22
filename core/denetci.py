"""
Kural ihlali denetleyicisi.

Şartname Bölüm 5: **deterministik kod, deterministik sonuç.** LLM'e hiçbir şey
sorulmaz. Bir ihlalin yakalanması modelin o gün nasıl bir metin ürettiğine
bağlı olamaz.

Ve: **engellemez, kaydeder.** Nihai karar kullanıcınındır (kimlik.md). Venüs
kuralı hatırlatır, sonra çekilir. İhlaller `~/.venus/ihlaller.jsonl`'a yazılır;
uzun vadede en değerli veri budur — hangi kuralı, hangi durumda, ne sıklıkla.

Veri eksikse kural denetlenmez, uydurulmaz: `risk` girilmemişse risk kuralı
sessizce atlanır. O alanın girilmesini istiyorsan kural dosyasındaki
`zorunlu_alanlar` listesine ekle — o zaman eksikliği ihlal olarak yakalanır.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from . import log
from .kurallar import Kurallar
from .log import VERI

IHLALLER = VERI / "ihlaller.jsonl"


@dataclass(frozen=True)
class Ihlal:
    kural: str      # "trading.gunluk_islem_limiti"
    mesaj: str      # kullanıcıya gösterilecek tek satır

    def __str__(self) -> str:
        return self.mesaj


def _sayi(kayit: dict, alan: str) -> float | None:
    d = kayit.get(alan)
    return float(d) if isinstance(d, (int, float)) and not isinstance(d, bool) else None


def _dolu(kayit: dict, alan: str) -> bool:
    d = kayit.get(alan)
    if d is None:
        return False
    if isinstance(d, str):
        return bool(d.strip())
    return True


def denetle(kayit: dict[str, Any], kurallar: Kurallar,
            gunun_kayitlari: list[dict[str, Any]] | None = None) -> list[Ihlal]:
    """Tek bir jurnal kaydını kurallara karşı denetler.

    `gunun_kayitlari`: aynı güne ait, bu kayıt DAHİL tüm kayıtlar. Günlük limit
    ve kayıp sonrası bekleme gibi kurallar tek kayda bakarak denetlenemez.
    """
    gunun_kayitlari = gunun_kayitlari or [kayit]
    ihlaller: list[Ihlal] = []

    # --- zorunlu alanlar ---
    for alan in kurallar.deger("trading.zorunlu_alanlar", ()):
        if not _dolu(kayit, alan):
            ihlaller.append(Ihlal("trading.zorunlu_alanlar",
                                  f"zorunlu alan boş: {alan}"))

    # --- günlük işlem limiti ---
    limit = kurallar.deger("trading.gunluk_islem_limiti")
    if limit is not None:
        sira = len(gunun_kayitlari)
        if sira > limit:
            ihlaller.append(Ihlal("trading.gunluk_islem_limiti",
                                  f"günün {sira}. işlemi — limit {limit}"))

    # --- işlem başına risk ---
    maks_risk = kurallar.deger("trading.maks_risk_yuzde")
    risk = _sayi(kayit, "risk")
    if maks_risk is not None and risk is not None and risk > maks_risk:
        ihlaller.append(Ihlal("trading.maks_risk_yuzde",
                              f"risk %{risk:g} — limit %{maks_risk:g}"))

    # --- planlanan R:R ---
    min_rr = kurallar.deger("trading.min_rr")
    hedef = _sayi(kayit, "hedef_r")
    if min_rr is not None and hedef is not None and hedef < min_rr:
        ihlaller.append(Ihlal("trading.min_rr",
                              f"hedef {hedef:g}R — en az {min_rr:g}R olmalıydı"))

    # --- günlük kayıp tavanı (net) ---
    maks_kayip = kurallar.deger("trading.gunluk_maks_kayip_r")
    if maks_kayip is not None:
        net = sum(r for r in (_sayi(k, "sonuc_r") for k in gunun_kayitlari)
                  if r is not None)
        if net <= -maks_kayip:
            ihlaller.append(Ihlal("trading.gunluk_maks_kayip_r",
                                  f"günlük net {net:+.2f}R — tavan -{maks_kayip:g}R"))

    # --- seans ---
    izinli = kurallar.deger("trading.izinli_seanslar")
    seans = (kayit.get("seans") or "").strip().lower()
    if izinli and seans and seans not in izinli:
        ihlaller.append(Ihlal("trading.izinli_seanslar",
                              f"izinli olmayan seans: {seans} "
                              f"(izinli: {', '.join(izinli)})"))

    # --- yasak davranışlar ---
    yasak = kurallar.deger("trading.yasak", ())
    if "stop_genisletme" in yasak and kayit.get("stop_genisletme") is True:
        ihlaller.append(Ihlal("trading.yasak", "stop genişletildi"))
    if "plan_disi_giris" in yasak and kayit.get("plan_disi_giris") is True:
        ihlaller.append(Ihlal("trading.yasak", "plan dışı giriş"))
    if "kayip_sonrasi_bekleme_ihlali" in yasak:
        ihlal = _bekleme_ihlali(kayit, kurallar, gunun_kayitlari)
        if ihlal:
            ihlaller.append(ihlal)

    return ihlaller


def _bekleme_ihlali(kayit: dict, kurallar: Kurallar, gunun: list[dict]) -> Ihlal | None:
    """Kayıptan sonra beklenmeden girilen işlem — 'revenge trade'in ölçülebilir hâli."""
    bekleme = kurallar.deger("trading.kayip_sonrasi_bekleme_dk")
    if bekleme is None:
        return None
    su_an = _zaman(kayit)
    if su_an is None:
        return None

    # Bu kayıttan önceki en yakın kayıp.
    onceki = [k for k in gunun
              if k.get("id") != kayit.get("id")
              and _zaman(k) is not None and _zaman(k) < su_an
              and (_sayi(k, "sonuc_r") or 0) < 0]
    if not onceki:
        return None

    son_kayip = max(onceki, key=_zaman)
    gecen = (su_an - _zaman(son_kayip)).total_seconds() / 60
    if gecen >= bekleme:
        return None
    return Ihlal("trading.yasak",
                 f"kayıptan {gecen:.0f} dk sonra giriş — {bekleme} dk beklenmeliydi")


def _zaman(kayit: dict) -> datetime | None:
    ham = kayit.get("islem_t") or kayit.get("t")
    try:
        return datetime.fromisoformat(ham) if ham else None
    except (TypeError, ValueError):
        return None


def kaydet(kayit: dict[str, Any], ihlaller: list[Ihlal]) -> None:
    """İhlalleri kalıcı dosyaya yazar. Boş listede dosyaya dokunulmaz."""
    if not ihlaller:
        return
    simdi = datetime.now().isoformat(timespec="seconds")
    with IHLALLER.open("a", encoding="utf-8") as f:
        for i in ihlaller:
            f.write(json.dumps({"t": simdi,
                                "islem_t": kayit.get("islem_t"),
                                "kayit": kayit.get("id"),
                                "sembol": kayit.get("sembol"),
                                "kural": i.kural,
                                "mesaj": i.mesaj}, ensure_ascii=False) + "\n")
    log.yaz("ihlal", kayit=kayit.get("id"), adet=len(ihlaller),
            kurallar=[i.kural for i in ihlaller])


def oku(n: int = 20) -> list[dict[str, Any]]:
    if not IHLALLER.exists():
        return []
    kayitlar = []
    with IHLALLER.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                kayitlar.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return kayitlar[-n:]
