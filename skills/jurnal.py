"""
Jurnal yetenekleri — kayıt, listeleme, istatistik.

Şartname Bölüm 11. Kayıt biçimi ve depo core/jurnal.py'de, kural denetimi
core/denetci.py'de; burada giriş ve gösterim var.

Kayıt anında kurallar denetlenir ve ihlal **kaydedilir, engellenmez**
(Bölüm 5). Venüs hatırlatır, sonra çekilir — karar kullanıcınındır.
"""

from datetime import date, datetime

from core.registry import Risk, Perm, skill, satir, bilgi, uyari, vurgu, alan, baslik, bosluk
from core import jurnal as depo
from core import denetci
from core import kurallar as kural_motoru
from core import karne as karne_motoru
from core import playbook as playbook_motoru
from core.bildirim import Seviye, bildir

AYLAR = ("Oca", "Şub", "Mar", "Nis", "May", "Haz",
         "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")

# Bölüm 11'deki kayıt düzeni: sıra ve etiketler oradan.
# Etiketler baştan küçük harf: "GİRİŞ".lower() Python'da "gi̇ri̇ş" üretir
# (birleşen nokta). Büyük harfe çevirmek gerekirse kabuk Türkçe kurallarıyla yapar.
SATIRLAR = (("setup", "setup"), ("seans", "seans"), ("bias", "bias"),
            ("htf", "htf"), ("likidite", "likidite"),
            ("giris_sebebi", "giriş"), ("cikis_sebebi", "çıkış"),
            ("execution", "execution"), ("duygu", "duygu"), ("gorsel", "görsel"))

ORNEK = ('jurnal sembol=XAUUSD yon=long seans=londra setup=sweep_mss_fvg '
         'kontrol=liquidity_sweep,mss,fvg,ote risk=1 hedef_r=3 sl=2612 tp=2680 '
         'htf="haftalık BOS sonrası" likidite=SSL giris_sebebi="OTE 0.705" duygu=sakin')

ISARET = {True: "✓", False: "✗"}


def _karne_satirlari(k, kayit) -> list:
    """Karneyi çıktıya çevirir. Geçen maddeler de gösterilir — "8/8 uygun"
    görmek, ihlal listesini görmek kadar bilgi taşır."""
    out = [baslik(f"karne · {k.gecen}/{k.toplam} · kalite {k.skor}/100")]
    for m in k.maddeler:
        out.append(alan(f"{ISARET[m.gecti]} {m.ad}",
                        m.aciklama or ("uygun" if m.gecti else f"-{m.agirlik}"),
                        "" if m.gecti else "warn"))
    if not k.setup_tanimli:
        out.append(bilgi(f"setup '{kayit.get('setup') or '—'}' playbook'ta yok — "
                         f"yalnızca kural denetimi yapıldı."))
    return out


def _denetle(kayit, gunun):
    """Kural denetimi + karne. Playbook setup'a özel R:R'yi sıkılaştırabilir."""
    kurallar = kural_motoru.yukle()
    pb = playbook_motoru.yukle(kurallar=kurallar)
    ihlaller = denetci.denetle(kayit, kurallar, gunun,
                               min_rr=karne_motoru.setup_min_rr(kayit, pb))
    return kurallar, ihlaller, karne_motoru.cikar(kayit, ihlaller, pb)


def _tarih(kayit) -> str:
    try:
        d = datetime.fromisoformat(kayit.get("islem_t") or kayit["t"])
    except (KeyError, TypeError, ValueError):
        return "?"
    return f"{d.day} {AYLAR[d.month - 1]} {d.year}, {d:%H:%M}"


def _r(kayit) -> str:
    d = kayit.get("sonuc_r")
    return f"{d:+.2f}R" if isinstance(d, (int, float)) else "açık"


def _baslik(kayit) -> str:
    return f"{kayit.get('sembol', '?')} · {_tarih(kayit)} · {_r(kayit)}"


@skill("jurnal", "işlem kaydı ekle", Risk.SARI, izinler=(Perm.YAZMA,),
       kullanim="jurnal alan=değer ...", takma_adlar=("j",))
