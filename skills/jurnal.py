"""
Jurnal yetenekleri — kayıt, listeleme, istatistik.

Şartname Bölüm 11. Kayıt biçimi ve depo core/jurnal.py'de, kural denetimi
core/denetci.py'de; burada giriş ve gösterim var.

Kayıt anında kurallar denetlenir ve ihlal **kaydedilir, engellenmez**
(Bölüm 5). Venüs hatırlatır, sonra çekilir — karar kullanıcınındır.
"""

from datetime import datetime

from core.registry import Risk, Perm, skill, satir, bilgi, uyari, vurgu
from core import jurnal as depo
from core import denetci
from core import kurallar as kural_motoru

AYLAR = ("Oca", "Şub", "Mar", "Nis", "May", "Haz",
         "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")

# Bölüm 11'deki kayıt düzeni: sıra ve etiketler oradan.
SATIRLAR = (("setup", "SETUP"), ("seans", "SEANS"), ("giris_sebebi", "GİRİŞ"),
            ("execution", "EXECUTION"), ("duygu", "DUYGU"))

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
        isaret = "✗" if k.get("ihlaller") else " "
        out.append(satir(f" {isaret} {k.get('id', '????')}  {_baslik(k)}"))
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

    out = [vurgu(_baslik(k))]
    for alan, etiket in SATIRLAR:
        if k.get(alan):
            out.append(satir(f"{etiket:<10}: {k[alan]}"))
    if k.get("yon") or k.get("risk") is not None or k.get("hedef_r") is not None:
        parca = []
        if k.get("yon"):
            parca.append(k["yon"])
        if isinstance(k.get("risk"), (int, float)):
            parca.append(f"risk %{k['risk']:g}")
        if isinstance(k.get("hedef_r"), (int, float)):
            parca.append(f"hedef {k['hedef_r']:g}R")
        out.append(satir(f"{'PLAN':<10}: {'  '.join(parca)}"))

    isaretli = [etiket for alan, etiket in
                (("stop_genisletme", "stop genişletme"), ("plan_disi_giris", "plan dışı giriş"))
                if k.get(alan) is True]
    if isaretli:
        out.append(satir(f"{'İŞARET':<10}: {', '.join(isaretli)}"))

    ihlaller = k.get("ihlaller") or []
    out.append(satir(f"{'KURAL':<10}: " +
                     ("✓ ihlal yok" if not ihlaller else f"✗ {len(ihlaller)} ihlal")))
    out += [uyari(f"            ✗ {m}") for m in ihlaller]

    # Bilinen alanların dışında kalanlar (kullanıcının kendi eklediği alanlar).
    bilinen = {"id", "t", "islem_t", "ihlaller", "yon", "risk", "hedef_r", "sonuc_r",
               "sembol", "stop_genisletme", "plan_disi_giris", *(a for a, _ in SATIRLAR)}
    ekstra = {a: d for a, d in k.items() if a not in bilinen}
    if ekstra:
        out.append(bilgi(""))
        out += [satir(f"{a:<10}: {d}") for a, d in ekstra.items()]
    return out
