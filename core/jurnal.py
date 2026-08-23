"""
Jurnal deposu — işlem kayıtlarının biçimi ve saklanması.

Şartname Bölüm 11. Kayıt alanları oradaki örnek kayıttan ve kurallar.yaml'ın
`zorunlu_alanlar` listesinden gelir; uydurulmaz.

Bu dosya kayıt tutar, yorum yapmaz. Kural denetimi core/denetci.py'de,
gösterim skills/jurnal.py'de. Analiz kodu bir günlük iş, veri aylar alır
(Bölüm 11) — bu yüzden depo baştan doğru alanları tutar.
"""

from __future__ import annotations

import json
import shlex
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from .log import VERI

JURNAL = VERI / "jurnal.jsonl"

# Sayısal alanlar. `sonuc_r` boş kalabilir: pozisyon henüz kapanmamıştır.
SAYI = ("risk", "hedef_r", "sonuc_r")
# evet/hayır alanları — `yasak` kurallarının dedektörleri bunlara bakar.
IKILI = ("stop_genisletme", "plan_disi_giris")
METIN = ("sembol", "yon", "seans", "setup", "giris_sebebi", "execution", "duygu")

YON = {"long": "long", "l": "long", "al": "long", "alis": "long", "alış": "long",
       "short": "short", "s": "short", "sat": "short", "satis": "short", "satış": "short"}

DOGRU = ("evet", "e", "true", "1", "var", "yes")
YANLIS = ("hayir", "hayır", "h", "false", "0", "yok", "no")


@dataclass(frozen=True)
class Ayristirma:
    veri: dict[str, Any]
    hatalar: tuple[str, ...]   # kayıt yazılamaz
    notlar: tuple[str, ...]    # yazılır ama kullanıcı bilsin


def ayristir(metin: str) -> Ayristirma:
    """`sembol=XAUUSD setup="sweep → MSS"` biçimini kayda çevirir.

    Serbest cümle değil, `alan=değer` çiftleri. Niyet çözücü Faz 3'te gelecek;
    o zamana kadar giriş deterministik olmalı, tahmin edilmemeli.
    """
    veri: dict[str, Any] = {}
    hatalar: list[str] = []
    notlar: list[str] = []

    try:
        parcalar = shlex.split(metin)
    except ValueError as e:
        return Ayristirma({}, (f"tırnak hatası: {e}",), ())

    for p in parcalar:
        if "=" not in p:
            hatalar.append(f"'{p}' anlaşılmadı — biçim: alan=değer")
            continue
        alan, _, ham = p.partition("=")
        alan = alan.strip().lower()
        ham = ham.strip()

        if not alan:
            hatalar.append(f"'{p}': alan adı boş")
            continue
        if not ham:
            continue                      # boş değer = alan verilmemiş sayılır

        if alan == "zaman":
            t, hata = _zaman(ham)
            if hata:
                hatalar.append(hata)
            else:
                veri["islem_t"] = t
        elif alan in SAYI:
            try:
                veri[alan] = float(ham.replace(",", ".").rstrip("rR%"))
            except ValueError:
                hatalar.append(f"{alan}: sayı olmalı (bulunan: {ham!r})")
        elif alan in IKILI:
            d = ham.lower()
            if d in DOGRU:
                veri[alan] = True
            elif d in YANLIS:
                veri[alan] = False
            else:
                hatalar.append(f"{alan}: evet/hayır olmalı (bulunan: {ham!r})")
        elif alan == "sembol":
            veri[alan] = ham.upper()
        elif alan == "yon":
            d = YON.get(ham.lower())
            if d is None:
                hatalar.append(f"yon: long ya da short olmalı (bulunan: {ham!r})")
            else:
                veri[alan] = d
        elif alan == "seans":
            veri[alan] = ham.lower()
        elif alan in METIN:
            veri[alan] = ham
        else:
            # Bilinmeyen alan reddedilmez: zorunlu_alanlar'a kullanıcı kendi
            # alanını ekleyebilmeli. Ama yazım hatası da böyle görünür, söylenir.
            veri[alan] = ham
            notlar.append(f"bilinmeyen alan '{alan}' — metin olarak kaydedildi")

    return Ayristirma(veri, tuple(hatalar), tuple(notlar))