async def _jurnal(arg):
    if not arg.strip():
        return [bilgi("kullanım: alan=değer çiftleri. örnek:"), satir(f"  {ORNEK}"),
                bilgi(""),
                bilgi("plan     : sembol yon seans setup kontrol risk hedef_r sl tp"),
                bilgi("gerekçe  : bias htf likidite giris_sebebi duygu"),
                bilgi("sonrası  : sonuc_r cikis_sebebi execution gorsel etiket"),
                bilgi("işaret   : stop_genisletme plan_disi_giris zaman"),
                bilgi(""),
                bilgi("sonuc_r boş bırakılırsa pozisyon açık sayılır — "
                      "sonra: tamamla <id> sonuc_r=2.4"),
                bilgi("kontrol listesini setup'ından görmek için: playbook")]

    coz = depo.ayristir(arg)
    if coz.hatalar:
        return [uyari("kayıt yazılmadı:")] + [satir(f"  {h}") for h in coz.hatalar]

    kayit = depo.hazirla(coz.veri)

    # Günlük limit ve bekleme kuralları bu kaydı da sayar.
    gunun = depo.gun(datetime.fromisoformat(kayit["islem_t"]).date()) + [kayit]
    kurallar, ihlaller, karne = _denetle(kayit, gunun)
    kayit["skor"] = karne.skor
    if ihlaller:
        kayit["ihlaller"] = [i.mesaj for i in ihlaller]

    depo.yaz(kayit)
    denetci.kaydet(kayit, ihlaller)
    for i in ihlaller:
        # Bölüm 12: kural ihlali anı KRİTİK. Ama kullanıcı bu kaydı kendi
        # girdi, uyarı zaten aşağıda görünüyor — kesinti değil, bütçeden
        # düşmez. Kayda geçer ki `bildirimler` ve geçmiş eksik kalmasın.
        bildir(Seviye.KRITIK, i.mesaj, f"jurnal:{kayit['id']}", kesintisiz=True)

    out = [bilgi(f"kaydedildi · {kayit['id']}"), satir(_baslik(kayit)), bosluk()]
    for note in coz.notlar:
        out.append(bilgi(f"  {note}"))
    out += _karne_satirlari(karne, kayit)
    if ihlaller:
        out.append(bosluk())
        out.append(bilgi("kaydedildi, engellenmedi. karar senin."))
    if not kurallar.okundu:
        out.append(uyari("kural dosyası okunamadı — bu kayıt denetlenmedi."))
    return out


@skill("tamamla", "kaydı tamamla ya da düzelt", Risk.SARI, izinler=(Perm.YAZMA,),
       kullanim="tamamla <id> alan=değer ...")
