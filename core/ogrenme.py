"""
Öğrenme motoru — aralıklı tekrar ve aktif hatırlama.

Bu dosya sistemin "ciddi" olmasını sağlayan yer. Bir dil modeline soru
sordurup cevabını yine ona değerlendirtmek öğretmek değildir; kendi ödevini
kendi notlandıran bir şey öğrenip öğrenmediğini ölçemez.

Burada üç şey deterministiktir ve hiçbiri modele sorulmaz:

1. **Ne zaman tekrar edileceği.** SM-2 algoritması. Bildiğin kart uzaklaşır,
   bilemediğin yarın geri gelir. Unutma eğrisine göre planlama, öğrenmede
   kanıtı en sağlam tekniktir ve tamamen aritmetiktir.

2. **Doğru olup olmadığı.** Cevap anahtarı kartta saklıdır. Karşılaştırma
   metin normalizasyonuyla yapılır. Model "bence yakın sayılır" diyemez.

3. **Ne kadar bildiğin.** İlerleme "kaç ders izledin" değil, kaç kartın
   OLGUN olduğu (tekrar aralığı OLGUNLUK_GUN'ü aşmış). İzlemek öğrenmek
   değildir.

Modelin işi yalnızca kart ÜRETMEK — ve ürettiği kart da cevabıyla birlikte
saklanır, yani sonraki değerlendirmeler yine deterministik kalır.
"""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from .log import VERI

KARTLAR = VERI / "kartlar.jsonl"
# Çalışma oturumunda ekranda duran kart. Kabuk istek-cevap olduğu için
# "hangi soruyu sordum" bilgisi bir yerde durmak zorunda.
ACIK = VERI / "acik_kart.json"

# SM-2 sabitleri
BASLANGIC_KOLAYLIK = 2.5
EN_DUSUK_KOLAYLIK = 1.3
# Bu aralığa ulaşan kart "olgun" sayılır: artık hatırlıyorsun demektir.
OLGUNLUK_GUN = 21

# Kullanıcının verebileceği cevaplar → SM-2 kalite notu (0-5)
NOTLAR = {
    "bilemedim": 0,
    "zor": 3,
    "bildim": 4,
    "kolay": 5,
}


@dataclass(frozen=True)
class Kart:
    id: str
    hedef: str
    soru: str
    cevap: str
    unite: str = ""
    kaynak: str = "elle"          # elle | model
    aralik: int = 0               # gün
    kolaylik: float = BASLANGIC_KOLAYLIK
    tekrar: int = 0
    sonraki: str = ""             # YYYY-MM-DD
    gecmis: tuple = ()            # (tarih, not) çiftleri

    @property
    def olgun(self) -> bool:
        return self.aralik >= OLGUNLUK_GUN

    @property
    def yeni(self) -> bool:
        return self.tekrar == 0

    @property
    def basari(self) -> float:
        if not self.gecmis:
            return 0.0
        dogru = sum(1 for _, n in self.gecmis if n >= 3)
        return 100 * dogru / len(self.gecmis)

    def gunu_geldi(self, bugun: date | None = None) -> bool:
        if not self.sonraki:
            return True
        return self.sonraki <= (bugun or date.today()).isoformat()


def sm2(kart: Kart, kalite: int) -> tuple[int, float, int]:
    """SM-2. Döner: (yeni aralık, yeni kolaylık, yeni tekrar sayısı).

    Kalite 3'ün altındaysa kart sıfırlanır — yarın tekrar karşına çıkar.
    Bu, "yanlış bildiğin şeyi unutmadan düzeltmek" ilkesidir.
    """
    kolaylik = kart.kolaylik + (0.1 - (5 - kalite) * (0.08 + (5 - kalite) * 0.02))
    kolaylik = max(EN_DUSUK_KOLAYLIK, round(kolaylik, 3))

    if kalite < 3:
        return 1, kolaylik, 0

    tekrar = kart.tekrar + 1
    if tekrar == 1:
        aralik = 1
    elif tekrar == 2:
        aralik = 6
    else:
        aralik = max(1, round(kart.aralik * kolaylik))
    return aralik, kolaylik, tekrar


# ---- normalizasyon ve karşılaştırma -------------------------------------

def _sade(t: str) -> str:
    """Karşılaştırma için sadeleştirme. Büyük/küçük harf, aksan, noktalama
    ve fazla boşluk cevabın doğruluğunu değiştirmez."""
    t = (t or "").lower().replace("ı", "i").replace("İ", "i")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def denetle(kart: Kart, cevap: str) -> bool | None:
    """Cevap doğru mu? Kartın cevap anahtarı boşsa None döner —
    o zaman kullanıcı kendi kendini notlandırır (açık uçlu kart)."""
    if not kart.cevap.strip():
        return None
    # Birden fazla kabul edilebilir cevap `|` ile ayrılır.
    kabul = [_sade(p) for p in kart.cevap.split("|") if p.strip()]
    return _sade(cevap) in kabul


# ---- depo ----------------------------------------------------------------

def _satirlar() -> list[dict]:
    if not KARTLAR.exists():
        return []
    out = []
    with KARTLAR.open(encoding="utf-8") as f:
        for s in f:
            s = s.strip()
            if s:
                try:
                    out.append(json.loads(s))
                except json.JSONDecodeError:
                    continue
    return out


