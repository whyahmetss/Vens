"""
Öğrenme yetenekleri — hedefler, müfredat ve çalışma oturumu.

Ciddi bir öğretme sisteminin kötü bir chatbot'tan farkı burada görünür:

- Soru sorulur, **sen cevaplarsın** (aktif hatırlama). Okumak öğrenmek değil.
- Cevap **deterministik** denetlenir; cevap anahtarı kartta saklıdır.
- Ne zaman tekrar edileceğini **SM-2 algoritması** söyler, model değil.
- İlerleme "kaç ders izledin" değil, kaç kartın olgunlaştığıdır.
- Övgü yok. Bildiğini bildiğini, bilmediğini bilmediğini söyler (kimlik.md).
"""

from datetime import date

from core.registry import (Risk, Perm, skill, satir, bilgi, uyari, alan,
                           baslik, bosluk, vurgu)
from core import hedef as hedef_motoru
from core import ogrenme as motor


def _cip(metin: str) -> str:
    m = metin.strip()
    if len(m) >= 2 and m[0] == m[-1] and m[0] in "\"'":
        return m[1:-1].strip()
    return m


def _tempo_satiri(t) -> list:
    h = t.hedef
    out = []
    if h.tur == "unite":
        out.append(alan("ilerleme", f"{t.biten}/{t.toplam} ünite   %{t.yuzde:.0f}"))
        if t.kalan_gun is not None:
            out.append(alan("kalan", f"{t.kalan_gun} gün"))
        if t.gereken_hiz is not None:
            cizgi = f"günde {t.gereken_hiz:.2f} ünite gerekiyor"
            if t.fiili_hiz is not None:
                cizgi += f"   ·   fiili {t.fiili_hiz:.2f}"
            out.append(alan("tempo", cizgi,
                            "" if t.tempoda else "warn"))
        if t.kalan_gun is not None and t.kalan_gun < 0:
            out.append(alan("", "bitiş tarihi geçti", "warn"))
    else:
        out.append(alan("seri", f"{t.seri} gün üst üste"))
        if h.gunluk_dakika:
            out.append(alan("günlük hedef", f"{h.gunluk_dakika} dk"))
    return out


@skill("hedefler", "hedefler ve tempo", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="hedefler")
async def _hedefler(arg):
    hedefler, sorunlar = hedef_motoru.yukle()
    if not hedefler:
        out = [bilgi("tanımlı hedef yok.")]
        out += [uyari(f"  {s}") for s in sorunlar]
        out.append(bilgi(f"tanımlamak için: {hedef_motoru._dosya()}"))
        return out

    out = []
    for ad, h in hedefler.items():
        gunler = _calisilan_gunler(ad) if h.tur == "aliskanlik" else None
        t = hedef_motoru.tempo(h, gunler)
        ozet = motor.ozet(ad)
        out.append(baslik(h.baslik))
        out += _tempo_satiri(t)
        out.append(alan("kart", f"{ozet['toplam']} toplam · {ozet['olgun']} olgun · "
                                f"{ozet['bugun']} bugün"))
        out.append(bosluk())
    if sorunlar:
        out.append(baslik(f"{len(sorunlar)} sorun"))
        out += [uyari(f"  {s}") for s in sorunlar]
    return out


def _calisilan_gunler(hedef_ad: str) -> set:
    """Alışkanlık hedefleri için: hangi günler odak seansı yapıldı."""
    try:
        from core import odak
        return {s.baslangic[:10] for s in odak.hepsi() if s.bitis}
    except Exception:
        return set()


@skill("hedef", "tek hedefin ayrıntısı", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="hedef <ad>")
async def _hedef(arg):
    ad = _cip(arg).lower()
    hedefler, _ = hedef_motoru.yukle()
    if not ad:
        return [bilgi("hedefler: " + (", ".join(hedefler) or "yok")),
                bilgi("ayrıntı için: hedef <ad>")]
    h = hedefler.get(ad)
    if h is None:
        return [uyari(f"hedef bulunamadı: {ad}"),
                bilgi("tanımlılar: " + (", ".join(hedefler) or "yok"))]

    t = hedef_motoru.tempo(h, _calisilan_gunler(ad) if h.tur == "aliskanlik" else None)
    biten = hedef_motoru.bitenler(ad)
    ozet = motor.ozet(ad)

    out = [baslik(h.baslik)] + _tempo_satiri(t) + [bosluk()]

    if h.uniteler:
        out.append(baslik("müfredat"))
        for u in h.uniteler:
            if u in biten:
                out.append(alan(f"✓ {u}", biten[u], "dim"))
            else:
                out.append(alan(f"· {u}", "bekliyor"))
        out.append(bosluk())

    out.append(baslik("kartlar"))
    out.append(alan("toplam", f"{ozet['toplam']}  ·  {ozet['yeni']} yeni  ·  "
                              f"{ozet['olgun']} olgun"))
    out.append(alan("bugün tekrar", f"{ozet['bugun']}"))
    if ozet["zayif"]:
        out.append(bosluk())
        out.append(baslik("en zayıf kartların"))
        for k in ozet["zayif"]:
            out.append(alan(f"%{k.basari:.0f}", k.soru[:60], "warn"))
    return out


@skill("unite", "üniteyi bitmiş işaretle", Risk.SARI, izinler=(Perm.YAZMA,),
       kullanim="unite <hedef> <ünite>")
async def _unite(arg):
    parca = arg.split()
    hedefler, _ = hedef_motoru.yukle()
    if len(parca) < 2:
        return [bilgi("kullanım: unite <hedef> <ünite>"),
                bilgi("hedefler: " + ", ".join(hedefler))]
    ad, u = parca[0].lower(), parca[1].lower()
    h = hedefler.get(ad)
    if h is None:
        return [uyari(f"hedef bulunamadı: {ad}")]
    if u not in h.uniteler:
        return [uyari(f"'{u}' bu hedefin müfredatında yok."),
                bilgi("üniteler: " + ", ".join(h.uniteler))]
    if u in hedef_motoru.bitenler(ad):
        return [bilgi(f"{u} zaten bitmiş.")]

    hedef_motoru.bitir(ad, u)
    t = hedef_motoru.tempo(h)
    out = [bilgi(f"✓ {u}")] + _tempo_satiri(t)
    # Ünite bitmesi öğrenmek değildir — kart yoksa söylenir.
    if not [k for k in motor.hepsi() if k.hedef == ad and k.unite == u]:
        out.append(bosluk())
        out.append(uyari("bu ünite için hiç kart yok — bitirdin ama ölçülmedi."))
        out.append(bilgi(f"kart eklemek: kart {ad} {u} <soru> = <cevap>"))
    return out
