"""
Koç — istatistiği yüzüne tutan katman.

**Şablonlar sabittir ve bu dosyada görünür.** LLM kullanılmaz. Sebep Bölüm
10'daki epistemik gerekçenin aynısı: modelin ürettiği ikna edici bir cümle,
logdan senin kendi çıkarımından ayırt edilemez. Koç seni ikna etmemeli,
sayıyı önüne koymalı.

Değişmez 4 burada en incedir. Kural şu:

    Koç ASLA "şunu yap" ya da "şunu yapma" demez.
    Sayıyı söyler ve soruyu sorar. Karar kullanıcınındır.

Her şablonun sonu bir soru ya da çıplak bir istatistiktir. Emir kipi yoktur.
Bir şablon eklerken bu kurala uyduğunu doğrula.

Eşikler gürültüyü keser: 4 tekrardan az bir davranış, 5 işlemden az bir grup
ya da 1R'den küçük bir etki bulgu sayılmaz. Az örneğe dayanarak birini
sorguya çekmek, onu gürültüye göre davranmaya iter.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import analiz

ASGARI_TEKRAR = 4       # bir davranışın bulgu sayılması için
ASGARI_ISLEM = 5        # bir grubun (seans/setup/sembol) bulgu sayılması için
ASGARI_ETKI = 1.0       # R cinsinden, altındaki fark gürültüdür


# Bir bulgunun işlemlerinin bu oranı daha önemli bir bulgu tarafından zaten
# kapsanıyorsa gösterilmez. Aynı 9 kötü işlem "fomo", "risk aşımı", "izinsiz
# seans" ve "min_rr" olarak dört kez sorulursa tek problem dört sorun gibi
# görünür ve mesaj sulanır.
ORTUSME_ESIGI = 0.8


@dataclass(frozen=True)
class Bulgu:
    baslik: str
    satirlar: tuple[str, ...]
    soru: str
    onem: float          # sıralama için: |R| etkisi
    kimlikler: frozenset = frozenset()
    kapsanan: tuple[str, ...] = ()   # bu bulgunun örttüğü diğer başlıklar


# --- şablonlar --------------------------------------------------------------
# Hepsi ya soruyla ya da çıplak sayıyla biter. Emir kipi yok.

SABLON_DAVRANIS = (
    "son {toplam} işleminde {adet} kez görüldü",
    "{zarar} zarar / {kar} kâr",
    "toplam etki {r:+.1f}R",
)
SORU_DAVRANIS = "Bu davranışı sürdürmek için istatistiksel gerekçen nedir?"

SABLON_GRUP = (
    "{adet} işlem, toplam {r:+.1f}R",
    "işlem başına {ort:+.2f}R, başarı %{basari:.0f}",
)
SORU_GRUP = "Burada işlem yapmayı sürdürmek için istatistiksel gerekçen nedir?"

SORU_SKOR_ISLIYOR = ("Kontrol listeni tamamlamadan girdiğin {eksik} işlem var. "
                     "Bunları neye dayanarak aldın?")
SORU_SKOR_ISLEMIYOR = ("Kontrol listesi sonucu öngörmüyor. Liste gerçekten bir şey "
                       "ölçüyor mu, yoksa alışkanlık mı?")

SORU_TEMIZ = None       # bulgu yoksa soru da yok


def bulgular(kayitlar) -> list[Bulgu]:
    """Eşikleri geçen gözlemleri, önem sırasına göre döndürür."""
    kapali = analiz.kapali(kayitlar)
    toplam = len(kapali)
    if toplam < ASGARI_ISLEM:
        return []

    out: list[Bulgu] = []

    # --- tekrarlanan davranışlar ---
    for d in analiz.davranislar(kayitlar):
        if d.adet < ASGARI_TEKRAR or d.toplam_r > -ASGARI_ETKI:
            continue
        kaynak = "senin etiketin" if d.kaynak == "etiket" else "denetçi yakaladı"
        out.append(Bulgu(
            baslik=f"{d.ad}  ({kaynak})",
            satirlar=tuple(s.format(toplam=toplam, adet=d.adet, zarar=d.zarar,
                                    kar=d.kar, r=d.toplam_r)
                           for s in SABLON_DAVRANIS),
            soru=SORU_DAVRANIS, onem=abs(d.toplam_r),
            kimlikler=d.kimlikler))

    # --- zarar ettiren gruplar ---
    for etiket, anahtar in (("seans", lambda k: k.get("seans")),
                            ("setup", lambda k: k.get("setup")),
                            ("sembol", lambda k: k.get("sembol"))):
        for g in analiz.kirilim(kapali, anahtar):
            if g.adet < ASGARI_ISLEM or g.toplam_r > -ASGARI_ETKI:
                continue
            kimlikler = frozenset(
                k["id"] for k in kapali
                if k.get("id") and str(anahtar(k)) == g.ad)
            out.append(Bulgu(
                baslik=f"{etiket}: {g.ad}",
                satirlar=tuple(s.format(adet=g.adet, r=g.toplam_r,
                                        ort=g.ort_r, basari=g.basari)
                               for s in SABLON_GRUP),
                soru=SORU_GRUP, onem=abs(g.toplam_r),
                kimlikler=kimlikler))

    # --- kontrol listesi işe yarıyor mu ---
    bantlar = [g for g in analiz.skor_kirilimi(kapali) if g.yeterli]
    if len(bantlar) >= 2:
        ust, alt = bantlar[0], bantlar[-1]
        fark = ust.ort_r - alt.ort_r
        if fark >= ASGARI_ETKI:
            eksik = _eksik_kontrol(kapali)
            out.append(Bulgu(
                baslik="kontrol listesi işe yarıyor",
                satirlar=(f"{ust.ad} bandı işlem başına {ust.ort_r:+.2f}R",
                          f"{alt.ad} bandı işlem başına {alt.ort_r:+.2f}R",
                          f"aradaki fark {fark:+.2f}R/işlem"),
                soru=SORU_SKOR_ISLIYOR.format(eksik=eksik), onem=fark))
        elif fark <= 0:
            out.append(Bulgu(
                baslik="kontrol listesi sonucu öngörmüyor",
                satirlar=(f"{ust.ad} bandı {ust.ort_r:+.2f}R",
                          f"{alt.ad} bandı {alt.ort_r:+.2f}R",
                          "yüksek skor daha iyi sonuç getirmiyor"),
                soru=SORU_SKOR_ISLEMIYOR, onem=abs(fark) + 0.5))

    out.sort(key=lambda b: -b.onem)
    return _ortusenleri_ele(out)


def _eksik_kontrol(kapali) -> int:
    """Setup'ı playbook'ta tanımlı olup kontrol listesi eksik kalan işlemler."""
    from . import kurallar as kural_motoru
    from . import playbook as playbook_motoru
    pb = playbook_motoru.yukle(kurallar=kural_motoru.yukle())
    n = 0
    for k in kapali:
        setup = pb.setup(k.get("setup", ""))
        if setup is None:
            continue
        isaretli = {str(x).lower() for x in (k.get("kontrol") or [])}
        if any(m.ad not in isaretli for m in setup.kontrol):
            n += 1
    return n


def _ortusenleri_ele(bulgular: list[Bulgu]) -> list[Bulgu]:
    """Aynı işlemleri gösteren bulguları teke indirir.

    En önemli bulgu kalır; onun işlemlerinin büyük kısmını tekrar eden bulgular
    "ayrıca şu adlarla da görünüyor" satırına iner. Amaç bilgiyi saklamak değil,
    tek problemi dört ayrı soru gibi sormamak.
    """
    tutulan: list[Bulgu] = []
    for b in bulgular:
        if not b.kimlikler:
            tutulan.append(b)
            continue
        ortusen = None
        for t in tutulan:
            if not t.kimlikler:
                continue
            ortak = len(b.kimlikler & t.kimlikler)
            if ortak / len(b.kimlikler) >= ORTUSME_ESIGI:
                ortusen = t
                break
        if ortusen is None:
            tutulan.append(b)
        else:
            i = tutulan.index(ortusen)
            tutulan[i] = Bulgu(
                baslik=ortusen.baslik, satirlar=ortusen.satirlar, soru=ortusen.soru,
                onem=ortusen.onem, kimlikler=ortusen.kimlikler,
                kapsanan=ortusen.kapsanan + (b.baslik,))
    return tutulan


def ozet(kayitlar) -> tuple[int, int, float, int]:
    """(işlem, farklı davranış, birleşik R etkisi, etkilenen işlem).

    Kullanıcının istediği "son 63 işleminde 4 farklı hata tekrarlandı" satırı.
    R'ler toplanmaz — bir işlem birden fazla davranışa girebilir (bkz. analiz).
    """
    kapali = analiz.kapali(kayitlar)
    zararli = [d for d in analiz.davranislar(kayitlar)
               if d.adet >= ASGARI_TEKRAR and d.toplam_r <= -ASGARI_ETKI]
    net, adet = analiz.net_etki(zararli, kayitlar)
    return len(kapali), len(zararli), net, adet
