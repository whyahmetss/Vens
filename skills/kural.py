"""
Kurallar yeteneği — aktif kuralları ve dosyadaki sorunları gösterir.

Çekirdek okur ve doğrular (core/kurallar.py), bu dosya yalnızca sunar.
Kural değiştirmek buradan yapılmaz: kurallar.yaml düzenlenir. Kuralın tek
bir yeri olması, "Venüs'e söyledim ama dosyada yok" durumunu imkânsız kılar.
"""

from core.registry import Risk, Perm, skill, satir, bilgi, uyari, alan, baslik, bosluk
from core import kurallar as kural_motoru

# Ekran etiketi ve biçim. Alan adları kurallar.yaml'daki hâliyle kalır,
# kullanıcıya okunur karşılıkları gösterilir.
ETIKET = {
    "trading.gunluk_islem_limiti":      ("günlük işlem limiti",   lambda d: f"{d} işlem"),
    "trading.maks_risk_yuzde":          ("maks risk",             lambda d: f"%{d:g}"),
    "trading.min_rr":                   ("min R:R",               lambda d: f"{d:g}"),
    "trading.gunluk_maks_kayip_r":      ("günlük maks kayıp",     lambda d: f"{d:g}R"),
    "trading.kayip_sonrasi_bekleme_dk": ("kayıp sonrası bekleme", lambda d: f"{d} dk"),
    "trading.izinli_seanslar":          ("izinli seanslar",       ", ".join),
    "trading.zorunlu_alanlar":          ("zorunlu alanlar",       ", ".join),
    "trading.yasak":                    ("yasak",                 ", ".join),
    "calisma.gunluk_odak_saati":        ("günlük odak saati",     str),
    "calisma.gece_calisma_uyarisi_saat":("gece çalışma uyarısı",  str),
}

BOLUM_BASLIK = {"trading": "trading", "calisma": "çalışma"}


@skill("kurallar", "aktif kuralları göster", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="kurallar", takma_adlar=("kural",))
async def _kurallar(arg):
    k = kural_motoru.yukle()

    if not k.okundu:
        out = [uyari("kural dosyası okunamadı — hiçbir kural uygulanmıyor.")]
        out += [satir(f"  {s}") for s in k.sorunlar]
        out.append(bilgi(f"  dosya: {k.dosya}"))
        return out

    out = []
    for bolum, alanlar in k.bolumler.items():
        out.append(baslik(BOLUM_BASLIK.get(bolum, bolum)))
        for ad, deger in alanlar.items():
            etiket, bicim = ETIKET.get(f"{bolum}.{ad}", (ad, str))
            out.append(alan(etiket, bicim(deger)))
        out.append(bosluk())

    if not k.bolumler:
        out.append(bilgi("tanımlı kural yok — kurallar.yaml boş."))

    if k.sorunlar:
        out.append(baslik(f"{len(k.sorunlar)} sorun — bu satırlar yok sayılıyor"))
        out += [alan(s.yol, s.mesaj, "warn") for s in k.sorunlar]
        out.append(bosluk())

    out.append(bilgi(f"kaynak: {k.dosya}"))
    return out


@skill("ihlaller", "kaydedilmiş kural ihlalleri", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="ihlaller [adet]")
async def _ihlaller(arg):
    from core import denetci

    try:
        n = int(arg.strip()) if arg.strip() else 20
    except ValueError:
        n = 20

    kayitlar = denetci.oku(n)
    if not kayitlar:
        return [bilgi("kayıtlı ihlal yok.")]

    # İşlemin zamanı gösterilir, kaydın yazıldığı zaman değil: bir günlük
    # işlemler gece toplu girilmiş olabilir, o zaman kayıt saati yanıltır.
    out = [alan(f"{str(i.get('islem_t') or i['t'])[5:16].replace('T', ' ')}  "
                f"{i.get('sembol') or '—'}", i["mesaj"], "warn") for i in kayitlar]

    # Hangi kuralı ne sıklıkla çiğnediğin, tek tek ihlallerden daha çok şey söyler.
    sayac: dict[str, int] = {}
    for i in kayitlar:
        sayac[i["kural"]] = sayac.get(i["kural"], 0) + 1
    out.append(bosluk())
    out.append(baslik(f"son {len(kayitlar)} ihlalin dağılımı"))
    for kural, adet in sorted(sayac.items(), key=lambda x: -x[1]):
        out.append(alan(kural, adet))
    return out