async def _tamamla(arg):
    parca = arg.split(None, 1)
    if len(parca) < 2:
        return [bilgi("kullanım: tamamla <id> alan=değer ..."),
                satir("  tamamla a3f1 sonuc_r=2.4 cikis_sebebi=\"TP1'de aldım\""),
                bilgi(""),
                bilgi("doldurulabilir (girişte bilinemezdi): "
                      + ", ".join(depo.SONRADAN_BILINEBILIR)),
                bilgi("dolu bir alana yazmak üzerine YAZMAZ — işlem sonrası "
                      "not olarak eklenir.")]

    kimlik = parca[0].strip().lower()
    mevcut = depo.bul(kimlik)
    if mevcut is None:
        return [uyari(f"kayıt bulunamadı: {kimlik}")]

    coz = depo.ayristir(parca[1])
    if coz.hatalar:
        return [uyari("düzeltme yazılmadı:")] + [satir(f"  {h}") for h in coz.hatalar]
    if not coz.veri:
        return [uyari("değişecek alan yok.")]

    aday = {a: d for a, d in coz.veri.items() if a not in ("id", "t", "islem_t")}
    # Geçmiş yeniden yazılamaz: yalnızca girişte bilinmesi imkânsız olan ve
    # HÂLÂ BOŞ olan alanlar dolar. Kalan her şey nota döner.
    yazilabilir, reddedilen = depo.ayir(mevcut, aday)

    out: list = []
    if yazilabilir:
        guncel = {**mevcut, **yazilabilir}
        gun_tarihi = datetime.fromisoformat(guncel["islem_t"]).date()
        gunun = [guncel if k.get("id") == kimlik else k for k in depo.gun(gun_tarihi)]
        if all(k.get("id") != kimlik for k in gunun):
            gunun.append(guncel)

        # Sonuç girilince günün net kaybı değişir; ihlaller yeniden hesaplanır.
        _, ihlaller, karne = _denetle(guncel, gunun)
        onceki = set(mevcut.get("ihlaller") or [])
        yazilabilir["ihlaller"] = [i.mesaj for i in ihlaller]
        yazilabilir["skor"] = karne.skor
        depo.duzelt(kimlik, yazilabilir)

        # Yalnızca YENİ ihlaller kaydedilir; eskiler ihlaller.jsonl'da zaten var.
        yeni_ihlal = [i for i in ihlaller if i.mesaj not in onceki]
        if yeni_ihlal:
            denetci.kaydet(guncel, yeni_ihlal)
            for i in yeni_ihlal:
                bildir(Seviye.KRITIK, i.mesaj, f"jurnal:{kimlik}", kesintisiz=True)

        out += [bilgi(f"güncellendi · {kimlik}"), satir(_baslik(guncel))]
        out += [alan(a, ", ".join(d) if isinstance(d, list) else str(d))
                for a, d in yazilabilir.items() if a not in ("ihlaller", "skor")]
        if yeni_ihlal:
            out.append(bosluk())
            out += _karne_satirlari(karne, guncel)
            out.append(bilgi("kaydedildi, engellenmedi. karar senin."))
    else:
        guncel = mevcut

    if reddedilen:
        # Kullanıcı dolu bir alanı değiştirmek istedi. Üzerine YAZILMAZ; niyet
        # not olarak kaydedilir. Sonradan hikâye uydurulamasın diye ORIGINAL
        # ile POST-TRADE NOTE ayrı durur.
        metin = " · ".join(
            f"{a}: {', '.join(d) if isinstance(d, list) else d}"
            for a, d in reddedilen.items())
        depo.not_ekle(kimlik, metin)
        out.append(bosluk())
        out.append(uyari("üzerine yazılmadı:"))
        for a, d in reddedilen.items():
            istenen = ", ".join(d) if isinstance(d, list) else d
            if depo.dolu_mu(mevcut, a):
                eski_d = mevcut.get(a)
                eski_d = ", ".join(eski_d) if isinstance(eski_d, list) else eski_d
                out.append(alan(a, f"{eski_d}  →  istenen: {istenen}   "
                                   f"(zaten dolu)", "warn"))
            else:
                # Boş ama giriş anına ait bir alan. Sonradan doldurmak, o
                # gerekçeyi girişte vermişsin gibi gösterirdi.
                out.append(alan(a, f"istenen: {istenen}   "
                                   f"(giriş alanı — sonradan yazılamaz)", "warn"))
        out.append(bilgi("işlem sonrası not olarak eklendi. "
                         "giriş gerekçesi olduğu gibi duruyor."))

    for note in coz.notlar:
        out.append(bilgi(f"  {note}"))
    return out


@skill("kayitlar", "son jurnal kayıtları", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="kayitlar [adet]")
async def _kayitlar(arg):
    kayitlar = depo.hepsi()
    if not kayitlar:
        return [bilgi("jurnal boş."), bilgi(f"örnek: {ORNEK}")]
    try:
        n = int(arg.strip()) if arg.strip() else 12
    except ValueError:
        n = 12
    out = []
    for k in kayitlar[-n:]:
        ihl = k.get("ihlaller")
        out.append(alan(f"{'✗ ' if ihl else ''}{k.get('id', '????')}", _baslik(k),
                        "warn" if ihl else ""))
    out.append(bilgi(f"{len(kayitlar)} kayıt · tek kayıt için: kayit <id>"))
    return out


