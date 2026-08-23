"""
Çalışma oturumu — aktif hatırlama döngüsü.

Akış:
    calis            sıradaki kartı sorar (cevabı GÖSTERMEZ)
    cevap <metin>    cevabını dener → deterministik denetim → notlanır
    bildim/zor/...   açık uçlu kartlarda kendi kendini notlarsın

Cevabı görmeden not vermek öğrenme değil, kendini kandırmadır; bu yüzden
`bildim` yalnızca cevap açıldıktan sonra ya da açık uçlu kartta çalışır.
"""

from core.registry import (Risk, Perm, skill, satir, bilgi, uyari, alan,
                           baslik, bosluk, vurgu)
from core import hedef as hedef_motoru
from core import ogrenme as motor
from core import ogretmen


def _cip(metin: str) -> str:
    m = metin.strip()
    if len(m) >= 2 and m[0] == m[-1] and m[0] in "\"'":
        return m[1:-1].strip()
    return m


def _sonraki(hedef: str = "") -> list:
    """Sıradaki kartı açar ve sorar."""
    kartlar = motor.gunun_kartlari(hedef)
    if not kartlar:
        motor.karti_kapat()
        ozet = motor.ozet(hedef)
        if not ozet["toplam"]:
            return [bilgi("hiç kart yok."),
                    bilgi("eklemek için: kart <hedef> <ünite> <soru> = <cevap>")]
        return [bilgi("bugünlük tekrar bitti."),
                alan("toplam", f"{ozet['toplam']} kart · {ozet['olgun']} olgun")]

    k = kartlar[0]
    motor.kart_ac(k, hedef)
    out = [baslik(f"{k.hedef}" + (f" · {k.unite}" if k.unite else "")),
           vurgu(k.soru), bosluk()]
    if k.gecmis:
        out.append(alan("geçmiş", f"{len(k.gecmis)} tekrar · %{k.basari:.0f} doğru "
                                  f"· aralık {k.aralik} gün", "dim"))
    else:
        out.append(alan("", "yeni kart", "dim"))
    out.append(bilgi(f"kalan {len(kartlar)} · cevabını yaz: cevap <metin>"))
    return out


@skill("calis", "çalışma oturumu başlat", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="calis [hedef]", takma_adlar=("çalış",))
async def _calis(arg):
    hedef = _cip(arg).lower()
    if hedef:
        hedefler, _ = hedef_motoru.yukle()
        if hedef not in hedefler:
            return [uyari(f"hedef bulunamadı: {hedef}"),
                    bilgi("tanımlılar: " + ", ".join(hedefler))]
    return _sonraki(hedef)


def _notla(kart, kalite: int, hedef: str = "") -> list:
    ilk_gorus = kart.kaynak == "model" and not kart.gecmis
    yeni = motor.isaretle(kart, kalite)
    motor.karti_kapat()
    out = [alan("sonraki tekrar", f"{yeni.aralik} gün sonra · {yeni.sonraki}",
                "" if kalite >= 3 else "warn")]
    if yeni.olgun:
        out.append(alan("", "bu kart olgunlaştı", "acik"))
    if ilk_gorus:
        # Yanlış cevaplı üretilmiş bir kart deterministik denetçiyi zehirler:
        # doğru bildiğini yanlış sayar. Kartı ilk gördüğünde denetleyebilesin
        # diye bir kez söylenir, sonra susar.
        out.append(alan("", f"bu kartı model üretti — cevap yanlışsa: "
                            f"kart-sil {kart.id}", "dim"))
    return out + [bosluk()] + _sonraki(hedef)


def _hedef_unite(ad: str, unite: str):
    """Hedef ve ünite doğrulaması. Döner: (Hedef, hata satırları)."""
    hedefler, _ = hedef_motoru.yukle()
    h = hedefler.get(ad)
    if h is None:
        return None, [uyari(f"hedef bulunamadı: {ad}"),
                      bilgi("tanımlılar: " + ", ".join(hedefler))]
    if h.uniteler and unite not in h.uniteler:
        return None, [uyari(f"'{unite}' bu hedefin müfredatında yok."),
                      bilgi("üniteler: " + ", ".join(h.uniteler))]
    return h, []


