"""
Kural dosyası okuyucu ve doğrulayıcı.

Şartname Bölüm 5: kurallar motoru DETERMİNİSTİK KODDUR. Bu dosya LLM'e hiçbir
şey sormaz, `kurallar.yaml`'ı okur ve makine-okunur bir yapıya çevirir.

İki iş yapar:

1. **Okur.** Dosya yoksa ya da bozuksa çökmez — sorunları listeler, elindekiyle
   döner. Kural dosyası bozuk diye Venüs açılmamazlık etmez.
2. **Doğrular.** Dosya elle yazılıyor; sessiz hata en tehlikeli hatadır.
   `gunluk_islem_limt: 2` yazılırsa o kural hiç uygulanmaz ve kimse fark etmez.
   Bu yüzden bilinmeyen anahtar da, tip hatası da, aralık dışı değer de
   raporlanır.

Geçersiz bir değer **düşürülür**, dosyanın geri kalanı ayakta kalır. Yarım bir
kural setiyle çalışmak, geçersiz bir eşikle kontrol yapmaktan güvenlidir.

Önbellek yok: her çağrı dosyayı yeniden okur. Kuralı değiştirmek dosyayı
düzenlemektir (Bölüm 4), yeniden başlatmak değil.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from . import log

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_DOSYA = KOK / "kurallar.yaml"

# `yasak` altına yazılabilecek davranışlar. Buradaki her ad için deterministik
# bir dedektör yazılır; listede olmayan bir yasak hiçbir zaman tespit edilmez.
# Sessizce kabul edilirse kullanıcı korunduğunu sanır — bu yüzden reddedilir.
BILINEN_YASAKLAR = (
    "stop_genisletme",
    "kayip_sonrasi_bekleme_ihlali",
    "plan_disi_giris",
)


@dataclass(frozen=True)
class Sorun:
    """Kural dosyasındaki tek bir aksaklık. `yol` = "trading.min_rr" biçiminde."""
    yol: str
    mesaj: str

    def __str__(self) -> str:
        return f"{self.yol}: {self.mesaj}"


@dataclass(frozen=True)
class Kurallar:
    dosya: Path
    bolumler: dict[str, dict[str, Any]]
    sorunlar: tuple[Sorun, ...]
    okundu: bool          # dosya açılıp ayrıştırılabildi mi

    @property
    def saglam(self) -> bool:
        return self.okundu and not self.sorunlar

    def deger(self, yol: str, varsayilan: Any = None) -> Any:
        """`kurallar.deger("trading.min_rr")`. Tanımsız/geçersiz alan → varsayılan."""
        bolum, _, alan = yol.partition(".")
        return self.bolumler.get(bolum, {}).get(alan, varsayilan)

    def tum(self) -> dict[str, Any]:
        """Geçerli tüm kurallar, "bolum.alan" -> değer olarak düz liste halinde."""
        return {f"{b}.{a}": d
                for b, alanlar in self.bolumler.items()
                for a, d in alanlar.items()}


# ---- doğrulayıcılar ------------------------------------------------------
# Hepsi aynı sözleşme: (değer) -> (temizlenmiş değer | None, sorun mesajları).
# None dönen değer düşürülür.

def _tam_sayi(d: Any, en_az: int) -> tuple[Any, list[str]]:
    """en_az dahil. bool, Python'da int'tir; kural değeri olarak kabul edilmez."""
    if isinstance(d, bool) or not isinstance(d, int):
        return None, ["tam sayı olmalı"]
    if d < en_az:
        return None, [f"en az {en_az} olmalı (bulunan: {d})"]
    return d, []


def _ondalik(d: Any, buyuk: float, en_cok: float | None = None) -> tuple[Any, list[str]]:
    """`buyuk` hariç alt sınır: risk yüzdesi ya da R hedefi sıfır olamaz."""
    if isinstance(d, bool) or not isinstance(d, (int, float)):
        return None, ["sayı olmalı"]
    d = float(d)
    if d <= buyuk:
        return None, [f"{buyuk:g}'den büyük olmalı (bulunan: {d:g})"]
    if en_cok is not None and d > en_cok:
        return None, [f"en fazla {en_cok:g} olabilir (bulunan: {d:g})"]
    return d, []


def _ad_listesi(d: Any, bilinen: tuple[str, ...] | None = None) -> tuple[Any, list[str]]:
    """Adlar küçük harfe indirilir; tek bozuk öğe listenin tamamını düşürmez."""
    if not isinstance(d, (list, tuple)):
        return None, ["liste olmalı"]
    adlar: list[str] = []
    sorunlar: list[str] = []
    for oge in d:
        if not isinstance(oge, str) or not oge.strip():
            sorunlar.append(f"öğe boş olmayan metin olmalı: {oge!r}")
            continue
        ad = oge.strip().lower()
        if bilinen is not None and ad not in bilinen:
            sorunlar.append(f"tanınmayan ad '{ad}' — hiçbir dedektör bunu aramaz "
                            f"(bilinenler: {', '.join(bilinen)})")
            continue
        if ad in adlar:
            sorunlar.append(f"yinelenen öğe: '{ad}'")
            continue
        adlar.append(ad)
    return tuple(adlar), sorunlar


def _saat(d: Any) -> tuple[Any, list[str]]:
    if not isinstance(d, str):
        return None, ['"SS:DD" biçiminde metin olmalı (örn. "09:30")']
    try:
        datetime.strptime(d.strip(), "%H:%M")
    except ValueError:
        return None, [f'"SS:DD" biçiminde olmalı (bulunan: {d!r})']
    return d.strip(), []


# Şema: bölüm -> alan -> doğrulayıcı. Burada olmayan anahtar bilinmeyendir.
SEMA = {
    "trading": {
        "gunluk_islem_limiti":      lambda d: _tam_sayi(d, en_az=0),
        "maks_risk_yuzde":          lambda d: _ondalik(d, buyuk=0, en_cok=100),
        "min_rr":                   lambda d: _ondalik(d, buyuk=0),
        "gunluk_maks_kayip_r":      lambda d: _ondalik(d, buyuk=0),
        "kayip_sonrasi_bekleme_dk": lambda d: _tam_sayi(d, en_az=0),
        "izinli_seanslar":          lambda d: _ad_listesi(d),
        "zorunlu_alanlar":          lambda d: _ad_listesi(d),
        "yasak":                    lambda d: _ad_listesi(d, bilinen=BILINEN_YASAKLAR),
    },
    "calisma": {
        "gunluk_odak_saati":         _saat,
        "gece_calisma_uyarisi_saat": _saat,
    },
}


def _dosya_yolu(dosya: str | Path | None) -> Path:
    if dosya is not None:
        return Path(dosya)
    return Path(os.environ.get("VENUS_KURALLAR", VARSAYILAN_DOSYA))


def yukle(dosya: str | Path | None = None) -> Kurallar:
    yol = _dosya_yolu(dosya)
    sorunlar: list[Sorun] = []

    if not yol.exists():
        return _bitir(yol, {}, [Sorun(yol.name, "kural dosyası bulunamadı")], okundu=False)

    try:
        ham = yaml.safe_load(yol.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as e:
        # yaml'ın hata metni çok satırlıdır; kabukta ve log satırında tek satır olmalı.
        neden = " ".join(str(e).split())
        return _bitir(yol, {}, [Sorun(yol.name, f"okunamadı: {neden}")], okundu=False)

    if ham is None:          # boş dosya: henüz doldurulmamış, hata değil
        ham = {}
    if not isinstance(ham, dict):
        return _bitir(yol, {}, [Sorun(yol.name, "kök seviye anahtar/değer olmalı")],
                      okundu=False)

    for bolum in ham:
        if bolum not in SEMA:
            sorunlar.append(Sorun(str(bolum), "bilinmeyen bölüm"))

    bolumler: dict[str, dict[str, Any]] = {}
    for bolum, alanlar in SEMA.items():
        icerik = ham.get(bolum)
        if icerik is None:   # bölüm yok ya da null: o kurallar tanımsız
            continue
        if not isinstance(icerik, dict):
            sorunlar.append(Sorun(bolum, "anahtar/değer bloğu olmalı"))
            continue

        gecerli: dict[str, Any] = {}
        for alan, deger in icerik.items():
            yol_adi = f"{bolum}.{alan}"
            if alan not in alanlar:
                sorunlar.append(Sorun(yol_adi, "bilinmeyen anahtar — yazım hatası mı?"))
                continue
            if deger is None:   # açıkça boş bırakılmış: kural tanımsız
                continue
            temiz, hatalar = alanlar[alan](deger)
            sorunlar.extend(Sorun(yol_adi, h) for h in hatalar)
            if temiz is not None:
                gecerli[alan] = temiz

        if gecerli:
            bolumler[bolum] = gecerli

    return _bitir(yol, bolumler, sorunlar, okundu=True)


def _bitir(yol: Path, bolumler: dict, sorunlar: list[Sorun], *, okundu: bool) -> Kurallar:
    # Değişmez 7: her şey loglanır. Bozuk kural dosyası ileride "neden ihlal
    # yakalanmadı" sorusunun cevabı olacak, kayda geçmeli.
    log.yaz("kurallar", olay="yuklendi", dosya=str(yol), okundu=okundu,
            kural=sum(len(a) for a in bolumler.values()),
            sorun=[str(s) for s in sorunlar])
    return Kurallar(dosya=yol, bolumler=bolumler,
                    sorunlar=tuple(sorunlar), okundu=okundu)