@skill("kayit", "tek jurnal kaydı", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="kayit <id>")
async def _kayit(arg):
    if not arg.strip():
        return [uyari("kullanım: kayit <id>")]
    k = depo.bul(arg)
    if k is None:
        return [uyari(f"kayıt bulunamadı: {arg.strip()}")]

    out = [baslik(_baslik(k)), baslik("original")]
    for ad, etiket in SATIRLAR:
        if k.get(ad):
            d = k[ad]
            out.append(alan(etiket, ", ".join(d) if isinstance(d, list) else d))
    if k.get("yon") or k.get("risk") is not None or k.get("hedef_r") is not None:
        parca = []
        if k.get("yon"):
            parca.append(k["yon"])
        if isinstance(k.get("risk"), (int, float)):
            parca.append(f"risk %{k['risk']:g}")
        if isinstance(k.get("hedef_r"), (int, float)):
            parca.append(f"hedef {k['hedef_r']:g}R")
        for ad, etiket in (("sl", "SL"), ("tp", "TP")):
            if isinstance(k.get(ad), (int, float)):
                parca.append(f"{etiket} {k[ad]:g}")
        out.append(alan("plan", "  ".join(parca)))

    isaretli = [etiket for ad, etiket in
                (("stop_genisletme", "stop genişletme"), ("plan_disi_giris", "plan dışı giriş"))
                if k.get(ad) is True]
    if isaretli:
        out.append(alan("işaret", ", ".join(isaretli), "warn"))

    if k.get("duzeltildi"):
        out.append(alan("düzeltme",
                        f"{k['duzeltildi']} kez · son {str(k.get('duzeltme_t',''))[5:16].replace('T',' ')}"))

    if k.get("kontrol"):
        out.append(alan("kontrol", ", ".join(k["kontrol"])))
    if k.get("etiket"):
        out.append(alan("etiket", ", ".join(k["etiket"]), "warn"))

    ihlaller = k.get("ihlaller") or []
    out.append(alan("kural", "✓ ihlal yok" if not ihlaller else f"✗ {len(ihlaller)} ihlal",
                    "" if not ihlaller else "warn"))
    out += [alan("", f"✗ {m}", "warn") for m in ihlaller]

    # Bilinen alanların dışında kalanlar (kullanıcının kendi eklediği alanlar).
    bilinen = {"id", "t", "islem_t", "ihlaller", "yon", "risk", "hedef_r", "sonuc_r",
               "sembol", "stop_genisletme", "plan_disi_giris", "kontrol", "etiket",
               "duzeltildi", "duzeltme_t", "notlar", "skor",
               *(a for a, _ in SATIRLAR)}
    ekstra = {a: d for a, d in k.items() if a not in bilinen}
    if ekstra:
        out.append(bosluk())
        out += [alan(a, ", ".join(d) if isinstance(d, list) else d)
                for a, d in ekstra.items()]

    # İşlem sonrası notlar ORIGINAL'dan ayrı durur: sonradan eklenen gerekçe,
    # girişteki gerekçeymiş gibi görünmemeli.
    notlar = k.get("notlar") or []
    if notlar:
        out.append(bosluk())
        out.append(baslik("post-trade note"))
        for n in notlar:
            out.append(alan(str(n.get("t", ""))[5:16].replace("T", " "),
                            n.get("metin", "")))
    return out