@skill("cevap", "açık karta cevabını ver", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="cevap <metin>")
async def _cevap(arg):
    kart, _, oturum = motor.acik_kart()
    if kart is None:
        return [bilgi("açık kart yok."), bilgi("başlatmak için: calis")]

    verilen = _cip(arg)
    if not verilen:
        return [uyari("kullanım: cevap <metin>")]

    dogru = motor.denetle(kart, verilen)
    motor.cevabi_ac()

    if dogru is None:
        # Açık uçlu kart: cevap anahtarı yok, kendin notlarsın.
        return [alan("senin cevabın", verilen), bosluk(),
                bilgi("bu kartın cevap anahtarı yok — kendin notla:"),
                bilgi("bildim · zor · bilemedim")]

    out = [alan("senin cevabın", verilen),
           alan("doğru cevap", kart.cevap, "" if dogru else "warn")]
    if dogru:
        out.insert(0, vurgu("✓ doğru"))
        # Doğru bilinen kart varsayılan olarak "bildim" (4) sayılır. Kolay
        # geldiyse `kolay` yazıp aralığı uzatabilirsin.
        return out + [bosluk()] + _notla(kart, motor.NOTLAR["bildim"], oturum)
    out.insert(0, uyari("✗ yanlış"))
    return out + [bosluk()] + _notla(kart, motor.NOTLAR["bilemedim"], oturum)


def _kendi_notu(ad: str):
    async def _fn(arg):
        kart, acildi, oturum = motor.acik_kart()
        if kart is None:
            return [bilgi("açık kart yok."), bilgi("başlatmak için: calis")]
        if not acildi:
            # Denemeden not vermek kendini kandırmaktır. Açık uçlu kartta da
            # geçerli: cevabı kafanda kurmakla yazmak aynı şey değildir.
            return [uyari("önce cevabını yaz: cevap <metin>"),
                    bilgi("denemeden not vermek ölçüm sayılmaz.")]
        out = []
        if kart.cevap.strip():
            out.append(alan("doğru cevap", kart.cevap))
        return out + _notla(kart, motor.NOTLAR[ad], oturum)
    return _fn


for _ad, _aciklama in (("bildim", "kartı bildim olarak notla"),
                       ("kolay", "kartı kolay olarak notla"),
                       ("zor", "kartı zor olarak notla"),
                       ("bilemedim", "kartı bilemedim olarak notla")):
    skill(_ad, _aciklama, Risk.YESIL, izinler=(Perm.YAZMA,),
          kullanim=_ad)(_kendi_notu(_ad))


@skill("kart", "kart ekle", Risk.SARI, izinler=(Perm.YAZMA,),
       kullanim="kart <hedef> <ünite> <soru> = <cevap>")
async def _kart(arg):
    if "=" not in arg:
        return [bilgi("kullanım: kart <hedef> <ünite> <soru> = <cevap>"),
                satir("  kart ingilizce_a2 past_simple 'go' fiilinin 2. hâli = went"),
                bilgi("birden fazla kabul edilebilir cevap: went|gone gibi"),
                bilgi("cevap boş bırakılırsa açık uçlu kart olur, kendin notlarsın.")]

    sol, _, cevap = arg.partition("=")
    parca = sol.split(None, 2)
    if len(parca) < 3:
        return [uyari("hedef, ünite ve soru gerekli.")]

    ad, unite, soru = parca[0].lower(), parca[1].lower(), _cip(parca[2])
    h, hata = _hedef_unite(ad, unite)
    if h is None:
        return hata

    k = motor.ekle(ad, soru, _cip(cevap), unite)
    return [bilgi(f"eklendi · {k.id}"), alan(k.soru, k.cevap or "(açık uçlu)")]


