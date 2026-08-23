"""
Review — işlem öncesi gerekçe ile işlem sonrası gerçeğin karşılaştırması.

Kullanıcının sorusu: "İşlem öncesindeki gerekçen ile işlem sonrasındaki
gerekçen aynı mı?" Kendi kendini kandırıp kandırmadığını burada yakalarsın.

Serbest metni anlamlandırmak LLM işidir ve bu dosya LLM kullanmaz. Bunun
yerine deterministik olarak ÖLÇÜLEBİLİR sapmalara bakar:

- planlanan hedef ile gerçekleşen sonucun ilişkisi (erken çıkış, aşırı kayıp)
- girişte kontrol listesinin tamamlanmış olup olmadığı
- işlemden SONRA gerekçeye eklenmek istenen şeyler (post-trade notlar)

Sonuncusu en önemlisi: not varsa, girişte söylemediğin bir şeyi sonradan
söylemek istemişsindir. Venüs bunu engellemez, görünür kılar.

Bu dosya yorum yapmaz, gözlem üretir. "Erken çıkmışsın" bir ölçüm;
"erken çıkma" bir emirdir (Değişmez 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Hedefin bu oranının altında kapatılan kârlı işlem "erken çıkış" sayılır.
ERKEN_ORAN = 0.6
# 1R'nin bu katından fazla kayıp, stop'un planlandığı yerde olmadığını gösterir.
ASIRI_KAYIP = 1.05


@dataclass(frozen=True)
class Gozlem:
    ad: str
    metin: str
    sapma: bool          # True ise plandan sapılmış


def _sayi(kayit: dict, alan: str) -> float | None:
    d = kayit.get(alan)
    if isinstance(d, bool) or not isinstance(d, (int, float)):
        return None
    return float(d)


def incele(kayit: dict[str, Any], setup=None) -> list[Gozlem]:
    """Tek kaydın plan-gerçek karşılaştırması."""
    out: list[Gozlem] = []
    hedef = _sayi(kayit, "hedef_r")
    sonuc = _sayi(kayit, "sonuc_r")

    if sonuc is None:
        return [Gozlem("sonuç", "pozisyon henüz kapanmadı — inceleme yapılamaz", False)]

    # --- plan vs gerçek ---
    if hedef is None:
        out.append(Gozlem("plan", "hedef R yazılmamış — sapma ölçülemiyor", False))
    elif sonuc >= hedef:
        out.append(Gozlem("plan", f"hedef {hedef:g}R, sonuç {sonuc:+.2f}R — plan tuttu", False))
    elif sonuc > 0 and sonuc < hedef * ERKEN_ORAN:
        pay = 100 * sonuc / hedef
        out.append(Gozlem("plan",
                          f"hedef {hedef:g}R, sonuç {sonuc:+.2f}R — planın %{pay:.0f}'inde "
                          f"kapattın", True))
    elif sonuc > 0:
        out.append(Gozlem("plan", f"hedef {hedef:g}R, sonuç {sonuc:+.2f}R — hedefin altında "
                                  f"ama yakın", False))
    else:
        out.append(Gozlem("plan", f"hedef {hedef:g}R, sonuç {sonuc:+.2f}R", False))

    if sonuc < -ASIRI_KAYIP:
        out.append(Gozlem("stop",
                          f"{abs(sonuc):.2f}R kayıp — 1R'den fazla. stop planlandığı "
                          f"yerde miydi?", True))

    # --- girişte kontrol listesi ---
    if setup is not None:
        isaretli = {str(x).lower() for x in (kayit.get("kontrol") or [])}
        eksik = [m.ad for m in setup.kontrol if m.ad not in isaretli]
        if "kontrol" not in kayit:
            out.append(Gozlem("kontrol", "kontrol listesi hiç cevaplanmamış", True))
        elif eksik:
            out.append(Gozlem("kontrol",
                              f"{len(eksik)}/{len(setup.kontrol)} madde işaretsizdi: "
                              f"{', '.join(eksik)}", True))
        else:
            out.append(Gozlem("kontrol", "girişte tüm maddeler işaretliydi", False))

    # --- çıkış gerekçesi ---
    if not str(kayit.get("cikis_sebebi") or "").strip():
        out.append(Gozlem("çıkış", "çıkış sebebi yazılmamış — neden çıktığın kayıtlı değil",
                          True))

    # --- sonradan eklenmek istenenler ---
    notlar = kayit.get("notlar") or []
    if notlar:
        out.append(Gozlem("sonradan",
                          f"{len(notlar)} işlem sonrası not var — girişte söylemediğin "
                          f"bir şeyi sonradan eklemek istemişsin", True))

    return out


def sapma_sayisi(gozlemler: list[Gozlem]) -> int:
    return sum(1 for g in gozlemler if g.sapma)


def incelenmemis(kayitlar) -> list[dict]:
    """Kapanmış ama çıkış sebebi yazılmamış kayıtlar — inceleme bekleyenler."""
    return [k for k in kayitlar
            if isinstance(k.get("sonuc_r"), (int, float))
            and not isinstance(k.get("sonuc_r"), bool)
            and not str(k.get("cikis_sebebi") or "").strip()]
