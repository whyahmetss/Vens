"""
Profil yeteneği — Venüs'ün senin hakkında bildikleri.

Bölüm 7'nin şartı: görülebilir, düzenlenebilir, silinebilir. Gizli hafıza yok.
Bu dosya "görülebilir" kısmını, `profil unut` ve `profil gizle` de diğer
ikisini karşılar.
"""

from core.registry import Risk, Perm, skill, bilgi, uyari, alan, baslik, bosluk
from core import profil as motor


def _cip(metin: str) -> str:
    """Çevreleyen tırnakları at. Kullanıcı `odak "x"` yazınca tırnak metne girmesin."""
    m = metin.strip()
    if len(m) >= 2 and m[0] == m[-1] and m[0] in "\"'":
        return m[1:-1].strip()
    return m

@skill("profil", "Venüs'ün senin hakkında bildikleri", Risk.YESIL,
       izinler=(Perm.OKUMA,), kullanim="profil [gizle <ad>] [goster <ad>]")
async def _profil(arg):
    parca = arg.split(None, 1)
    if parca and parca[0].lower() in ("gizle", "goster", "göster"):
        if len(parca) < 2:
            return [uyari(f"kullanım: profil {parca[0]} <ad>")]
        ad = parca[1].strip()
        if parca[0].lower() == "gizle":
            motor.gizle(ad)
            return [bilgi(f"gizlendi: {ad}"), bilgi("geri açmak: profil goster " + ad)]
        motor.goster(ad)
        return [bilgi(f"tekrar gösterilecek: {ad}")]

    cikarim, beyan, gizli = motor.hepsi()
    out = []

    if beyan:
        out.append(baslik("senin söylediklerin"))
        for b in beyan:
            out.append(alan(f"{b.kimlik}  {b.ad}", b.deger))
        out.append(bosluk())

    if cikarim:
        out.append(baslik("verinden çıkardıklarım"))
        for b in cikarim:
            out.append(alan(b.ad, b.deger))
            out.append(alan("", f"↳ {b.kaynak}", "dim"))
        out.append(bosluk())
    else:
        out.append(bilgi("henüz çıkarım yapacak kadar veri yok."))
        out.append(bilgi(f"(en az {motor.ASGARI_OLAY} olay gerekiyor)"))
        out.append(bosluk())

    if gizli:
        out.append(alan("gizlediklerin", ", ".join(sorted(gizli)), "dim"))
        out.append(bosluk())

    out.append(bilgi("eklemek: profil-ekle <ad> <değer>   ·   silmek: profil-unut <id>"))
    out.append(bilgi("katılmadığın bir çıkarımı susturmak: profil gizle <ad>"))
    out.append(bilgi(f"hepsi burada, gizli hafıza yok · {motor.PROFIL}"))
    return out


@skill("profil-ekle", "profile kendi beyanını ekle", Risk.SARI,
       izinler=(Perm.YAZMA,), kullanim="profil-ekle <ad> <değer>")
async def _profil_ekle(arg):
    parca = arg.split(None, 1)
    if len(parca) < 2:
        return [bilgi("kullanım: profil-ekle <ad> <değer>"),
                bilgi('örnek: profil-ekle çalışma-saati "sabah 06:00 - 10:00"'),
                bilgi("aynı adı tekrar yazarsan sonuncusu geçerli olur.")]
    k = motor.beyan_ekle(parca[0].strip(), _cip(parca[1]))
    return [bilgi(f"eklendi · {k['kimlik']}"), alan(k["beyan"], k["deger"])]


@skill("profil-unut", "profildeki bir beyanı sil", Risk.TURUNCU,
       izinler=(Perm.SILME,), kullanim="profil-unut <id>")
async def _profil_unut(arg):
    kimlik = arg.strip().lower()
    if not kimlik:
        return [uyari("kullanım: profil-unut <id>")]
    if not motor.unut(kimlik):
        return [uyari(f"beyan bulunamadı: {kimlik}")]
    return [bilgi(f"unutuldu · {kimlik}")]
