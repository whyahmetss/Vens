"""
Odak yetenekleri — çalışma seansı başlat, bitir, gör.

Hatırlatmalar `kurallar.yaml`'ın `calisma` bölümünden gelir. Venüs
engellemez, söyler ve çekilir (kimlik.md).
"""

from datetime import date, datetime

from core.registry import Risk, Perm, skill, satir, bilgi, uyari, alan, baslik, bosluk
from core.bildirim import Seviye, bildir, hepsi as bildirim_hepsi
from core.zamanlayici import periyodik
from core import kurallar as kural_motoru
from core import odak as motor


def _sure(dk: int) -> str:
    return f"{dk // 60}s {dk % 60}dk" if dk >= 60 else f"{dk} dk"


def _cip(metin: str) -> str:
    """Çevreleyen tırnakları at. Kullanıcı `odak "x"` yazınca tırnak metne girmesin."""
    m = metin.strip()
    if len(m) >= 2 and m[0] == m[-1] and m[0] in "\"'":
        return m[1:-1].strip()
    return m

@skill("odak", "odak seansı başlat ya da durumu gör", Risk.SARI,
       izinler=(Perm.YAZMA,), kullanim="odak [ne üzerinde çalışıyorsun]")
async def _odak(arg):
    konu = _cip(arg)
    acik = motor.acik_seans()

    if not konu:
        bugun = motor.gunluk_dakika()
        hedef = kural_motoru.yukle().deger("calisma.gunluk_odak_hedefi_dk")
        out = []
        if acik:
            out.append(baslik(f"açık seans · {_sure(acik.dakika)}"))
            out.append(alan("konu", acik.konu))
            if acik.proje:
                out.append(alan("proje", acik.proje))
            out.append(alan("başlangıç", acik.baslangic[11:16]))
            out.append(bosluk())
            out.append(bilgi("bitirmek için: bitir [not]"))
        else:
            out.append(bilgi("açık seans yok."))
            out.append(bilgi("başlatmak için: odak <ne üzerinde çalışıyorsun>"))
        out.append(bosluk())
        cizgi = f"bugün {_sure(bugun)}"
        if hedef:
            cizgi += f" / {_sure(int(hedef))} hedef  (%{100*bugun/hedef:.0f})"
        out.append(alan("toplam", cizgi))
        return out

    if acik:
        return [uyari(f"zaten açık bir seans var: {acik.konu} ({_sure(acik.dakika)})"),
                bilgi("önce bitir, sonra yenisini başlat.")]

    # Aktif proje varsa seans ona bağlanır — sonradan "neye ne kadar zaman
    # ayırdım" sorusunun cevabı buradan çıkar.
    proje = ""
    try:
        from core.proje import aktif
        p = aktif()
        proje = p.ad if p else ""
    except Exception:
        pass

    s = motor.basla(konu, proje)
    out = [bilgi(f"başladı · {s.id}"), alan("konu", konu)]
    if proje:
        out.append(alan("proje", proje))
    return out


@skill("bitir", "açık odak seansını kapat", Risk.SARI, izinler=(Perm.YAZMA,),
       kullanim="bitir [not]")
async def _bitir(arg):
    acik = motor.acik_seans()
    if acik is None:
        return [bilgi("açık seans yok.")]
    motor.bitir(acik.id, _cip(arg))
    bugun = motor.gunluk_dakika()
    hedef = kural_motoru.yukle().deger("calisma.gunluk_odak_hedefi_dk")
    out = [bilgi(f"bitti · {_sure(acik.dakika)}"), alan("konu", acik.konu)]
    if _cip(arg):
        out.append(alan("not", _cip(arg)))
    cizgi = f"bugün toplam {_sure(bugun)}"
    if hedef:
        kalan = int(hedef) - bugun
        cizgi += f" · hedefe {_sure(kalan)} kaldı" if kalan > 0 else " · hedef tuttu"
    out.append(bilgi(cizgi))
    return out


@skill("odaklar", "son odak seansları", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="odaklar [adet]")
async def _odaklar(arg):
    seanslar = motor.hepsi()
    if not seanslar:
        return [bilgi("henüz odak seansı yok."), bilgi("başlatmak: odak <konu>")]
    try:
        n = int(arg.strip()) if arg.strip() else 10
    except ValueError:
        n = 10
    out = [baslik(f"{len(seanslar)} seans · bugün {_sure(motor.gunluk_dakika())}")]
    for s in seanslar[-n:]:
        etiket = f"{s.baslangic[5:16].replace('T', ' ')}"
        deger = f"{_sure(s.dakika):>8}   {s.konu}"
        if s.acik:
            deger += "   ● açık"
        if s.notu:
            deger += f"   · {s.notu}"
        out.append(alan(etiket, deger, "acik" if s.acik else ""))
    return out


def _bildirildi_mi(anahtar: str) -> bool:
    return any(b.kaynak == anahtar for b in bildirim_hepsi())


@periyodik(60, ad="odak")
async def _odak_kontrolu():
    """Çalışma hatırlatmaları. Hepsi kurallar.yaml'a bağlı; boşsa sessiz."""
    k = kural_motoru.yukle()
    simdi = datetime.now()
    bugun = date.today().isoformat()
    acik = motor.acik_seans()

    # --- seans çok uzadı ---
    sure = k.deger("calisma.odak_sure_dk")
    if acik and sure and acik.dakika >= int(sure):
        anahtar = f"odak:uzun:{acik.id}"
        if not _bildirildi_mi(anahtar):
            bildir(Seviye.NORMAL,
                   f"{_sure(acik.dakika)} aralıksız çalışıyorsun — {acik.konu}", anahtar)

    # --- gece çalışması ---
    gece = k.deger("calisma.gece_calisma_uyarisi_saat")
    if acik and gece:
        s, d = (int(x) for x in gece.split(":"))
        # Gece saati ertesi güne sarkabilir: 01:00 uyarısı 00:00-06:00 arasında
        # anlamlıdır, öğlen değil.
        gecti = (simdi.hour, simdi.minute) >= (s, d) if s >= 12 else \
                (s, d) <= (simdi.hour, simdi.minute) < (6, 0)
        anahtar = f"odak:gece:{bugun}"
        if gecti and not _bildirildi_mi(anahtar):
            bildir(Seviye.YUKSEK,
                   f"saat {simdi:%H:%M} ve hâlâ açık seansın var — {acik.konu}", anahtar)

    # --- günlük odak saati geldi, hiç başlamadın ---
    odak_saati = k.deger("calisma.gunluk_odak_saati")
    if odak_saati and not motor.gun():
        s, d = (int(x) for x in odak_saati.split(":"))
        anahtar = f"odak:hatirlatma:{bugun}"
        if (simdi.hour, simdi.minute) >= (s, d) and not _bildirildi_mi(anahtar):
            bildir(Seviye.NORMAL, f"bugün henüz odak seansı başlatmadın", anahtar)
