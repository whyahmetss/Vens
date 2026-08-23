"""
Proje yetenekleri.

`proje` tek başına "nerede kaldım" sorusunun cevabıdır: aktif proje,
bıraktığın yerdeki sonraki adım, ve o projeye ayırdığın son odak seansları.
"""

from core.registry import Risk, Perm, skill, bilgi, uyari, alan, baslik, bosluk
from core import proje as motor
from core import odak as odak_motoru

DURUM_ISARET = {"aktif": "●", "beklemede": "◐", "bitti": "✓", "arsiv": "·"}


def _sure(dk: int) -> str:
    return f"{dk // 60}s {dk % 60}dk" if dk >= 60 else f"{dk} dk"


def _cip(metin: str) -> str:
    """Çevreleyen tırnakları at. Kullanıcı `odak "x"` yazınca tırnak metne girmesin."""
    m = metin.strip()
    if len(m) >= 2 and m[0] == m[-1] and m[0] in "\"'":
        return m[1:-1].strip()
    return m

@skill("proje", "aktif proje ve nerede kaldığın", Risk.SARI, izinler=(Perm.YAZMA,),
       kullanim="proje [ad]", takma_adlar=("nerede-kaldim",))
async def _proje(arg):
    ad = _cip(arg)

    if ad:
        mevcut = motor.bul(ad)
        if mevcut is None:
            motor.kaydet(ad, durum="aktif")
        motor.aktif_et(motor.bul(ad).ad)
        p = motor.bul(ad)
        out = [bilgi(("aktif proje: " if mevcut else "oluşturuldu ve aktif: ") + p.ad)]
        if p.sonraki:
            out.append(alan("sonraki adım", p.sonraki, "acik"))
        return out

    p = motor.aktif()
    if p is None:
        acik = [x for x in motor.hepsi() if x.acik]
        out = [bilgi("aktif proje yok.")]
        if acik:
            out.append(bilgi("açık projeler: " + ", ".join(x.ad for x in acik)))
        out.append(bilgi("seçmek/oluşturmak için: proje <ad>"))
        return out

    out = [baslik(p.ad)]
    if p.aciklama:
        out.append(alan("açıklama", p.aciklama))
    out.append(alan("durum", p.durum))
    if p.sonraki:
        out.append(alan("sonraki adım", p.sonraki, "acik"))
    else:
        out.append(alan("sonraki adım", "yazılmamış — `sonraki <metin>`", "dim"))

    seanslar = [s for s in odak_motoru.hepsi() if s.proje == p.ad]
    if seanslar:
        toplam = sum(s.dakika for s in seanslar)
        out.append(alan("ayrılan zaman", f"{_sure(toplam)}  ({len(seanslar)} seans)"))
        out.append(bosluk())
        out.append(baslik("son çalışmalar"))
        for s in seanslar[-4:]:
            out.append(alan(s.baslangic[5:16].replace("T", " "),
                            f"{_sure(s.dakika):>8}   {s.konu}"
                            + (f"   · {s.notu}" if s.notu else "")))
    return out


@skill("projeler", "tüm projeler", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="projeler")
async def _projeler(arg):
    liste = motor.hepsi()
    if not liste:
        return [bilgi("henüz proje yok."), bilgi("oluşturmak için: proje <ad>")]
    a = motor.aktif()
    sure = {}
    for s in odak_motoru.hepsi():
        if s.proje:
            sure[s.proje] = sure.get(s.proje, 0) + s.dakika

    out = [baslik(f"{len(liste)} proje")]
    for p in liste:
        isaret = DURUM_ISARET.get(p.durum, "·")
        etiket = f"{isaret} {p.ad}" + ("  ←" if a and a.ad == p.ad else "")
        parca = [p.durum]
        if p.ad in sure:
            parca.append(_sure(sure[p.ad]))
        if p.sonraki:
            parca.append(p.sonraki[:40])
        out.append(alan(etiket, "   ".join(parca), "" if p.acik else "dim"))
    return out


@skill("sonraki", "aktif projede sonraki adımı yaz", Risk.SARI,
       izinler=(Perm.YAZMA,), kullanim="sonraki <metin>")
async def _sonraki(arg):
    p = motor.aktif()
    if p is None:
        return [uyari("aktif proje yok."), bilgi("önce: proje <ad>")]
    metin = _cip(arg)
    if not metin:
        return [alan(p.ad, p.sonraki or "sonraki adım yazılmamış"),
                bilgi("yazmak için: sonraki <metin>")]
    motor.kaydet(p.ad, sonraki=metin)
    return [bilgi(f"{p.ad} · sonraki adım kaydedildi"), alan("", metin, "acik"),
            bilgi("yarın `proje` yazdığında bu satır önüne gelecek.")]


@skill("proje-durum", "aktif projenin durumunu değiştir", Risk.SARI,
       izinler=(Perm.YAZMA,), kullanim="proje-durum <aktif|beklemede|bitti|arsiv>")
async def _proje_durum(arg):
    p = motor.aktif()
    if p is None:
        return [uyari("aktif proje yok.")]
    durum = arg.strip().lower()
    if durum not in motor.DURUMLAR:
        return [uyari(f"durum şunlardan biri olmalı: {', '.join(motor.DURUMLAR)}")]
    motor.kaydet(p.ad, durum=durum)
    return [bilgi(f"{p.ad} · {durum}")]
