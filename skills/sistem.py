import platform
from datetime import datetime
from pathlib import Path

import psutil

from core.registry import Risk, Perm, skill, satir, bilgi, hepsi, alan, baslik, bosluk
from core import log

RENK = {"yesil": "●", "sari": "●", "turuncu": "▲", "kirmizi": "■"}


@skill("yardim", "yetenek listesi", Risk.YESIL, takma_adlar=("help", "?"))
async def _yardim(arg):
    out = [baslik(f"{len(hepsi())} yetenek")]
    for s in hepsi():
        isaret = RENK.get(s.risk.value, "●")
        out.append(alan(f"{isaret} {s.ad}", s.aciklama,
                        "warn" if s.risk.value == "turuncu" else ""))
    out.append(bosluk())
    out.append(bilgi("● doğrudan çalışır   ▲ onay ister"))
    return out


AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
GUNLER = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")


@skill("saat", "zaman damgası", Risk.YESIL)
async def _saat(arg):
    d = datetime.now()
    # locale'e güvenilmez; makineden makineye değişir.
    return [satir(d.strftime("%H:%M:%S")),
            bilgi(f"{d.day} {AYLAR[d.month - 1]} {d.year}, {GUNLER[d.weekday()]}")]


@skill("sistem", "makine durumu", Risk.YESIL, izinler=(Perm.OKUMA,))
async def _sistem(arg):
    vm = psutil.virtual_memory()
    du = psutil.disk_usage(str(Path.home()))
    return [
        alan("platform", f"{platform.system()} {platform.release()}"),
        alan("cpu", f"%{psutil.cpu_percent(interval=0.3):.0f}   {psutil.cpu_count()} çekirdek"),
        alan("bellek", f"%{vm.percent:.0f}   {vm.used/1e9:.1f} / {vm.total/1e9:.1f} GB"),
        alan("disk", f"%{du.percent:.0f}   {du.free/1e9:.0f} GB boş"),
    ]


@skill("log", "son olayları göster", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="log [adet]")
async def _log(arg):
    try:
        n = int(arg.strip()) if arg.strip() else 15
    except ValueError:
        n = 15
    kayitlar = log.oku(n)
    if not kayitlar:
        return [bilgi("henüz kayıt yok.")]
    out = []
    for k in kayitlar:
        ozet = k.get("yetenek") or k.get("girdi", "")
        sonuc = k.get("sonuc", "")
        out.append(alan(f"{k['t'][11:19]}  {k['tur']}",
                        f"{ozet}{'   ' + sonuc if sonuc else ''}"))
    return out