def _yaz(kayit: dict) -> None:
    with KARTLAR.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def hepsi() -> list[Kart]:
    """Kartların güncel hâli. Tekrar satırları taban kartın üstüne uygulanır."""
    taban: dict[str, dict] = {}
    sira: list[str] = []
    silinen: set[str] = set()

    for k in _satirlar():
        if "sil" in k:
            silinen.add(k["sil"])
        elif "tekrar_et" in k:
            hedef = taban.get(k["tekrar_et"])
            if hedef is not None:
                hedef.update({"aralik": k["aralik"], "kolaylik": k["kolaylik"],
                              "tekrar": k["tekrar"], "sonraki": k["sonraki"]})
                hedef.setdefault("gecmis", []).append([k["t"][:10], k["not"]])
        elif "id" in k:
            taban[k["id"]] = dict(k)
            sira.append(k["id"])

    out = []
    for i in sira:
        if i in silinen:
            continue
        d = taban[i]
        out.append(Kart(id=d["id"], hedef=d.get("hedef", ""), soru=d.get("soru", ""),
                        cevap=d.get("cevap", ""), unite=d.get("unite", ""),
                        kaynak=d.get("kaynak", "elle"), aralik=d.get("aralik", 0),
                        kolaylik=d.get("kolaylik", BASLANGIC_KOLAYLIK),
                        tekrar=d.get("tekrar", 0), sonraki=d.get("sonraki", ""),
                        gecmis=tuple(tuple(g) for g in d.get("gecmis", []))))
    return out


def ekle(hedef: str, soru: str, cevap: str, unite: str = "",
         kaynak: str = "elle") -> Kart:
    kayit = {"id": uuid.uuid4().hex[:4], "hedef": hedef, "soru": soru,
             "cevap": cevap, "unite": unite, "kaynak": kaynak,
             "t": datetime.now().isoformat(timespec="seconds")}
    _yaz(kayit)
    return next(k for k in hepsi() if k.id == kayit["id"])


def sil(kimlik: str) -> bool:
    if not any(k.id == kimlik for k in hepsi()):
        return False
    _yaz({"sil": kimlik, "t": datetime.now().isoformat(timespec="seconds")})
    return True


def isaretle(kart: Kart, kalite: int) -> Kart:
    """Kartı notlandırır ve bir sonraki tekrar tarihini hesaplar."""
    aralik, kolaylik, tekrar = sm2(kart, kalite)
    sonraki = (date.today() + timedelta(days=aralik)).isoformat()
    _yaz({"tekrar_et": kart.id, "aralik": aralik, "kolaylik": kolaylik,
          "tekrar": tekrar, "sonraki": sonraki, "not": kalite,
          "t": datetime.now().isoformat(timespec="seconds")})
    return next(k for k in hepsi() if k.id == kart.id)


def gunun_kartlari(hedef: str = "", bugun: date | None = None) -> list[Kart]:
    """Bugün çalışılması gerekenler. Bilemediklerin önce gelir."""
    kartlar = [k for k in hepsi() if k.gunu_geldi(bugun)
               and (not hedef or k.hedef == hedef)]
    # Sıralama: geciken > yeni > diğerleri. Zayıf noktaya önce dönülür.
    kartlar.sort(key=lambda k: (k.basari if k.gecmis else 50, k.sonraki or ""))
    return kartlar


def ozet(hedef: str = "") -> dict[str, Any]:
    kartlar = [k for k in hepsi() if not hedef or k.hedef == hedef]
    return {
        "toplam": len(kartlar),
        "yeni": sum(1 for k in kartlar if k.yeni),
        "olgun": sum(1 for k in kartlar if k.olgun),
        "bugun": len(gunun_kartlari(hedef)),
        "zayif": sorted((k for k in kartlar if k.gecmis and k.basari < 60),
                        key=lambda k: k.basari)[:5],
    }


# ---- açık kart (çalışma oturumu durumu) ---------------------------------

def acik_kart() -> tuple[Kart | None, bool, str]:
    """Ekranda duran kart, cevabın açılıp açılmadığı ve OTURUMUN hedef filtresi.

    Filtre saklanmak zorunda: `calis` filtresiz başlatıldıysa oturum tüm
    hedefler üzerinden sürmeli. Kartın kendi hedefine bakmak, ilk cevaptan
    sonra oturumu sessizce daraltırdı.
    """
    if not ACIK.exists():
        return None, False, ""
    try:
        d = json.loads(ACIK.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, False, ""
    kart = next((k for k in hepsi() if k.id == d.get("kart")), None)
    return kart, bool(d.get("acildi")), d.get("hedef", "")


def kart_ac(kart: Kart, hedef: str = "") -> None:
    ACIK.write_text(json.dumps({"kart": kart.id, "acildi": False, "hedef": hedef,
                                "t": datetime.now().isoformat(timespec="seconds")},
                               ensure_ascii=False), encoding="utf-8")


def cevabi_ac() -> None:
    if ACIK.exists():
        try:
            d = json.loads(ACIK.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        d["acildi"] = True
        ACIK.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def karti_kapat() -> None:
    ACIK.unlink(missing_ok=True)