def _zaman(ham: str) -> tuple[str | None, str | None]:
    """`SS:DD` (bugün) ya da `YYYY-AA-GG SS:DD`. İşlemin zamanı kaydın zamanı değildir."""
    for bicim, tam in (("%Y-%m-%d %H:%M", True), ("%H:%M", False)):
        try:
            d = datetime.strptime(ham, bicim)
        except ValueError:
            continue
        if not tam:
            bugun = date.today()
            d = d.replace(year=bugun.year, month=bugun.month, day=bugun.day)
        return d.isoformat(timespec="seconds"), None
    return None, f'zaman: "SS:DD" ya da "YYYY-AA-GG SS:DD" olmalı (bulunan: {ham!r})'


def _yeni_id(mevcut: set[str]) -> str:
    while True:
        kimlik = uuid.uuid4().hex[:4]
        if kimlik not in mevcut:
            return kimlik


def hazirla(veri: dict[str, Any]) -> dict[str, Any]:
    """Kaydı yazmadan kimlik ve zaman damgalarıyla tamamlar.

    Yazmadan önce denetim yapılabilsin diye ayrıdır: günlük limit gibi kurallar
    kaydın kendisini de sayar, ihlaller de kaydın içinde saklanır.
    """
    simdi = datetime.now().isoformat(timespec="seconds")
    return {"id": _yeni_id({k["id"] for k in hepsi() if "id" in k}),
            "t": simdi,
            "islem_t": veri.get("islem_t", simdi),
            **{a: d for a, d in veri.items() if a != "islem_t"}}


def yaz(kayit: dict[str, Any]) -> dict[str, Any]:
    """Depo append-only: kayıt silinmez, düzeltilmez. Jurnal olan biteni tutar."""
    with JURNAL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    return kayit


def duzelt(kimlik: str, veri: dict[str, Any]) -> dict[str, Any]:
    """Var olan kaydı düzeltir — ama eskisini SİLMEZ.

    Depo append-only kalır: düzeltme yeni bir satırdır. Jurnal olan biteni
    tutar; "risk %5'ti, sonra %1 yazdım" bilgisi kaybolursa jurnal disiplin
    aracı olmaktan çıkar. `hepsi()` okurken düzeltmeleri üstüne uygular ve
    kaydın kaç kez düzeltildiğini işaretler.
    """
    kayit = {"duzeltme": kimlik,
             "t": datetime.now().isoformat(timespec="seconds"), **veri}
    with JURNAL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    return kayit


def _satirlar() -> list[dict[str, Any]]:
    if not JURNAL.exists():
        return []
    out = []
    with JURNAL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue          # bozuk satır tüm jurnali kaybettirmemeli
    return out


def hepsi() -> list[dict[str, Any]]:
    """Kayıtların GÜNCEL hâli: taban satırların üstüne düzeltmeler uygulanmış."""
    kayitlar: dict[str, dict] = {}
    sira: list[str] = []
    duzeltmeler: dict[str, list[dict]] = {}

    for k in _satirlar():
        if "duzeltme" in k:
            duzeltmeler.setdefault(str(k["duzeltme"]), []).append(k)
        elif "id" in k:
            kayitlar[k["id"]] = dict(k)
            sira.append(k["id"])

    for kimlik, liste in duzeltmeler.items():
        hedef = kayitlar.get(kimlik)
        if hedef is None:
            continue              # sahibi olmayan düzeltme yok sayılır
        for d in liste:
            for alan, deger in d.items():
                if alan not in ("duzeltme", "t"):
                    hedef[alan] = deger
        hedef["duzeltildi"] = len(liste)
        hedef["duzeltme_t"] = liste[-1]["t"]

    out = [kayitlar[i] for i in sira]
    out.sort(key=lambda k: k.get("islem_t", k.get("t", "")))
    return out


def gun(tarih: date, kayitlar: list[dict] | None = None) -> list[dict[str, Any]]:
    ek = tarih.isoformat()
    return [k for k in (hepsi() if kayitlar is None else kayitlar)
            if str(k.get("islem_t", "")).startswith(ek)]


def bul(kimlik: str) -> dict[str, Any] | None:
    kimlik = kimlik.strip().lower()
    for k in hepsi():
        if k.get("id") == kimlik:
            return k
    return None
