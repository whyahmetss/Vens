import platform
from datetime import datetime
from pathlib import Path

import psutil

from core.registry import Risk, Perm, skill, satir, bilgi, hepsi
from core import log

RENK = {"yesil": "●", "sari": "●", "turuncu": "▲", "kirmizi": "■"}


@skill("yardim", "yetenek listesi", Risk.YESIL, takma_adlar=("help", "?"))
async def _yardim(arg):
    out = [bilgi("yetenekler:")]
    for s in hepsi():
        isaret = RENK.get(s.risk.value, "●")
        out.append(satir(f"  {isaret} {s.ad:<11} {s.aciklama}"))
    out.append(bilgi(""))
    out.append(bilgi("● yeşil/sarı: doğrudan çalışır   ▲ turuncu: onay ister"))
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
        satir(f"platform : {platform.system()} {platform.release()}"),
        satir(f"cpu      : %{psutil.cpu_percent(interval=0.3):.0f}  ({psutil.cpu_count()} çekirdek)"),
        satir(f"bellek   : %{vm.percent:.0f}  ({vm.used/1e9:.1f} / {vm.total/1e9:.1f} GB)"),
        satir(f"disk     : %{du.percent:.0f}  ({du.free/1e9:.0f} GB boş)"),
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
        saat = k["t"][11:19]
        ozet = k.get("yetenek") or k.get("girdi", "")
        sonuc = k.get("sonuc", "")
        out.append(satir(f"  {saat}  {k['tur']:<13} {ozet:<12} {sonuc}"))
    return out
