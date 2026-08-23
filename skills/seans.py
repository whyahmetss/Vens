"""
Seans / killzone hatırlatıcısı.

Şartname Bölüm 6 ve Değişmez 4: **sinyal değil hatırlatma.** Bu dosya
seansın başladığını söyler. Yön, giriş, seviye, "fırsat var" — hiçbiri yok
ve eklenmemeli.

Killzone saatleri New York yerel saatinde tanımlıdır, çünkü ICT çerçevesi
onları oraya göre tarif eder ve ABD yaz saatiyle kayarlar. Kullanıcının
saatine dönüştürme zoneinfo ile yapılır (stdlib, yeni bağımlılık yok).

Hangi seansların hatırlatılacağı uydurulmaz: `kurallar.yaml`'daki
`izinli_seanslar` listesi neyse o. İşlem yapmadığın seans için uyarı almak
bildirim bütçesini boşa harcar (Bölüm 12).
"""

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from core.registry import Risk, Perm, skill, bilgi, uyari, alan, baslik, bosluk
from core.zamanlayici import periyodik
from core.bildirim import Seviye, bildir, hepsi as bildirim_hepsi
from core import kurallar as kural_motoru

NY = ZoneInfo("America/New_York")

# (ad, başlangıç, bitiş) — New York yerel saati, 24 saat.
KILLZONE = (
    ("asya",          (20, 0), (0, 0)),
    ("londra",        (2, 0),  (5, 0)),
    ("new_york_am",   (7, 0),  (10, 0)),
    ("londra_kapanis", (10, 0), (12, 0)),
    ("new_york_pm",   (13, 30), (16, 0)),
)


def yerel_dilim() -> ZoneInfo:
    return ZoneInfo(os.environ.get("VENUS_SAAT_DILIMI", "Europe/Istanbul"))


def _bugun_ny(saat, gun: date) -> datetime:
    return datetime(gun.year, gun.month, gun.day, saat[0], saat[1], tzinfo=NY)


def _aralik(bas, bit, gun: date) -> tuple[datetime, datetime]:
    b = _bugun_ny(bas, gun)
    s = _bugun_ny(bit, gun)
    if s <= b:                       # gece yarısını aşan seans (asya 20:00→00:00)
        s += timedelta(days=1)
    return b, s


def durum(simdi: datetime | None = None) -> list[dict]:
    """Her killzone'un kullanıcı saatindeki aralığı ve şu anki durumu."""
    yerel = yerel_dilim()
    simdi = simdi or datetime.now(NY)
    simdi_ny = simdi.astimezone(NY)
    out = []
    for ad, bas, bit in KILLZONE:
        b, s = _aralik(bas, bit, simdi_ny.date())
        if s < simdi_ny:             # bugünkü aralık geçtiyse yarınkini göster
            b, s = _aralik(bas, bit, simdi_ny.date() + timedelta(days=1))
        elif b > simdi_ny:           # bugün henüz başlamadıysa dünden sarkıyor mu
            db, ds = _aralik(bas, bit, simdi_ny.date() - timedelta(days=1))
            if db <= simdi_ny < ds:
                b, s = db, ds
        out.append({"ad": ad, "bas": b.astimezone(yerel), "bit": s.astimezone(yerel),
                    "acik": b <= simdi_ny < s})
    return out


@skill("seans", "killzone saatleri ve durumu", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="seans")
async def _seans(arg):
    izinli = kural_motoru.yukle().deger("trading.izinli_seanslar", ())
    yerel = yerel_dilim()
    out = [baslik(f"killzone · {yerel.key}")]
    for d in durum():
        # Açık olan seans vurgulanır, izlenmeyen sönükleşir — durum renkle
        # anlatılır, boşlukla değil.
        if d["acik"]:
            cls = "acik"
        elif d["ad"] in izinli:
            cls = ""
        else:
            cls = "dim"
        etiket = ("● " if d["acik"] else "") + d["ad"]
        out.append(alan(etiket, f"{d['bas']:%H:%M} — {d['bit']:%H:%M}", cls))
    if not izinli:
        out.append(bosluk())
        out.append(uyari("kurallar.yaml'da izinli seans tanımlı değil — "
                         "hiçbir seans hatırlatılmaz."))
    return out


def _bildirildi_mi(ad: str, gun: date) -> bool:
    kaynak = f"seans:{ad}:{gun.isoformat()}"
    return any(b.kaynak == kaynak for b in bildirim_hepsi())


@periyodik(60, ad="killzone")
async def _killzone_kontrolu():
    """Dakikada bir bakar; izinli bir killzone açıldıysa bir kez hatırlatır.

    Tekrar koruması bildirim deposundan okunur, bellekten değil — Venüs gün
    içinde yeniden başlatılırsa aynı seans ikinci kez hatırlatılmamalı.
    """
    izinli = kural_motoru.yukle().deger("trading.izinli_seanslar", ())
    if not izinli:
        return
    bugun = datetime.now(NY).date()
    for d in durum():
        if not d["acik"] or d["ad"] not in izinli:
            continue
        if _bildirildi_mi(d["ad"], bugun):
            continue
        bildir(Seviye.YUKSEK,
               f"{d['ad']} killzone başladı — {d['bas']:%H:%M} · {d['bit']:%H:%M}",
               f"seans:{d['ad']}:{bugun.isoformat()}")