@skill("istatistik", "jurnal özeti", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="istatistik", takma_adlar=("ist",))
async def _istatistik(arg):
    kayitlar = depo.hepsi()
    if not kayitlar:
        return [bilgi("jurnal boş — istatistik için önce kayıt gerek.")]

    kapali = [k for k in kayitlar
              if isinstance(k.get("sonuc_r"), (int, float))]
    acik = len(kayitlar) - len(kapali)

    out = [baslik(f"{len(kayitlar)} kayıt" + (f" · {acik} açık" if acik else ""))]
    if not kapali:
        out.append(bilgi("sonuçlanmış kayıt yok — R istatistiği çıkarılamaz."))
        return out

    rler = [float(k["sonuc_r"]) for k in kapali]
    kazanan = [r for r in rler if r > 0]
    out += [
        alan("toplam",    f"{sum(rler):+.2f}R"),
        alan("ortalama",  f"{sum(rler) / len(rler):+.2f}R"),
        alan("win rate",  f"%{100 * len(kazanan) / len(kapali):.0f}  "
                          f"({len(kazanan)}/{len(kapali)})"),
        alan("en iyi",    f"{max(rler):+.2f}R"),
        alan("en kötü",   f"{min(rler):+.2f}R"),
    ]

    dagilim: dict[str, list[float]] = {}
    for k in kapali:
        dagilim.setdefault((k.get("setup") or "—").strip(), []).append(float(k["sonuc_r"]))
    if dagilim:
        out.append(bosluk())
        out.append(baslik("setup dağılımı"))
        for setup, rs in sorted(dagilim.items(), key=lambda x: -sum(x[1])):
            out.append(alan(setup, f"{len(rs)} işlem   ort {sum(rs) / len(rs):+.2f}R"
                                   f"   top {sum(rs):+.2f}R"))

    ihlal_sayisi = sum(len(k.get("ihlaller") or []) for k in kayitlar)
    if ihlal_sayisi:
        out.append(bosluk())
        out.append(uyari(f"{ihlal_sayisi} kural ihlali kayıtlı — ayrıntı: ihlaller"))

    # Az örnekle çıkarılan oran gürültüdür; Venüs emin olmadığını söyler.
    if len(kapali) < 20:
        out.append(bosluk())
        out.append(bilgi(f"{len(kapali)} işlem az — bu oranlar henüz bir şey anlatmıyor."))
    return out


@skill("eksik", "sonuçlanmamış ve boş kayıtlar", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="eksik")
async def _eksik(arg):
    kayitlar = depo.hepsi()
    if not kayitlar:
        return [bilgi("jurnal boş.")]

    zorunlu = kural_motoru.yukle().deger("trading.zorunlu_alanlar", ())
    acik = [k for k in kayitlar if not isinstance(k.get("sonuc_r"), (int, float))]
    bosluklu = [(k, [a for a in zorunlu if not str(k.get(a) or "").strip()])
                for k in kayitlar]
    bosluklu = [(k, eksikler) for k, eksikler in bosluklu if eksikler]

    if not acik and not bosluklu and not [
            k for k in kayitlar
            if playbook_motoru.yukle(kurallar=kural_motoru.yukle()).setup(
                k.get("setup", "")) is not None and "kontrol" not in k]:
        bugun = len(depo.gun(date.today(), kayitlar))
        return [bilgi("eksik kayıt yok." + (f" bugün {bugun} işlem." if bugun else ""))]

    out = []
    if acik:
        out.append(baslik(f"{len(acik)} kayıt sonuçlanmamış"))
        out.append(bilgi("kapatmak için: tamamla <id> sonuc_r=2.4"))
        out += [alan(k.get("id", "????"), _baslik(k)) for k in acik[-10:]]
        out.append(bosluk())
    # Kontrol listesi HİÇ cevaplanmamış kayıtlar. İşaretlenmemiş madde geçerli
    # bir cevaptır ("görmedim"); hiç cevaplamamak eksikliktir.
    pb = playbook_motoru.yukle(kurallar=kural_motoru.yukle())
    cevapsiz = [k for k in kayitlar
                if pb.setup(k.get("setup", "")) is not None and "kontrol" not in k]
    if cevapsiz:
        out.append(baslik(f"{len(cevapsiz)} kayıtta kontrol listesi cevaplanmamış"))
        out += [alan(k.get("id", "????"), f"{k.get('sembol','?')}  setup {k.get('setup')}")
                for k in cevapsiz[-10:]]
        out.append(bilgi("cevaplamak artık mümkün değil — giriş anına ait. "
                         "sonraki kayıtta kontrol=... yaz."))
        out.append(bosluk())

    if bosluklu:
        out.append(baslik(f"{len(bosluklu)} kayıtta zorunlu alan boş"))
        out += [alan(f"{k.get('id', '????')}  {k.get('sembol', '?')}", ", ".join(e), "warn")
                for k, e in bosluklu[-10:]]
    return out
