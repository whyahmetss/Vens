"""
Niyet çözücü — serbest cümleyi bir yeteneğe eşler.

Şartname Bölüm 15 / CLAUDE.md Faz 3. Modele "ne yapayım" sorulmaz,
**"hangi yeteneği hangi parametreyle çağırayım"** sorulur.

Üç yapısal koruma, üçü de Değişmez 1'in ("model yetenek uydurabilir; sistem
uydurulmuş yeteneği çalıştıramaz") ayrı ayrı uygulanışı:

1. **Ajan döngüsü yok.** Tek çağrı yapılır. Model hiçbir şey çalıştırmaz,
   yalnızca bir araç adı seçer. Sonucu geri beslenmez, ikinci tur yoktur.
2. **Araç listesi kayıt defterinden üretilir**, elle yazılmaz — `/yetenekler`
   ile aynı kaynak. Listede olmayan bir ad dönerse çağrı reddedilir.
3. **Çalıştırma çekirdeğin risk kapısından geçer.** Niyet çözücü yeteneği
   kendisi çağırmaz; router'a komut verir. TURUNCU yetenek yine onay ister.

Model kapalıysa ya da ağ yoksa kabuk deterministik çalışmaya devam eder.
Niyet çözücü bir kolaylıktır, bağımlılık değildir.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass

from . import log
from . import model as model_secimi
from .registry import hepsi

# Araç adı kısıtı: modele verilen ad ^[a-zA-Z0-9_-]{1,64}$ olmalı. Türkçe
# harfli bir yetenek adı eklenirse sessizce düşmesin diye burada ayıklanır.
AD_KALIBI = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

ANLASILMADI = "anlasilmadi"

# Bu görevin modeli core/model.py'deki tabloda; her görev kendi modelini seçer.
GOREV = "niyet"

SISTEM = """Sen VENÜS'ün niyet çözücüsüsün. Tek işin var: kullanıcının cümlesini
verilen yeteneklerden BİRİNE eşlemek.

- Soruyu cevaplama, yorum yapma, tavsiye verme. Yalnızca araç seç.
- İstenen şey listede yoksa, emin değilsen ya da cümle birden fazla iş
  istiyorsa `anlasilmadi` aracını çağır. Yakın bir yetenek uydurma.
- `arg` alanına yeteneğin kullanım biçimine uyan parametreyi yaz. Yetenek
  parametre almıyorsa boş bırak.
