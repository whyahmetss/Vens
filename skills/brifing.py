"""
Sabah brifingi ve gün kapanışı.

Şartname Bölüm 12: Venüs komut beklemeden konuşabilir. Şu ana kadar bunu
yalnızca killzone ve seviye için yapıyordu — ikisi de trading. Bu dosya
proaktifliği güne yayıyor.

İkisi de yeni veri üretmez, var olanı bir araya getirir: aktif proje,
açık pozisyon, incelenmemiş kayıt, odak süresi, bekleyen bildirim.

Kendiliğinden gelen kısım NORMAL seviyededir — sessiz rozet, ekran bölme.
Brifing bir hatırlatmadır, kesinti değil (Bölüm 12).
"""

from datetime import date, datetime, timedelta

from core.registry import Risk, Perm, skill, satir, bilgi, uyari, alan, baslik, bosluk
from core.bildirim import Seviye, bildir, bekleyenler, hepsi as bildirim_hepsi
from core.zamanlayici import periyodik
from core import kurallar as kural_motoru
from core import jurnal as depo
from core import odak as odak_motoru
from core import proje as proje_motoru
from core import review as review_motoru

GUNLER = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")
AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")


def _sure(dk: int) -> str:
    return f"{dk // 60}s {dk % 60}dk" if dk >= 60 else f"{dk} dk"


def _tarih(d: date) -> str:
    return f"{d.day} {AYLAR[d.month - 1]}, {GUNLER[d.weekday()]}"


def _acik_pozisyonlar(kayitlar):
    return [k for k in kayitlar
            if not isinstance(k.get("sonuc_r"), (int, float))
            or isinstance(k.get("sonuc_r"), bool)]


@skill("gunaydin", "sabah brifingi", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="gunaydin", takma_adlar=("brifing", "günaydın"))
async def _gunaydin(arg):
    bugun = date.today()
    kayitlar = depo.hepsi()
    out = [baslik(_tarih(bugun))]

    # --- nerede kaldın (Bölüm 0'ın tek cümlelik hedefi) ---
    p = proje_motoru.aktif()
    if p is not None:
        out.append(alan("aktif proje", p.ad))
        if p.sonraki:
            out.append(alan("sonraki adım", p.sonraki, "acik"))
        else:
            out.append(alan("sonraki adım", "yazılmamış", "dim"))
    else:
        acik_p = [x for x in proje_motoru.hepsi() if x.acik]
        if acik_p:
            out.append(alan("projeler", ", ".join(x.ad for x in acik_p)))

    # --- dün ne kadar çalıştın ---
    dun = odak_motoru.gunluk_dakika(bugun - timedelta(days=1))
    if dun:
        out.append(alan("dün odak", _sure(dun)))

    # --- bugünün seansları ---
    try:
        from skills.seans import durum as seans_durumu
        izinli = kural_motoru.yukle().deger("trading.izinli_seanslar", ())
        bugunku = [d for d in seans_durumu() if d["ad"] in izinli]
        if bugunku:
            out.append(bosluk())
            out.append(baslik("bugünün killzone'ları"))
            for d in bugunku:
                out.append(alan(("● " if d["acik"] else "") + d["ad"],
                                f"{d['bas']:%H:%M} — {d['bit']:%H:%M}",
                                "acik" if d["acik"] else ""))
    except Exception:
        pass

    # --- açık işler ---
    acik = _acik_pozisyonlar(kayitlar)
    incelenmemis = review_motoru.incelenmemis(kayitlar)
    bekleyen = bekleyenler()
    if acik or incelenmemis or bekleyen:
        out.append(bosluk())
        out.append(baslik("açık işler"))
        if acik:
            out.append(alan("açık pozisyon", f"{len(acik)}  "
                                             + ", ".join(k.get("sembol", "?") for k in acik[:4]),
                            "warn"))
        if incelenmemis:
            out.append(alan("incelenmemiş kayıt", f"{len(incelenmemis)}  → review"))
        if bekleyen:
            out.append(alan("bekleyen bildirim", f"{len(bekleyen)}  → bildirimler"))
    else:
        out.append(bosluk())
        out.append(bilgi("açık iş yok."))
    return out


