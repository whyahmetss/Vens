"""
Kalıcı profil — Venüs'ün kullanıcı hakkında bildikleri.

Şartname Bölüm 7, Hafıza Aşama 3. Bölümün şartı pazarlığa açık değildir:

    "Her kayıt kullanıcı tarafından görülebilir, düzenlenebilir, silinebilir.
     GİZLİ HAFIZA YOK."

Bu yüzden profil iki tür kayıttan oluşur ve ikisi de görünür:

**Çıkarılan** — Venüs'ün verinden ürettiği. Saklanmaz, her seferinde yeniden
hesaplanır ve yanında NEREDEN çıktığı yazar. Saklanmaması bilinçlidir: saklanan
bir çıkarım eskir ve kullanıcı onu doğrulayamaz. Katılmadığın bir çıkarımı
`gizle` ile susturabilirsin.

**Beyan** — senin Venüs'e söylediğin. Dosyada durur, düzenlenir, silinir.

Çıkarımlar DETERMİNİSTİKTİR. Modele "bu kullanıcı nasıl biri" sorulmaz —
o soru, cevabı doğrulanamayan bir hafıza üretir. Burada yalnızca sayılabilir
şeyler var: ne zaman çalışıyorsun, hangi komutu kullanıyorsun, hangi hatayı
tekrarlıyorsun.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from . import log
from .log import VERI

PROFIL = VERI / "profil.jsonl"

# Bir çıkarımın söylenmesi için gereken asgari veri. Altında Venüs susar:
# üç olaydan "en aktif saatin şu" diye bir sonuç çıkarmak uydurmaktır.
ASGARI_OLAY = 20
ASGARI_KAYIT = 5


@dataclass(frozen=True)
class Bilgi:
    ad: str
    deger: str
    kaynak: str            # bu nereden çıktı — doğrulanabilir olmalı
    tur: str               # "cikarim" | "beyan"
    kimlik: str = ""       # beyanlar için; silmek/düzenlemek için


def _satirlar() -> list[dict]:
    if not PROFIL.exists():
        return []
    out = []
    with PROFIL.open(encoding="utf-8") as f:
        for s in f:
            s = s.strip()
            if s:
                try:
                    out.append(json.loads(s))
                except json.JSONDecodeError:
                    continue
    return out


def _yaz(kayit: dict) -> None:
    with PROFIL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


# ---- beyanlar (senin söylediklerin) -------------------------------------

def beyanlar() -> list[Bilgi]:
    """Silinmemiş beyanlar. Depo append-only; silme bir 'sil' satırıdır."""
    silinen = {k["sil"] for k in _satirlar() if "sil" in k}
    son: dict[str, dict] = {}
    for k in _satirlar():
        if "beyan" in k and k.get("kimlik") not in silinen:
            son[k["beyan"]] = k          # aynı anahtar tekrar yazılırsa sonuncu geçerli
    return [Bilgi(ad=k["beyan"], deger=k.get("deger", ""),
                  kaynak=f"sen söyledin · {k['t'][:10]}", tur="beyan",
                  kimlik=k.get("kimlik", ""))
            for k in son.values()]


def beyan_ekle(ad: str, deger: str) -> dict:
    import uuid
    kayit = {"beyan": ad, "deger": deger, "kimlik": uuid.uuid4().hex[:4],
             "t": datetime.now().isoformat(timespec="seconds")}
    _yaz(kayit)
    return kayit


def unut(kimlik: str) -> bool:
    if not any(b.kimlik == kimlik for b in beyanlar()):
        return False
    _yaz({"sil": kimlik, "t": datetime.now().isoformat(timespec="seconds")})
    return True


# ---- gizlenen çıkarımlar -------------------------------------------------

def gizlenenler() -> set[str]:
    acilan = {k["goster"] for k in _satirlar() if "goster" in k}
    return {k["gizle"] for k in _satirlar() if "gizle" in k} - acilan


def gizle(ad: str) -> None:
    _yaz({"gizle": ad, "t": datetime.now().isoformat(timespec="seconds")})


def goster(ad: str) -> None:
    _yaz({"goster": ad, "t": datetime.now().isoformat(timespec="seconds")})


# ---- çıkarımlar (verinden) ----------------------------------------------

def cikarimlar() -> list[Bilgi]:
    """Yalnızca sayılabilir olanlar. Yeterli veri yoksa o satır hiç çıkmaz."""
    out: list[Bilgi] = []
    olaylar = log.hepsi()
    komutlar = [o for o in olaylar if o.get("tur") == "komut" and o.get("yetenek")]

    if len(olaylar) >= ASGARI_OLAY:
        ilk = min(o["t"] for o in olaylar)[:10]
        gun = len({o["t"][:10] for o in olaylar})
        out.append(Bilgi("kullanım", f"{ilk} tarihinden beri, {gun} ayrı gün",
                         f"{len(olaylar)} olay", "cikarim"))

        saatler = Counter(int(o["t"][11:13]) for o in olaylar if len(o.get("t", "")) > 13)
        if saatler:
            en = saatler.most_common(3)
            out.append(Bilgi("aktif saatlerin",
                             ", ".join(f"{s:02d}:00" for s, _ in en),
                             f"{sum(saatler.values())} olayın dağılımı", "cikarim"))

    if len(komutlar) >= ASGARI_OLAY:
        sik = Counter(o["yetenek"] for o in komutlar).most_common(4)
        out.append(Bilgi("en çok kullandığın",
                         ", ".join(f"{a} ({n})" for a, n in sik),
                         f"{len(komutlar)} komut", "cikarim"))

    # --- trading tarafı, yalnızca yeterli kayıt varsa ---
    try:
        from . import analiz, jurnal
        kapali = analiz.kapali(jurnal.hepsi())
    except Exception:
        kapali = []

    if len(kapali) >= ASGARI_KAYIT:
        seans = Counter(k.get("seans") for k in kapali if k.get("seans"))
        if seans:
            ad, n = seans.most_common(1)[0]
            out.append(Bilgi("en çok işlem yaptığın seans", f"{ad} ({n} işlem)",
                             f"{len(kapali)} sonuçlanmış işlem", "cikarim"))
        sembol = Counter(k.get("sembol") for k in kapali if k.get("sembol"))
        if sembol:
            ad, n = sembol.most_common(1)[0]
            out.append(Bilgi("en çok işlem yaptığın sembol", f"{ad} ({n} işlem)",
                             f"{len(kapali)} sonuçlanmış işlem", "cikarim"))
        try:
            from . import koc
            zararli = [d for d in analiz.davranislar(jurnal.hepsi())
                       if d.adet >= koc.ASGARI_TEKRAR and d.toplam_r <= -koc.ASGARI_ETKI]
            if zararli:
                out.append(Bilgi("tekrarlayan hataların",
                                 ", ".join(f"{d.ad} ({d.adet}x)" for d in zararli[:4]),
                                 "koç eşiklerini geçenler", "cikarim"))
        except Exception:
            pass

    gizli = gizlenenler()
    return [b for b in out if b.ad not in gizli]


def hepsi() -> tuple[list[Bilgi], list[Bilgi], set[str]]:
    """(çıkarımlar, beyanlar, gizlenenler)"""
    return cikarimlar(), beyanlar(), gizlenenler()
