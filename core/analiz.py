"""
Analiz — kullanıcıyı modelleme katmanı.

`istatistik` "ne oldu" der (win rate, ortalama R). Bu dosya "NEDEN oldu ve
tekrar mı ediyor" sorusuna bakar: hangi setup, hangi seans, hangi davranış
para kazandırıyor ya da kaybettiriyor.

Üç ilke:

1. **Deterministik.** Modele hiçbir şey sorulmaz. Aynı jurnal her zaman aynı
   analizi verir; yoksa "en kârlı setup" bir ölçü değil bir izlenim olur.

2. **Az örnek istatistik değildir.** 2 işlemlik bir setup "en kârlı" ilan
   edilirse sistem seni gürültüye göre yönlendirir. `ASGARI_ORNEK` altındaki
   gruplar gösterilir ama sıralamaya girmez ve işaretlenir.

3. **Yorum yok.** Bu dosya sayı üretir, tavsiye üretmez (Değişmez 4). "Şu
   setup'ı bırak" demek analiz katmanının işi değildir.

Davranışlar iki kaynaktan gelir ve tek listede toplanır:
- kullanıcının kendi etiketleri (`etiket=fomo,gec_giris`)
- denetçinin yakaladığı kural ihlalleri (ihlaller.jsonl, kayıt id'siyle)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from . import denetci

# Bir grubun "en iyi / en kötü" sıralamasına girebilmesi için gereken işlem
# sayısı. Altındakiler görünür ama sıralanmaz.
ASGARI_ORNEK = 5

RR_BANTLARI = ((0.0, 1.0, "< 1R"), (1.0, 2.0, "1 – 2R"),
               (2.0, 3.0, "2 – 3R"), (3.0, float("inf"), "3R +"))

SKOR_BANTLARI = ((90, 101, "90 – 100"), (70, 90, "70 – 89"),
                 (50, 70, "50 – 69"), (0, 50, "0 – 49"))


def _r(kayit: dict) -> float | None:
    d = kayit.get("sonuc_r")
    if isinstance(d, bool) or not isinstance(d, (int, float)):
        return None
    return float(d)


def kapali(kayitlar: Iterable[dict]) -> list[dict]:
    """Yalnızca sonuçlanmış kayıtlar. Açık pozisyon hiçbir ortalamaya girmez."""
    return [k for k in kayitlar if _r(k) is not None]


@dataclass(frozen=True)
class Grup:
    ad: str
    adet: int
    kazanan: int
    toplam_r: float
    ort_skor: float | None

    @property
    def ort_r(self) -> float:
        return self.toplam_r / self.adet if self.adet else 0.0

    @property
    def basari(self) -> float:
        return 100 * self.kazanan / self.adet if self.adet else 0.0

    @property
    def yeterli(self) -> bool:
        return self.adet >= ASGARI_ORNEK


def kirilim(kayitlar: Iterable[dict], anahtar: Callable[[dict], Any]) -> list[Grup]:
    """Kayıtları bir anahtara göre gruplar ve toplam R'ye göre sıralar.

    Anahtar None dönerse kayıt o kırılıma girmez (örn. seansı yazılmamış kayıt
    seans kırılımını kirletmesin).
    """
    havuz: dict[str, list[dict]] = {}
    for k in kapali(kayitlar):
        ad = anahtar(k)
        if ad is None or str(ad).strip() == "":
            continue
        havuz.setdefault(str(ad), []).append(k)

    gruplar = []
    for ad, liste in havuz.items():
        rler = [_r(k) for k in liste]
        skorlar = [k["skor"] for k in liste if isinstance(k.get("skor"), (int, float))]
        gruplar.append(Grup(ad=ad, adet=len(liste),
                            kazanan=sum(1 for r in rler if r > 0),
                            toplam_r=sum(rler),
                            ort_skor=sum(skorlar) / len(skorlar) if skorlar else None))
    gruplar.sort(key=lambda g: -g.toplam_r)
    return gruplar


def en_iyi_kotu(gruplar: list[Grup]) -> tuple[Grup | None, Grup | None]:
    """Yalnızca yeterli örneği olan gruplar sıralamaya girer."""
    yeterli = [g for g in gruplar if g.yeterli]
    if not yeterli:
        return None, None
    return yeterli[0], yeterli[-1]


def rr_kirilimi(kayitlar: Iterable[dict]) -> list[Grup]:
    """Planlanan R:R'ye göre. "RR 2.8+ kazandırıyor" bilgisi buradan çıkar."""
    def band(k):
        h = k.get("hedef_r")
        if isinstance(h, bool) or not isinstance(h, (int, float)):
            return None
        for alt, ust, ad in RR_BANTLARI:
            if alt <= h < ust:
                return ad
        return None
    return kirilim(kayitlar, band)