- Trading'de yön, giriş/çıkış ya da "al/sat" isteniyorsa `anlasilmadi` çağır.
  Venüs sinyal üretmez."""


@dataclass(frozen=True)
class Niyet:
    yetenek: str | None    # çalıştırılacak yetenek; None ise çalıştırma yok
    arg: str
    hata: str | None       # kullanıcıya gösterilecek sebep
    ham: str | None = None # modelin döndürdüğü ad (reddedilmiş olsa da)

    @property
    def komut(self) -> str:
        return f"{self.yetenek} {self.arg}".strip()


def model() -> str:
    return model_secimi.sec(GOREV)


def acik_mi() -> bool:
    """Anahtar yoksa ya da elle kapatıldıysa niyet çözücü devre dışıdır."""
    if os.environ.get("VENUS_NIYET", "").strip().lower() in ("kapali", "kapalı", "0"):
        return False
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def neden_kapali() -> str:
    if os.environ.get("VENUS_NIYET", "").strip().lower() in ("kapali", "kapalı", "0"):
        return "niyet çözücü kapalı (VENUS_NIYET)"
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return "anthropic paketi kurulu değil (pip install -r requirements.txt)"
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return "ANTHROPIC_API_KEY tanımlı değil"
    return "niyet çözücü kapalı"


def araclar() -> tuple[list[dict], list[str]]:
    """Kayıt defterinden araç tanımı üretir. Elle yazılan ikinci bir liste yok.

    Döner: (araç tanımları, atlanan yetenek adları)
    """
    tanimlar: list[dict] = []
    atlanan: list[str] = []

    for s in hepsi():
        if not AD_KALIBI.match(s.ad):
            atlanan.append(s.ad)
            continue
        aciklama = s.aciklama
        if s.kullanim:
            aciklama += f" — kullanım: {s.kullanim}"
        if s.takma_adlar:
            aciklama += f" (takma ad: {', '.join(s.takma_adlar)})"
        tanimlar.append({
            "name": s.ad,
            "description": aciklama,
            "strict": True,
            "input_schema": {
                "type": "object",
                "properties": {"arg": {
                    "type": "string",
                    "description": "Yeteneğe geçilecek parametre. "
                                   "Yetenek parametre almıyorsa boş metin.",
                }},
                "required": ["arg"],
                "additionalProperties": False,
            },
        })

    # Modelin dürüst çıkışı. Bu araç olmasa, zorunlu araç seçimi altında
    # model en yakın yeteneği seçmeye itilirdi — yani uydurmaya.
    tanimlar.append({
        "name": ANLASILMADI,
        "description": "Cümle hiçbir yeteneğe eşlenemiyorsa, birden fazla iş "
                       "isteniyorsa ya da emin değilsen bunu çağır.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"sebep": {
                "type": "string",
                "description": "Tek cümle, Türkçe: neden eşlenemedi.",
            }},
            "required": ["sebep"],
            "additionalProperties": False,
        },
    })
    return tanimlar, atlanan


async def coz(cumle: str) -> Niyet:
    """Cümleyi tek bir yetenek çağrısına çevirir. Hiçbir şey çalıştırmaz."""
    cumle = cumle.strip()
    if not cumle:
        return Niyet(None, "", "boş girdi")
    if not acik_mi():
        return Niyet(None, "", neden_kapali())

    import anthropic

    tanimlar, atlanan = araclar()
    if atlanan:
        log.yaz("niyet", olay="arac_atlandi", yetenek=atlanan)

    t0 = time.perf_counter()
    try:
        istemci = anthropic.AsyncAnthropic()
        yanit = await istemci.messages.create(
            model=model(),
            max_tokens=2048,
            system=SISTEM,
            # Araç listesi ve sistem metni sabittir; yetenek sayısı büyüdükçe
            # önbelleğe girer. Kısa listede sessizce devre dışı kalır.
            cache_control={"type": "ephemeral"},
            # Yönlendirme basit bir iştir; düşük efor gecikmeyi de düşürür.
            output_config={"effort": "low"},
            tools=tanimlar,
            # Model mutlaka bir araç seçmeli ve tek araç seçmeli: serbest
            # metinle cevap verme yolu kapalı. Dürüst çıkışı `anlasilmadi`.
            tool_choice={"type": "any", "disable_parallel_tool_use": True},
            messages=[{"role": "user", "content": cumle}],
        )
    except anthropic.APIStatusError as e:
        log.yaz("niyet", olay="hata", girdi=cumle, kod=e.status_code, hata=str(e.message))
        return Niyet(None, "", f"model hatası ({e.status_code})")
    except anthropic.APIConnectionError:
        log.yaz("niyet", olay="hata", girdi=cumle, hata="baglanti")
        return Niyet(None, "", "modele ulaşılamadı — ağ yok mu?")
    except Exception as e:                     # kabuk asla çökmemeli
        log.yaz("niyet", olay="hata", girdi=cumle, hata=repr(e))
        return Niyet(None, "", f"niyet çözülemedi: {e}")

    ms = int((time.perf_counter() - t0) * 1000)
    secim = next((b for b in yanit.content if b.type == "tool_use"), None)

    if secim is None:
        # tool_choice="any" altında olmaması gerekir; yine de güvenle karşıla.
        log.yaz("niyet", olay="arac_yok", girdi=cumle, ms=ms,
                durma=yanit.stop_reason)
        return Niyet(None, "", "model bir yetenek seçmedi")

    from .registry import bul   # döngüsel içe aktarmayı önlemek için burada

    if secim.name == ANLASILMADI:
        sebep = str(secim.input.get("sebep", "")).strip() or "eşleşen yetenek yok"
        log.yaz("niyet", olay="anlasilmadi", girdi=cumle, ms=ms, sebep=sebep,
                **_kullanim(yanit))
        return Niyet(None, "", sebep, ham=ANLASILMADI)

    # Değişmez 1: listede olmayan ad çalıştırılmaz. Kayıt defteri tek doğruluk
    # kaynağıdır — modelin ne döndürdüğü değil, defterde ne olduğu belirler.
    if bul(secim.name) is None:
        log.yaz("niyet", olay="reddedildi", girdi=cumle, ms=ms, ad=secim.name,
                **_kullanim(yanit))
        return Niyet(None, "", f"model kayıtlı olmayan bir yetenek döndürdü: "
                               f"{secim.name}", ham=secim.name)

    arg = str(secim.input.get("arg", "")).strip()
    log.yaz("niyet", olay="cozuldu", girdi=cumle, ms=ms, yetenek=secim.name,
            arg=arg, model=model(), **_kullanim(yanit))
    return Niyet(secim.name, arg, None, ham=secim.name)


def _kullanim(yanit) -> dict:
    """Jeton sayıları loga girer: maliyet zamanla ölçülebilir olmalı."""
    k = getattr(yanit, "usage", None)
    if k is None:
        return {}
    return {"girdi_jeton": getattr(k, "input_tokens", None),
            "cikti_jeton": getattr(k, "output_tokens", None)}
