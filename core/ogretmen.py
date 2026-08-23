"""
Kart üretici — modelin öğrenme sistemindeki TEK işi.

Sınır bilinçlidir ve dardır:

    Model kart ÜRETİR. Kartı değerlendirmez, ne zaman soracağına karar
    vermez, ilerlemeni yorumlamaz.

Ürettiği her kart cevabıyla birlikte saklanır. Böylece o kart bundan sonra
her karşına çıktığında değerlendirme core/ogrenme.py'nin deterministik
karşılaştırmasıyla yapılır — model bir daha devreye girmez. "Bence yakın
sayılır" diyebilen bir sistem, öğrenip öğrenmediğini ölçemez.

Model kapalıysa (anahtar yok, ağ yok) kart elle eklenmeye devam eder.
Öğrenme motoru modele bağımlı değildir; model yalnızca kart yazma işini
hızlandırır.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from . import log
from . import model as model_secimi

GOREV = "ogretmen"
EN_COK = 20

SISTEM = """Sen bir çalışma kartı üreticisisin. Aktif hatırlama (active recall)
için kart yazıyorsun.

Kurallar:
- Her kartın cevabı KISA ve KESİN olmalı. Deterministik olarak karşılaştırılacak;
  "duruma göre değişir" tipi cevap işe yaramaz.
- Kabul edilebilir birden fazla cevap varsa | ile ayır: "went|gitti"
- Soru tek bir şeyi sormalı. İki şey soran kart, yanlış cevabın hangisinden
  geldiğini gizler.
- Tanım ezberi değil, kullanım sor. "FVG nedir" yerine "Şu üç mumda FVG hangi
  aralıkta oluşur" tipi sorular daha iyidir — ama cevap yine kesin olmalı.
- Var olan kartları TEKRARLAMA.
- Açıklama, giriş cümlesi, öneri yazma. Yalnızca kartları üret."""


@dataclass(frozen=True)
class Uretim:
    kartlar: tuple[tuple[str, str], ...]   # (soru, cevap)
    hata: str | None = None


def _elle_kapali() -> bool:
    # Kendi anahtarı var: niyet çözücüyü kapatmak kart üretimini kapatmaz.
    return os.environ.get("VENUS_OGRETMEN", "").strip().lower() in ("kapali", "kapalı", "0")


def acik_mi() -> bool:
    return not _elle_kapali() and model_secimi.hazir()[0]


def neden_kapali() -> str:
    if _elle_kapali():
        return "kart üretici kapalı (VENUS_OGRETMEN)"
    return model_secimi.hazir()[1] or "kart üretici kapalı"


def model() -> str:
    return model_secimi.sec(GOREV)


ARAC = {
    "name": "kartlar",
    "description": "Üretilen çalışma kartları.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "kartlar": {
                "type": "array",
                "description": "Kart listesi.",
                "items": {
                    "type": "object",
                    "properties": {
                        "soru": {"type": "string", "description": "Tek bir şey soran soru."},
                        "cevap": {"type": "string",
                                  "description": "Kısa ve kesin cevap. "
                                                 "Alternatifler | ile ayrılır."},
                    },
                    "required": ["soru", "cevap"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["kartlar"],
        "additionalProperties": False,
    },
}


async def uret(hedef_baslik: str, unite: str, adet: int,
               mevcut: list[str], dil_notu: str = "") -> Uretim:
    """Bir ünite için kart üretir. Hiçbir şey kaydetmez — çağıran kaydeder."""
    if not acik_mi():
        return Uretim((), neden_kapali())
    adet = max(1, min(EN_COK, adet))

    import anthropic

    istek = [f"Hedef: {hedef_baslik}", f"Ünite: {unite}", f"Adet: {adet} kart"]
    if dil_notu:
        istek.append(dil_notu)
    if mevcut:
        istek.append("Zaten var olan kartlar (tekrarlama):\n" +
                     "\n".join(f"- {s}" for s in mevcut[:40]))

    t0 = time.perf_counter()
    try:
        istemci = anthropic.AsyncAnthropic()
        yanit = await istemci.messages.create(
            model=model(),
            max_tokens=4096,
            system=SISTEM,
            tools=[ARAC],
            # Model serbest metinle cevap veremez: yalnızca kart üretir.
            tool_choice={"type": "tool", "name": "kartlar"},
            messages=[{"role": "user", "content": "\n\n".join(istek)}],
        )
    except anthropic.APIStatusError as e:
        log.yaz("ogretmen", olay="hata", kod=e.status_code, hata=str(e.message))
        return Uretim((), f"model hatası ({e.status_code})")
    except anthropic.APIConnectionError:
        log.yaz("ogretmen", olay="hata", hata="baglanti")
        return Uretim((), "modele ulaşılamadı — ağ yok mu?")
    except Exception as e:
        log.yaz("ogretmen", olay="hata", hata=repr(e))
        return Uretim((), f"kart üretilemedi: {e}")

    ms = int((time.perf_counter() - t0) * 1000)
    blok = next((b for b in yanit.content if b.type == "tool_use"), None)
    if blok is None:
        return Uretim((), "model kart üretmedi")

    ham = blok.input.get("kartlar") or []
    kartlar: list[tuple[str, str]] = []
    for k in ham:
        soru = str(k.get("soru", "")).strip()
        cevap = str(k.get("cevap", "")).strip()
        # Boş soru ya da boş cevap kabul edilmez: cevabı olmayan üretilmiş
        # kart, deterministik değerlendirmeyi imkânsız kılar.
        if soru and cevap and soru not in mevcut:
            kartlar.append((soru, cevap))

    k = getattr(yanit, "usage", None)
    log.yaz("ogretmen", olay="uretildi", unite=unite, istenen=adet,
            uretilen=len(kartlar), ms=ms, model=model(),
            girdi_jeton=getattr(k, "input_tokens", None),
            cikti_jeton=getattr(k, "output_tokens", None))
    return Uretim(tuple(kartlar))
