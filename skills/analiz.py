"""
Analiz yeteneği — kırılımlar ve tekrarlanan davranışlar.

Çekirdek hesaplar (core/analiz.py), bu dosya sunar. Sayı üretilir, tavsiye
üretilmez (Değişmez 4): "geç girişlerin -4.7R" bir gözlemdir, "geç girme"
bir emirdir. Venüs birincisini söyler.
"""

from core.registry import Risk, Perm, skill, bilgi, uyari, alan, baslik, bosluk
from core import analiz as motor
from core import jurnal as depo

GORUNUM = ("setup", "seans", "sembol", "rr", "skor", "hata")

KAYNAK = {"etiket": "senin etiketin", "kural": "denetçi yakaladı"}


def _grup_satiri(g) -> dict:
    ek = "" if g.yeterli else f"   az örnek"
    return alan(g.ad,
                f"{g.adet:>3} işlem   {g.toplam_r:+.1f}R   ort {g.ort_r:+.2f}R"
                f"   %{g.basari:.0f}{ek}",
                "" if g.yeterli else "dim")


def _kirilim_bolumu(baslik_ad, gruplar) -> list:
    if not gruplar:
        return []
    out = [baslik(baslik_ad)] + [_grup_satiri(g) for g in gruplar]
    iyi, kotu = motor.en_iyi_kotu(gruplar)
    if iyi is not None and kotu is not None and iyi.ad != kotu.ad:
        out.append(alan("→ en iyi / en kötü", f"{iyi.ad}  ·  {kotu.ad}", "acik"))
    out.append(bosluk())
    return out


@skill("analiz", "kırılımlar ve tekrarlanan davranışlar", Risk.YESIL,
       izinler=(Perm.OKUMA,), kullanim="analiz [setup|seans|sembol|rr|skor|hata]")
async def _analiz(arg):
    kayitlar = depo.hepsi()
    kapali = motor.kapali(kayitlar)
    if not kapali:
        return [bilgi("sonuçlanmış kayıt yok — analiz için önce jurnal gerek.")]

    istenen = arg.strip().lower()
    if istenen and istenen not in GORUNUM:
        return [uyari(f"bilinmeyen görünüm: {istenen}"),
                bilgi("görünümler: " + ", ".join(GORUNUM))]

    toplam = sum(k["sonuc_r"] for k in kapali)
    out = [baslik(f"{len(kapali)} sonuçlanmış işlem · {toplam:+.1f}R")]

    def ister(ad):
        return not istenen or istenen == ad

    if ister("setup"):
        out += _kirilim_bolumu("setup", motor.kirilim(kapali, lambda k: k.get("setup")))
    if ister("seans"):
        out += _kirilim_bolumu("seans", motor.kirilim(kapali, lambda k: k.get("seans")))
    if ister("sembol"):
        out += _kirilim_bolumu("sembol", motor.kirilim(kapali, lambda k: k.get("sembol")))
    if ister("rr"):
        out += _kirilim_bolumu("planlanan R:R", motor.rr_kirilimi(kapali))

    if ister("skor"):
        skorlar = motor.skor_kirilimi(kapali)
        if skorlar:
            out.append(baslik("kalite skoru → sonuç"))
            out += [_grup_satiri(g) for g in skorlar]
            # Playbook'un bir şey ölçüp ölçmediğinin tek objektif kanıtı.
            yeterli = [g for g in skorlar if g.yeterli]
            if len(yeterli) >= 2:
                ust, alt = yeterli[0], yeterli[-1]
                fark = ust.ort_r - alt.ort_r
                out.append(alan("→ fark",
                                f"{ust.ad} ile {alt.ad} arası {fark:+.2f}R/işlem",
                                "acik" if fark > 0 else "warn"))
                if fark <= 0:
                    out.append(bilgi("yüksek skorlu işlemler daha iyi sonuç vermiyor — "
                                     "kontrol listesi bir şey ölçmüyor olabilir."))
            out.append(bosluk())

    if ister("hata"):
        dvr = [d for d in motor.davranislar(kayitlar) if d.adet]
        if dvr:
            out.append(baslik("tekrarlanan davranışlar"))
            for d in dvr:
                out.append(alan(f"{d.ad}  ({KAYNAK.get(d.kaynak, d.kaynak)})",
                                f"{d.adet:>3}x   {d.kar}K / {d.zarar}Z   "
                                f"{d.toplam_r:+.1f}R",
                                "warn" if d.toplam_r < 0 else ""))
            zararli = [d for d in dvr if d.toplam_r < 0]
            if zararli:
                # Davranışların R'leri TOPLANMAZ: bir işlem birden fazla
                # davranışa girebilir. Birleşik etki, bu davranışlardan en az
                # birinin görüldüğü işlemlerin toplamıdır.
                net, adet = motor.net_etki(zararli, kayitlar)
                out.append(alan("→ zararlı davranışların birleşik etkisi",
                                f"{net:+.1f}R   ({adet} işlem)", "warn"))
                out.append(bilgi("bir işlem birden fazla davranışa girebilir; "
                                 "satırların R'leri toplanmaz."))
            out.append(bosluk())

    az = [g for g in motor.kirilim(kapali, lambda k: k.get("setup")) if not g.yeterli]
    if len(kapali) < 20 or az:
        out.append(bilgi(f"az örnek işaretli gruplar sıralamaya girmiyor "
                         f"(en az {motor.ASGARI_ORNEK} işlem). "
                         f"Bu sayılar arttıkça anlam kazanır."))
    return out
