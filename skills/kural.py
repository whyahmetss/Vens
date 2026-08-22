"""
Kurallar yeteneği — aktif kuralları ve dosyadaki sorunları gösterir.

Çekirdek okur ve doğrular (core/kurallar.py), bu dosya yalnızca sunar.
Kural değiştirmek buradan yapılmaz: kurallar.yaml düzenlenir. Kuralın tek
bir yeri olması, "Venüs'e söyledim ama dosyada yok" durumunu imkânsız kılar.
"""

from core.registry import Risk, Perm, skill, satir, bilgi, uyari, vurgu
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
        out.append(vurgu(BOLUM_BASLIK.get(bolum, bolum)))
        for alan, deger in alanlar.items():
            etiket, bicim = ETIKET.get(f"{bolum}.{alan}", (alan, str))
            out.append(satir(f"  {etiket:<22} {bicim(deger)}"))
        out.append(bilgi(""))

    if not k.bolumler:
        out.append(bilgi("tanımlı kural yok — kurallar.yaml boş."))

    if k.sorunlar:
        out.append(uyari(f"{len(k.sorunlar)} sorun var, bu satırlar yok sayılıyor:"))
        out += [satir(f"  {s}") for s in k.sorunlar]
        out.append(bilgi(""))

    out.append(bilgi(f"kaynak: {k.dosya}"))
    return out
