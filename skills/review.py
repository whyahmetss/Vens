"""
Review ve koç yetenekleri.

Çekirdek hesaplar (core/review.py, core/koc.py), bu dosya sunar.
İkisi de gözlem üretir, emir üretmez (Değişmez 4).
"""

from core.registry import Risk, Perm, skill, satir, bilgi, uyari, alan, baslik, bosluk
from core import jurnal as depo
from core import koc as koc_motoru
from core import kurallar as kural_motoru
from core import playbook as playbook_motoru
from core import review as motor


def _setup(kayit):
    pb = playbook_motoru.yukle(kurallar=kural_motoru.yukle())
    return pb.setup(kayit.get("setup", ""))


@skill("review", "plan ile gerçeğin karşılaştırması", Risk.YESIL,
       izinler=(Perm.OKUMA,), kullanim="review [id]", takma_adlar=("incele",))
async def _review(arg):
    kayitlar = depo.hepsi()
    if not kayitlar:
        return [bilgi("jurnal boş.")]

    kimlik = arg.strip().lower()
    if not kimlik:
        bekleyen = motor.incelenmemis(kayitlar)
        if not bekleyen:
            return [bilgi("inceleme bekleyen kayıt yok."),
                    bilgi("tek kayıt için: review <id>")]
        out = [baslik(f"{len(bekleyen)} kayıt incelenmemiş")]
        for k in bekleyen[-10:]:
            out.append(alan(k.get("id", "????"),
                            f"{k.get('sembol','?')}  {k.get('sonuc_r'):+.2f}R  "
                            f"çıkış sebebi yok"))
        out.append(bosluk())
        out.append(bilgi("çıkış sebebini yazmak için: "
                         "tamamla <id> cikis_sebebi=\"...\""))
        return out

    k = depo.bul(kimlik)
    if k is None:
        return [uyari(f"kayıt bulunamadı: {kimlik}")]

    gozlemler = motor.incele(k, _setup(k))
    sapma = motor.sapma_sayisi(gozlemler)

    out = [baslik(f"{k.get('sembol','?')} · {kimlik}"
                  + (f" · {sapma} sapma" if sapma else " · sapma yok"))]

    out.append(baslik("plan (girişte söylediğin)"))
    for ad, etiket in (("giris_sebebi", "giriş sebebi"), ("htf", "htf"),
                       ("likidite", "likidite"), ("bias", "bias")):
        if k.get(ad):
            out.append(alan(etiket, k[ad]))
    if k.get("kontrol"):
        out.append(alan("kontrol", ", ".join(k["kontrol"])))

    out.append(baslik("gerçek (sonra olan)"))
    for ad, etiket in (("cikis_sebebi", "çıkış sebebi"), ("execution", "execution")):
        if k.get(ad):
            out.append(alan(etiket, k[ad]))
    for n in (k.get("notlar") or []):
        out.append(alan("sonradan not", n.get("metin", ""), "warn"))

    out.append(baslik("karşılaştırma"))
    for g in gozlemler:
        out.append(alan(g.ad, g.metin, "warn" if g.sapma else ""))
    return out


@skill("koc", "tekrarlanan davranışları yüzüne tutar", Risk.YESIL,
       izinler=(Perm.OKUMA,), kullanim="koc", takma_adlar=("koç",))
async def _koc(arg):
    kayitlar = depo.hepsi()
    islem, davranis, net, etkilenen = koc_motoru.ozet(kayitlar)

    if islem < koc_motoru.ASGARI_ISLEM:
        return [bilgi(f"{islem} sonuçlanmış işlem var — "
                      f"en az {koc_motoru.ASGARI_ISLEM} gerek."),
                bilgi("az örneğe dayanarak seni sorguya çekmek, "
                      "gürültüye göre davranmaya iter.")]

    bulgular = koc_motoru.bulgular(kayitlar)
    if not bulgular:
        return [baslik(f"{islem} işlem"),
                bilgi("eşikleri geçen tekrarlanan davranış yok."),
                bilgi(f"(en az {koc_motoru.ASGARI_TEKRAR} tekrar ve "
                      f"{koc_motoru.ASGARI_ETKI:g}R etki aranıyor)")]

    # Başlıktaki sayı GÖSTERİLEN bulgu sayısıyla aynı olmalı; örtüşenler
    # elendikten sonra "5 davranış" deyip 4 blok basmak kafa karıştırır.
    gosterilen = sum(1 for b in bulgular if b.kimlikler)
    out = [baslik(f"son {islem} işlemde {gosterilen} davranış tekrarlandı")]
    if davranis:
        out.append(alan("birleşik etki", f"{net:+.1f}R   ({etkilenen} işlem)", "warn"))
        out.append(bosluk())

    for b in bulgular:
        out.append(baslik(b.baslik))
        for c in b.satirlar:
            out.append(satir(f"  {c}"))
        if b.kapsanan:
            out.append(bilgi(f"  aynı işlemler şu adlarla da görünüyor: "
                             f"{', '.join(b.kapsanan)}"))
        out.append(uyari(f"  {b.soru}"))
        out.append(bosluk())

    out.append(bilgi("karar senin."))
    return out
