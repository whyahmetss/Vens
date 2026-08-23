"""
Command Center ve bağlam şeriti.

Şartname Bölüm 13. İki ayrı şey, aynı veriden beslenir:

**Bağlam şeriti** — "Paneller bağlama göre açılır, hep açık durmaz."
Sürekli görünen küçük bir şerit değil; yalnızca söylenecek bir şey varsa
belirir. Açık killzone yoksa, sonuçsuz kayıt yoksa, ihlal yoksa hiçbir şey
göstermez. Varsayılan durum minimaldir.

**Command Center** — "ayrı bir ekrandır ve çağrılınca açılır." Bölüm 13'ün
saydığı bölümler: aktif görev, agent durumu, piyasa, son aktiviteler,
hafıza, bildirimler, sistem.

Hiçbir bölüm uydurulmuş veri göstermez. Karşılığı olmayan bölüm "kurulu
değil" der — boş bir kutu, dolu görünen yanlış bir kutudan iyidir.
"""

import platform
from datetime import date, datetime

import psutil

from core.registry import Risk, Perm, skill, bilgi, alan, baslik, bosluk, ekran
from core import bildirim as bildirim_motoru
from core import denetci, log
from core import jurnal as depo
from core import kurallar as kural_motoru
from core.log import VERI
from skills.seans import durum as seans_durumu


def _acik_seans() -> list[str]:
    izinli = kural_motoru.yukle().deger("trading.izinli_seanslar", ())
    return [d["ad"] for d in seans_durumu() if d["acik"] and d["ad"] in izinli]


def _sonucsuz(kayitlar) -> list[dict]:
    return [k for k in kayitlar if not isinstance(k.get("sonuc_r"), (int, float))]


def _bugunku_ihlal(kayitlar) -> int:
    bugun = date.today().isoformat()
    return sum(len(k.get("ihlaller") or []) for k in kayitlar
               if str(k.get("islem_t", "")).startswith(bugun))


def baglam() -> list[dict]:
    """Şeritte gösterilecek çipler. Söylenecek bir şey yoksa boş liste."""
    cipler: list[dict] = []
    try:
        kayitlar = depo.hepsi()
    except Exception:
        kayitlar = []

    for ad in _acik_seans():
        cipler.append({"metin": f"{ad} açık", "tur": "acik"})

    n = len(_sonucsuz(kayitlar))
    if n:
        cipler.append({"metin": f"{n} pozisyon sonuçsuz", "tur": ""})

    ihlal = _bugunku_ihlal(kayitlar)
    if ihlal:
        cipler.append({"metin": f"bugün {ihlal} ihlal", "tur": "uyari"})

    bugun = len(depo.gun(date.today(), kayitlar)) if kayitlar else 0
    limit = kural_motoru.yukle().deger("trading.gunluk_islem_limiti")
    if bugun and limit is not None:
        cipler.append({"metin": f"{bugun}/{limit} işlem",
                       "tur": "uyari" if bugun > limit else ""})
    return cipler


@skill("merkez", "command center ekranı", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="merkez", takma_adlar=("komuta", "cc"))
async def _merkez(arg):
    kayitlar = depo.hepsi()
    kurallar = kural_motoru.yukle()
    out = [ekran("merkez")]

    # --- aktif görev: açık pozisyon, sistemdeki tek "devam eden iş" ---
    out.append(baslik("aktif görev"))
    acik = _sonucsuz(kayitlar)
    if acik:
        for k in acik[-4:]:
            out.append(alan(k.get("sembol", "?"),
                            f"{k.get('id')} · {str(k.get('islem_t',''))[5:16].replace('T',' ')}"))
    else:
        out.append(bilgi("açık pozisyon yok"))

    # --- agent durumu ---
    out.append(baslik("agent"))
    niyet_durum = "kapalı"
    try:
        from core import niyet, model
        niyet_durum = f"açık · {model.sec('niyet')}" if niyet.acik_mi() else niyet.neden_kapali()
    except Exception:
        pass
    out.append(alan("niyet çözücü", niyet_durum))
    out.append(alan("gece vardiyası", "kurulu değil"))     # Faz 8

    # --- piyasa: izlenen semboller jurnalden gelir, liste uydurulmaz ---
    out.append(baslik("piyasa"))
    semboller = []
    for k in reversed(kayitlar):
        s = k.get("sembol")
        if s and s not in semboller:
            semboller.append(s)
        if len(semboller) >= 5:
            break
    for ad in _acik_seans() or []:
        out.append(alan("seans", f"● {ad}", "acik"))
    if semboller:
        out.append(alan("son işlenen", ", ".join(semboller)))
    else:
        out.append(bilgi("jurnal boş — izlenecek sembol yok"))

    # --- son aktiviteler ---
    out.append(baslik("son aktivite"))
    for k in log.oku(5):
        out.append(alan(k["t"][11:19], f"{k['tur']}   {k.get('yetenek') or k.get('olay','')}"))

    # --- hafıza (Bölüm 7 aşama 2: sorgulanabilir dosyalar) ---
    out.append(baslik("hafıza"))
    for ad, yol in (("jurnal", depo.JURNAL), ("notlar", VERI / "notlar.jsonl"),
                    ("ihlaller", denetci.IHLALLER), ("olaylar", log.OLAYLAR)):
        n = sum(1 for _ in yol.open(encoding="utf-8")) if yol.exists() else 0
        out.append(alan(ad, f"{n} kayıt"))

    # --- bildirimler ---
    out.append(baslik("bildirim"))
    bekleyen = bildirim_motoru.bekleyenler()
    iletilen = bildirim_motoru.bugun_iletilen()
    out.append(alan("bekleyen", f"{len(bekleyen)}", "warn" if bekleyen else ""))
    out.append(alan("günlük bütçe", f"{iletilen}/{bildirim_motoru.GUNLUK_BUTCE}"))

    # --- sistem ---
    out.append(baslik("sistem"))
    vm = psutil.virtual_memory()
    out.append(alan("platform", f"{platform.system()} {platform.release()}"))
    out.append(alan("cpu", f"%{psutil.cpu_percent(interval=0.2):.0f}"))
    out.append(alan("bellek", f"%{vm.percent:.0f}"))
    out.append(alan("kurallar", "yüklü" if kurallar.okundu else "OKUNAMADI",
                    "" if kurallar.okundu else "warn"))
    return out