@skill("kapanis", "gün kapanışı", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="kapanis", takma_adlar=("kapanış",))
async def _kapanis(arg):
    bugun = date.today()
    kayitlar = depo.hepsi()
    bugunku = depo.gun(bugun, kayitlar)
    k = kural_motoru.yukle()
    out = [baslik(f"{_tarih(bugun)} · kapanış")]

    # --- trading ---
    kapali = [x for x in bugunku
              if isinstance(x.get("sonuc_r"), (int, float))
              and not isinstance(x.get("sonuc_r"), bool)]
    limit = k.deger("trading.gunluk_islem_limiti")
    if bugunku:
        net = sum(x["sonuc_r"] for x in kapali)
        cizgi = f"{len(bugunku)} işlem"
        if limit is not None:
            cizgi += f" / {limit} limit"
        if kapali:
            cizgi += f"   net {net:+.2f}R"
        out.append(alan("trading", cizgi,
                        "warn" if limit is not None and len(bugunku) > limit else ""))
        ihlal = sum(len(x.get("ihlaller") or []) for x in bugunku)
        if ihlal:
            out.append(alan("kural ihlali", f"{ihlal}  → ihlaller", "warn"))
    else:
        out.append(alan("trading", "bugün işlem yok"))

    # --- çalışma ---
    dakika = odak_motoru.gunluk_dakika(bugun)
    hedef = k.deger("calisma.gunluk_odak_hedefi_dk")
    cizgi = _sure(dakika)
    if hedef:
        cizgi += f" / {_sure(int(hedef))}   %{100 * dakika / hedef:.0f}"
    out.append(alan("odak", cizgi, "" if not hedef or dakika >= hedef else "warn"))

    acik_seans = odak_motoru.acik_seans()
    if acik_seans:
        out.append(alan("açık seans", f"{acik_seans.konu} · {_sure(acik_seans.dakika)}",
                        "warn"))

    # --- yarına bırakılanlar ---
    eksikler = []
    acik_poz = _acik_pozisyonlar(bugunku)
    if acik_poz:
        eksikler.append(f"{len(acik_poz)} pozisyon sonuçsuz")
    incelenmemis = review_motoru.incelenmemis(kayitlar)
    if incelenmemis:
        eksikler.append(f"{len(incelenmemis)} kayıt incelenmemiş")
    p = proje_motoru.aktif()
    if p is not None and not p.sonraki:
        eksikler.append(f"{p.ad} için sonraki adım yazılmamış")

    out.append(bosluk())
    if eksikler:
        out.append(baslik("yarına kalanlar"))
        for e in eksikler:
            out.append(satir(f"  {e}"))
        if p is not None and not p.sonraki:
            out.append(bilgi("yarın nereden başlayacağını şimdi yaz: sonraki <metin>"))
    else:
        out.append(bilgi("açık iş kalmadı."))
    return out


def _bildirildi_mi(anahtar: str) -> bool:
    return any(b.kaynak == anahtar for b in bildirim_hepsi())


@periyodik(60, ad="brifing")
async def _brifing_kontrolu():
    """Brifing ve kapanış saatleri geldiğinde sessiz rozet bırakır.

    Ekranı bölmez: brifing bir hatırlatmadır. İçeriği kullanıcı `gunaydin`
    ya da `kapanis` yazınca üretilir — bildirimin içine sıkıştırılmaz.
    """
    k = kural_motoru.yukle()
    simdi = datetime.now()
    bugun = date.today().isoformat()

    for alan_adi, komut, metin in (
            ("calisma.brifing_saati", "gunaydin", "sabah brifingin hazır"),
            ("calisma.kapanis_saati", "kapanis", "gün kapanışı — bugünü kapatalım mı")):
        saat = k.deger(alan_adi)
        if not saat:
            continue
        s, d = (int(x) for x in saat.split(":"))
        anahtar = f"{komut}:{bugun}"
        if (simdi.hour, simdi.minute) >= (s, d) and not _bildirildi_mi(anahtar):
            bildir(Seviye.NORMAL, f"{metin} — `{komut}`", anahtar)
