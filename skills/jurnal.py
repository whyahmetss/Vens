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
from core.bildirim import Seviye, bildir

AYLAR = ("Oca", "Şub", "Mar", "Nis", "May", "Haz",
         "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")

# Bölüm 11'deki kayıt düzeni: sıra ve etiketler oradan.
# Etiketler baştan küçük harf: "GİRİŞ".lower() Python'da "gi̇ri̇ş" üretir
# (birleşen nokta). Büyük harfe çevirmek gerekirse kabuk Türkçe kurallarıyla yapar.
SATIRLAR = (("setup", "setup"), ("seans", "seans"), ("giris_sebebi", "giriş"),
            ("execution", "execution"), ("duygu", "duygu"))

ORNEK = ('jurnal sembol=XAUUSD yon=long seans=londra risk=1 hedef_r=3 sonuc_r=2.4 '
         'setup="sweep → MSS → FVG" giris_sebebi="OTE 0.705" execution=iyi duygu=sabırsız')


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
                bilgi(""), bilgi("alanlar: sembol yon seans risk hedef_r sonuc_r "
                                 "setup giris_sebebi execution duygu"),
                bilgi("        stop_genisletme plan_disi_giris zaman"),
                bilgi("sonuc_r boş bırakılırsa pozisyon açık sayılır.")]

    coz = depo.ayristir(arg)
    if coz.hatalar:
        return [uyari("kayıt yazılmadı:")] + [satir(f"  {h}") for h in coz.hatalar]

    kayit = depo.hazirla(coz.veri)
    kurallar = kural_motoru.yukle()

    # Günlük limit ve bekleme kuralları bu kaydı da sayar.
    gunun = depo.gun(datetime.fromisoformat(kayit["islem_t"]).date()) + [kayit]
    ihlaller = denetci.denetle(kayit, kurallar, gunun)
    if ihlaller:
        kayit["ihlaller"] = [i.mesaj for i in ihlaller]

    depo.yaz(kayit)
    denetci.kaydet(kayit, ihlaller)
    for i in ihlaller:
        # Bölüm 12: kural ihlali anı KRİTİK. Ama kullanıcı bu kaydı kendi
        # girdi, uyarı zaten aşağıda görünüyor — kesinti değil, bütçeden
        # düşmez. Kayda geçer ki `bildirimler` ve geçmiş eksik kalmasın.
        bildir(Seviye.KRITIK, i.mesaj, f"jurnal:{kayit['id']}", kesintisiz=True)

    out = [bilgi(f"kaydedildi · {kayit['id']}"), satir(_baslik(kayit))]
    for note in coz.notlar:
        out.append(bilgi(f"  {note}"))
    if ihlaller:
        out.append(satir(""))
        out.append(uyari(f"{len(ihlaller)} kural ihlali:"))
        out += [uyari(f"  ✗ {i.mesaj}") for i in ihlaller]
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
                satir("  tamamla a3f1 sonuc_r=2.4 execution=iyi"),
                bilgi("eski değer silinmez — düzeltme yeni satır olarak yazılır.")]

    kimlik = parca[0].strip().lower()
    mevcut = depo.bul(kimlik)
    if mevcut is None:
        return [uyari(f"kayıt bulunamadı: {kimlik}")]

    coz = depo.ayristir(parca[1])
    if coz.hatalar:
        return [uyari("düzeltme yazılmadı:")] + [satir(f"  {h}") for h in coz.hatalar]
    if not coz.veri:
        return [uyari("değişecek alan yok.")]

    # islem_t düzeltilebilir ama kaydın kimliği ve yazılma zamanı değişmez.
    veri = {a: d for a, d in coz.veri.items() if a not in ("id", "t")}
    guncel = {**mevcut, **veri}

    # Sonuç girilince günün net kaybı değişir; ihlaller yeniden hesaplanmalı.
    kurallar = kural_motoru.yukle()
    gun_tarihi = datetime.fromisoformat(guncel["islem_t"]).date()
    gunun = [guncel if k.get("id") == kimlik else k for k in depo.gun(gun_tarihi)]
    if all(k.get("id") != kimlik for k in gunun):
        gunun.append(guncel)
    ihlaller = denetci.denetle(guncel, kurallar, gunun)

    onceki = set(mevcut.get("ihlaller") or [])
    veri["ihlaller"] = [i.mesaj for i in ihlaller]
    depo.duzelt(kimlik, veri)

    # Yalnızca YENİ ihlaller kaydedilir; eskiler ihlaller.jsonl'da zaten var.
    yeni_ihlal = [i for i in ihlaller if i.mesaj not in onceki]
    if yeni_ihlal:
        denetci.kaydet(guncel, yeni_ihlal)
        for i in yeni_ihlal:
            bildir(Seviye.KRITIK, i.mesaj, f"jurnal:{kimlik}", kesintisiz=True)

    out = [bilgi(f"güncellendi · {kimlik}"), satir(_baslik(guncel))]
    out += [alan(a, str(d)) for a, d in veri.items() if a != "ihlaller"]
    for note in coz.notlar:
        out.append(bilgi(f"  {note}"))
    if yeni_ihlal:
        out.append(satir(""))
        out.append(uyari(f"{len(yeni_ihlal)} yeni kural ihlali:"))
        out += [uyari(f"  ✗ {i.mesaj}") for i in yeni_ihlal]
        out.append(bilgi("kaydedildi, engellenmedi. karar senin."))
    kalkan = onceki - {i.mesaj for i in ihlaller}
    if kalkan:
        # Düzeltme bir ihlali "kaldırdıysa" bu sessizce geçmemeli.
        out.append(bilgi(f"{len(kalkan)} ihlal artık geçerli değil — "
                         f"eski kayıt jurnalde duruyor."))
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

    out = [baslik(_baslik(k))]
    for ad, etiket in SATIRLAR:
        if k.get(ad):
            out.append(alan(etiket, k[ad]))
    if k.get("yon") or k.get("risk") is not None or k.get("hedef_r") is not None:
        parca = []
        if k.get("yon"):
            parca.append(k["yon"])
        if isinstance(k.get("risk"), (int, float)):
            parca.append(f"risk %{k['risk']:g}")
        if isinstance(k.get("hedef_r"), (int, float)):
            parca.append(f"hedef {k['hedef_r']:g}R")
        out.append(alan("plan", "  ".join(parca)))

    isaretli = [etiket for ad, etiket in
                (("stop_genisletme", "stop genişletme"), ("plan_disi_giris", "plan dışı giriş"))
                if k.get(ad) is True]
    if isaretli:
        out.append(alan("işaret", ", ".join(isaretli), "warn"))

    if k.get("duzeltildi"):
        out.append(alan("düzeltme",
                        f"{k['duzeltildi']} kez · son {str(k.get('duzeltme_t',''))[5:16].replace('T',' ')}"))

    ihlaller = k.get("ihlaller") or []
    out.append(alan("kural", "✓ ihlal yok" if not ihlaller else f"✗ {len(ihlaller)} ihlal",
                    "" if not ihlaller else "warn"))
    out += [alan("", f"✗ {m}", "warn") for m in ihlaller]

    # Bilinen alanların dışında kalanlar (kullanıcının kendi eklediği alanlar).
    bilinen = {"id", "t", "islem_t", "ihlaller", "yon", "risk", "hedef_r", "sonuc_r",
               "sembol", "stop_genisletme", "plan_disi_giris",
               "duzeltildi", "duzeltme_t", *(a for a, _ in SATIRLAR)}
    ekstra = {a: d for a, d in k.items() if a not in bilinen}
    if ekstra:
        out.append(bosluk())
        out += [alan(a, d) for a, d in ekstra.items()]
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

    if not acik and not bosluklu:
        bugun = len(depo.gun(date.today(), kayitlar))
        return [bilgi("eksik kayıt yok." + (f" bugün {bugun} işlem." if bugun else ""))]

    out = []
    if acik:
        out.append(baslik(f"{len(acik)} kayıt sonuçlanmamış"))
        out.append(bilgi("kapatmak için: tamamla <id> sonuc_r=2.4"))
        out += [alan(k.get("id", "????"), _baslik(k)) for k in acik[-10:]]
        out.append(bosluk())
    if bosluklu:
        out.append(baslik(f"{len(bosluklu)} kayıtta zorunlu alan boş"))
        out += [alan(f"{k.get('id', '????')}  {k.get('sembol', '?')}", ", ".join(e), "warn")
                for k, e in bosluklu[-10:]]
    return out