@skill("kart-uret", "üniteye kart ürettir", Risk.SARI,
       izinler=(Perm.YAZMA, Perm.AG),
       kullanim="kart-uret <hedef> <ünite> [adet]")
async def _kart_uret(arg):
    parca = arg.split()
    if len(parca) < 2:
        hedefler, _ = hedef_motoru.yukle()
        return [bilgi("kullanım: kart-uret <hedef> <ünite> [adet]"),
                bilgi("hedefler: " + ", ".join(hedefler))]

    ad, unite = parca[0].lower(), parca[1].lower()
    adet = 10
    if len(parca) > 2:
        if not parca[2].isdigit():
            return [uyari(f"adet sayı olmalı: {parca[2]}")]
        adet = min(int(parca[2]), ogretmen.EN_COK)

    h, hata = _hedef_unite(ad, unite)
    if h is None:
        return hata

    if not ogretmen.acik_mi():
        # Motor modele bağımlı değil; bu görünür olsun diye elle ekleme
        # satırı hatırlatılır.
        return [uyari(ogretmen.neden_kapali()),
                bilgi("kartı elle ekleyebilirsin:"),
                satir(f"  kart {ad} {unite} <soru> = <cevap>")]

    mevcut = [k.soru for k in motor.hepsi() if k.hedef == ad and k.unite == unite]
    u = await ogretmen.uret(h.baslik, unite, adet, mevcut, h.dil_notu)
    if u.hata:
        return [uyari(u.hata)]
    if not u.kartlar:
        return [bilgi("yeni kart üretilmedi."),
                bilgi(f"bu ünitede zaten {len(mevcut)} kart var.")]

    out = [baslik(f"{len(u.kartlar)} kart · {h.baslik} · {unite}")]
    for soru, cevap in u.kartlar:
        k = motor.ekle(ad, soru, cevap, unite, kaynak="model")
        out.append(alan(k.id, f"{soru}   →   {cevap}"))
    out.append(bosluk())
    out.append(bilgi("cevapları gözden geçir — yanlış olanı: kart-sil <id>"))
    return out


@skill("kartlar", "kart havuzu", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="kartlar [hedef]")
async def _kartlar(arg):
    hedef = _cip(arg).lower()
    kartlar = [k for k in motor.hepsi() if not hedef or k.hedef == hedef]
    if not kartlar:
        return [bilgi("kart yok."),
                bilgi("eklemek: kart <hedef> <ünite> <soru> = <cevap>")]

    ozet = motor.ozet(hedef)
    out = [baslik(f"{ozet['toplam']} kart · {ozet['yeni']} yeni · "
                  f"{ozet['olgun']} olgun · bugün {ozet['bugun']}")]
    for k in sorted(kartlar, key=lambda k: (k.sonraki or "", k.id))[:20]:
        durum = (f"{k.aralik}g" if k.tekrar else "yeni")
        basari = f"%{k.basari:.0f}" if k.gecmis else "—"
        soru = k.soru if len(k.soru) <= 52 else k.soru[:51] + "…"
        out.append(alan(f"{k.id}  {durum:>5}  {basari:>4}",
                        soru
                        + (f"   [{k.unite}]" if k.unite else "")
                        + ("  [model]" if k.kaynak == "model" else ""),
                        "warn" if k.gecmis and k.basari < 60 else ""))
    return out


@skill("kart-sil", "kartı sil", Risk.TURUNCU, izinler=(Perm.SILME,),
       kullanim="kart-sil <id>")
async def _kart_sil(arg):
    kimlik = _cip(arg).lower()
    if not kimlik:
        return [uyari("kullanım: kart-sil <id>")]
    if not motor.sil(kimlik):
        return [uyari(f"kart bulunamadı: {kimlik}")]
    return [bilgi(f"silindi · {kimlik}")]
