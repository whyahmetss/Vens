"""
Bildirim seviyeleri ve günlük bütçe.

Şartname Bölüm 12. Venüs komut beklemeden konuşabilir — ama bir bütçesi
vardır. Bölümün kendi uyarısı: **bütçe aşılırsa kullanıcı sistemi susturur
ve proje ölür.** Bu yüzden bütçe bir öneri değil, kodda uygulanan sınırdır.

| seviye | ne zaman              | nasıl                  |
|--------|-----------------------|------------------------|
| KRİTİK | kural ihlali, sorun   | kesintili (+ses: Faz 4)|
| YÜKSEK | killzone, toplantı    | görsel (+ses: Faz 4)   |
| NORMAL | jurnal eksik          | sessiz rozet           |
| DÜŞÜK  | bilgi                 | sadece log             |

Bütçe yalnızca **kesintili** olanlara işler (KRİTİK + YÜKSEK, günde 3).
Kullanıcının kendi komutuna verilen cevap kesinti değildir — ihlal uyarısı
`jurnal` çıktısında zaten görünür, bütçeden düşmez. Sayılan şey, kullanıcı
bir şey sormadan ekranı bölen bildirimdir.

Ses Faz 4'te. Seviyeler şimdiden ayrıldı çünkü sonradan ayırmak, her çağrı
yerini tek tek gözden geçirmek demektir.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import date, datetime
from enum import Enum

from . import kanal, log
from .log import VERI

BILDIRIMLER = VERI / "bildirimler.jsonl"


class Seviye(str, Enum):
    KRITIK = "kritik"
    YUKSEK = "yuksek"
    NORMAL = "normal"
    DUSUK = "dusuk"


# Ekranı bölme hakkı olan seviyeler. Bütçe bunlara işler.
KESINTILI = (Seviye.KRITIK, Seviye.YUKSEK)
GUNLUK_BUTCE = 3


@dataclass(frozen=True)
class Bildirim:
    t: str
    seviye: str
    metin: str
    kaynak: str
    durum: str        # iletildi | kuyrukta | kayitli

    @property
    def saat(self) -> str:
        return self.t[11:16]

    @property
    def bekliyor(self) -> bool:
        return self.durum in ("kuyrukta", "kayitli")


def bildir(seviye: Seviye, metin: str, kaynak: str,
           kesintisiz: bool = False) -> Bildirim:
    """Bildirimi kaydeder ve gerekiyorsa iletir.

    `kesintisiz=True`: bildirim kullanıcının kendi komutunun çıktısında zaten
    görünüyor. Kayda geçer ama ekranı bölmez ve bütçeden düşmez.
    """
    simdi = datetime.now().isoformat(timespec="microseconds")

    if seviye is Seviye.DUSUK:
        durum = "log"                         # Bölüm 12: sadece log, rozet bile değil
    elif kesintisiz or seviye is Seviye.NORMAL:
        durum = "kayitli"                     # rozet; kendiliğinden bölmez
    elif not kanal.acik():
        # Açık kabuk yok: kimse bölünmedi. Bütçeyi burada harcamak, kullanıcı
        # ekrana geldiğinde hakkını yemek olurdu — kuyruğa alınır, rozette durur.
        durum = "kuyrukta"
    elif bugun_iletilen() >= GUNLUK_BUTCE:
        durum = "kuyrukta"                    # bütçe doldu (Bölüm 12)
    else:
        durum = "iletildi"

    b = Bildirim(t=simdi, seviye=seviye.value, metin=metin,
                 kaynak=kaynak, durum=durum)
    _yaz(b)
    log.yaz("bildirim", seviye=b.seviye, kaynak=kaynak, durum=durum, metin=metin)

    # Kabuk "log" dışında her şeyi görür. Ekranı bölmek mi rozeti artırmak mı
    # gerektiğine köprü `durum`a bakarak karar verir.
    if durum != "log":
        kanal.yayinla({"bildirim": True, "seviye": b.seviye, "durum": b.durum,
                       "saat": b.saat, "text": b.metin})
    return b


def bugun_iletilen(gun: date | None = None) -> int:
    """Bugün ekranı bölmüş kesintili bildirim sayısı.

    Dosyadan okunur, bellekten değil: Venüs'ü yeniden başlatmak bütçeyi
    sıfırlamamalı — yoksa sınır kendiliğinden delinir.
    """
    ek = (gun or date.today()).isoformat()
    return sum(1 for b in hepsi()
               if b.durum == "iletildi"
               and b.seviye in (s.value for s in KESINTILI)
               and b.t.startswith(ek))


ISARET = "okundu_isareti"


def bekleyenler() -> list[Bildirim]:
    """Görülmemişler: kuyruğa alınanlar ve rozet olarak duranlar."""
    sinir = _son_okuma()
    return [b for b in hepsi() if b.bekliyor and b.t > sinir]


def hepsi() -> list[Bildirim]:
    """Gerçek bildirimler. Okundu işaretleri iç kayıttır, listeye girmez."""
    return [b for b in _tum_satirlar() if b.durum != ISARET]


def okundu() -> int:
    """Bekleyenleri okunmuş sayar.

    Depo append-only — eski satırların durumu değiştirilemez. Bu yüzden
    silme ya da güncelleme yerine bir sınır damgası yazılır: bu damgadan
    eski bekleyenler artık bekleyen sayılmaz.
    """
    bekleyen = bekleyenler()
    if not bekleyen:
        return 0
    _yaz(Bildirim(t=datetime.now().isoformat(timespec="microseconds"),
                  seviye=Seviye.DUSUK.value, metin=f"{len(bekleyen)} bildirim okundu",
                  kaynak="okundu", durum=ISARET))
    return len(bekleyen)


def _son_okuma() -> str:
    damgalar = [b.t for b in _tum_satirlar() if b.durum == ISARET]
    return max(damgalar) if damgalar else ""


def _tum_satirlar() -> list[Bildirim]:
    if not BILDIRIMLER.exists():
        return []
    out = []
    with BILDIRIMLER.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(Bildirim(**json.loads(line)))
            except (json.JSONDecodeError, TypeError):
                continue
    return out


def _yaz(b: Bildirim) -> None:
    with BILDIRIMLER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(b), ensure_ascii=False) + "\n")