def skor_kirilimi(kayitlar: Iterable[dict]) -> list[Grup]:
    """Kalite skoru bandına göre sonuç.

    Playbook'un gerçekten işe yarayıp yaramadığının tek objektif kanıtı budur:
    yüksek skorlu işlemler daha iyi sonuç veriyorsa kontrol listesi bir şey
    ölçüyor demektir. Vermiyorsa listeyi gözden geçirmek gerekir.
    """
    def band(k):
        s = k.get("skor")
        if isinstance(s, bool) or not isinstance(s, (int, float)):
            return None
        for alt, ust, ad in SKOR_BANTLARI:
            if alt <= s < ust:
                return ad
        return None
    gruplar = skor_kirilimi_sirala(kirilim(kayitlar, band))
    return gruplar


def skor_kirilimi_sirala(gruplar: list[Grup]) -> list[Grup]:
    sira = [ad for _, _, ad in SKOR_BANTLARI]
    return sorted(gruplar, key=lambda g: sira.index(g.ad) if g.ad in sira else 99)


@dataclass(frozen=True)
class Davranis:
    ad: str
    kaynak: str            # "etiket" (senin beyanın) | "kural" (denetçi yakaladı)
    adet: int              # kaç işlemde görüldü
    kapali: int            # bunların kaçı sonuçlandı
    zarar: int
    kar: int
    toplam_r: float
    kimlikler: frozenset   # hangi kayıtlarda — toplamı çıkarırken şart


def net_etki(davranislar: Iterable[Davranis], kayitlar: Iterable[dict]) -> tuple[float, int]:
    """Davranışların BİRLEŞİK R etkisi.

    Davranışların R'lerini toplamak yanlıştır: tek bir kötü işlem hem "fomo"
    hem "izinli olmayan seans" hem "risk aşımı" olabilir; toplarsan aynı zararı
    üç kez sayarsın ve gerçekte olduğundan çok daha kötü bir tablo çıkar.
    Doğru sayı, bu davranışlardan EN AZ BİRİNİN görüldüğü işlemlerin toplamıdır.
    """
    indeks = {k.get("id"): k for k in kayitlar if k.get("id")}
    kimlikler: set = set()
    for d in davranislar:
        kimlikler |= d.kimlikler
    rler = [_r(indeks[i]) for i in kimlikler
            if i in indeks and _r(indeks[i]) is not None]
    return sum(rler), len(rler)


def davranislar(kayitlar: Iterable[dict]) -> list[Davranis]:
    """Tekrarlanan davranışlar ve toplam R etkileri.

    Etiketler kullanıcının beyanı, kural ihlalleri denetçinin tespiti. İkisi
    tek listede ama kaynağı işaretli — "fomo" senin dediğin, "izinli_seanslar"
    Venüs'ün gördüğü.
    """
    kayit_indeks = {k.get("id"): k for k in kayitlar if k.get("id")}

    # davranış -> kayıt id kümesi
    havuz: dict[tuple[str, str], set[str]] = {}

    for k in kayitlar:
        for e in (k.get("etiket") or []):
            havuz.setdefault((str(e), "etiket"), set()).add(k.get("id"))

    # ihlaller.jsonl kural adını kayıt id'siyle tutuyor — şema değişikliği
    # gerekmeden buradan birleştiriliyor.
    for i in denetci.hepsi():
        kimlik, kural = i.get("kayit"), i.get("kural")
        if kimlik in kayit_indeks and kural:
            havuz.setdefault((str(kural).split(".", 1)[-1], "kural"), set()).add(kimlik)

    out = []
    for (ad, kaynak), kimlikler in havuz.items():
        ilgili = [kayit_indeks[i] for i in kimlikler if i in kayit_indeks]
        rler = [_r(k) for k in ilgili if _r(k) is not None]
        out.append(Davranis(ad=ad, kaynak=kaynak, adet=len(ilgili),
                            kapali=len(rler),
                            zarar=sum(1 for r in rler if r < 0),
                            kar=sum(1 for r in rler if r > 0),
                            toplam_r=sum(rler),
                            kimlikler=frozenset(kimlikler)))
    # En çok zarar ettiren önce: bakılması gereken sıra bu.
    out.sort(key=lambda d: (d.toplam_r, -d.adet))
    return out
