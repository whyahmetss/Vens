"""
Bilgisayar kontrolü — beyaz listeli.

Şartname Bölüm 9: sistemin **en riskli** bölümü. Bu yüzden fazlarda en sonda
ve bu yüzden kapsamı dar.

**Yapabildikleri:** guard/beyazliste.yaml'da KAYITLI bir uygulamayı açmak,
KAYITLI bir sayfayı açmak, kayıtlılardan oluşan bir düzeni kurmak.

**Yapamadıkları:** serbest terminal komutu, klavye/mouse simülasyonu, dosya
silme/taşıma, uygulama kapatma. Bunlar v1 kapsamı dışıdır ve buraya
eklenmemelidir.

Komut listeden gelir, kullanıcıdan ya da modelden değil. Model olmayan bir
ad uydurursa listede bulunamaz ve hiçbir şey çalışmaz (Değişmez 1).
Komutlar `shell=False` ile, liste hâlinde çalıştırılır — düz metin komut
kabul edilmez, çünkü kabuk onu ayrıştırır ve araya komut sıkıştırılabilir.
"""

import os
import subprocess
import webbrowser
from pathlib import Path

import yaml

from core.registry import Risk, Perm, skill, bilgi, uyari, alan, baslik, bosluk
from core import log

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN = KOK / "guard" / "beyazliste.yaml"


def _dosya() -> Path:
    return Path(os.environ.get("VENUS_BEYAZLISTE", VARSAYILAN))


def yukle() -> tuple[dict, list[str]]:
    """Beyaz listeyi okur ve doğrular. Döner: (liste, sorunlar)."""
    yol = _dosya()
    if not yol.exists():
        return {}, [f"beyaz liste yok: {yol}"]
    try:
        ham = yaml.safe_load(yol.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as e:
        return {}, [f"okunamadı: {' '.join(str(e).split())}"]
    if not isinstance(ham, dict):
        return {}, ["kök seviye anahtar/değer olmalı"]

    sorunlar: list[str] = []
    temiz = {"uygulamalar": {}, "sayfalar": {}, "duzenler": {}}

    for ad, giris in (ham.get("uygulamalar") or {}).items():
        komut = (giris or {}).get("komut") if isinstance(giris, dict) else None
        # Düz metin komut REDDEDİLİR: kabuk onu ayrıştırır, araya komut girer.
        if not isinstance(komut, (list, tuple)) or not komut:
            sorunlar.append(f"uygulamalar.{ad}: 'komut' boş olmayan liste olmalı")
            continue
        if not all(isinstance(p, str) for p in komut):
            sorunlar.append(f"uygulamalar.{ad}: komut öğeleri metin olmalı")
            continue
        temiz["uygulamalar"][str(ad)] = {
            "komut": [str(p) for p in komut],
            "aciklama": str((giris or {}).get("aciklama", "")),
        }

    for ad, url in (ham.get("sayfalar") or {}).items():
        u = str(url or "")
        if not u.startswith(("http://", "https://")):
            sorunlar.append(f"sayfalar.{ad}: yalnızca http/https (bulunan: {u!r})")
            continue
        temiz["sayfalar"][str(ad)] = u

    for ad, giris in (ham.get("duzenler") or {}).items():
        adimlar = (giris or {}).get("adimlar") if isinstance(giris, dict) else None
        if not isinstance(adimlar, (list, tuple)) or not adimlar:
            sorunlar.append(f"duzenler.{ad}: 'adimlar' boş olmayan liste olmalı")
            continue
        gecerli = []
        for a in adimlar:
            if not isinstance(a, dict) or len(a) != 1:
                sorunlar.append(f"duzenler.{ad}: her adım tek anahtar olmalı")
                continue
            tur, hedef = next(iter(a.items()))
            if tur not in ("uygulama", "sayfa"):
                sorunlar.append(f"duzenler.{ad}: bilinmeyen adım türü '{tur}'")
                continue
            havuz = temiz["uygulamalar"] if tur == "uygulama" else temiz["sayfalar"]
            if str(hedef) not in havuz:
                sorunlar.append(f"duzenler.{ad}: '{hedef}' beyaz listede yok")
                continue
            gecerli.append((tur, str(hedef)))
        if gecerli:
            temiz["duzenler"][str(ad)] = {
                "adimlar": gecerli,
                "aciklama": str((giris or {}).get("aciklama", "")),
            }
    return temiz, sorunlar


def _uygulama_ac(ad: str, giris: dict) -> str:
    subprocess.Popen(giris["komut"], shell=False,          # shell=False: Değişmez 1
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log.yaz("bilgisayar", olay="uygulama", ad=ad, komut=giris["komut"])
    return f"uygulama açıldı: {ad}"


def _sayfa_ac(ad: str, url: str) -> str:
    webbrowser.open(url)
    log.yaz("bilgisayar", olay="sayfa", ad=ad, url=url)
    return f"sayfa açıldı: {ad}"


@skill("beyazliste", "açılabilecek uygulama, sayfa ve düzenler", Risk.YESIL,
       izinler=(Perm.OKUMA,), kullanim="beyazliste")
async def _beyazliste(arg):
    liste, sorunlar = yukle()
    out = []
    for bolum, baslikad in (("uygulamalar", "uygulama"), ("sayfalar", "sayfa"),
                            ("duzenler", "düzen")):
        girisler = liste.get(bolum) or {}
        if not girisler:
            continue
        out.append(baslik(baslikad))
        for ad, g in girisler.items():
            if bolum == "sayfalar":
                out.append(alan(ad, g))
            elif bolum == "uygulamalar":
                out.append(alan(ad, g["aciklama"] or " ".join(g["komut"])[:60]))
            else:
                out.append(alan(ad, f"{len(g['adimlar'])} adım"
                                    + (f"   {g['aciklama']}" if g["aciklama"] else "")))
        out.append(bosluk())

    if not any(liste.get(b) for b in ("uygulamalar", "sayfalar", "duzenler")):
        out.append(bilgi("beyaz liste boş — Venüs hiçbir şey açamaz."))
        out.append(bilgi(f"doldurmak için: {_dosya()}"))
    if sorunlar:
        out.append(baslik(f"{len(sorunlar)} sorun — bu girişler yok sayılıyor"))
        out += [uyari(f"  {s}") for s in sorunlar]
    return out


@skill("ac", "kayıtlı uygulama ya da sayfa aç", Risk.SARI,
       izinler=(Perm.CALISTIRMA, Perm.TARAYICI), kullanim="ac <ad>")
async def _ac(arg):
    ad = arg.strip()
    if not ad:
        return [uyari("kullanım: ac <ad>"), bilgi("listeyi görmek için: beyazliste")]
    liste, _ = yukle()

    if ad in (liste.get("uygulamalar") or {}):
        try:
            return [bilgi(_uygulama_ac(ad, liste["uygulamalar"][ad]))]
        except (OSError, ValueError) as e:
            return [uyari(f"açılamadı: {e}")]
    if ad in (liste.get("sayfalar") or {}):
        try:
            return [bilgi(_sayfa_ac(ad, liste["sayfalar"][ad]))]
        except Exception as e:
            return [uyari(f"açılamadı: {e}")]

    # Değişmez 1: listede yoksa çalışmaz. Yaklaştırma da yapılmaz.
    log.yaz("bilgisayar", olay="reddedildi", ad=ad)
    return [uyari(f"beyaz listede yok: {ad}"),
            bilgi("Venüs yalnızca guard/beyazliste.yaml'da yazanı açar.")]


@skill("duzen", "kayıtlı çalışma alanı düzenini kur", Risk.SARI,
       izinler=(Perm.CALISTIRMA, Perm.TARAYICI), kullanim="duzen <ad>")
async def _duzen(arg):
    ad = arg.strip()
    liste, _ = yukle()
    duzenler = liste.get("duzenler") or {}

    if not ad:
        if not duzenler:
            return [bilgi("tanımlı düzen yok."), bilgi(f"tanımlamak için: {_dosya()}")]
        return [baslik("düzenler")] + [
            alan(a, g["aciklama"] or f"{len(g['adimlar'])} adım") for a, g in duzenler.items()]

    if ad not in duzenler:
        log.yaz("bilgisayar", olay="reddedildi", duzen=ad)
        return [uyari(f"düzen bulunamadı: {ad}")]

    out = [bilgi(f"düzen kuruluyor: {ad}")]
    for tur, hedef in duzenler[ad]["adimlar"]:
        try:
            if tur == "uygulama":
                out.append(bilgi("  " + _uygulama_ac(hedef, liste["uygulamalar"][hedef])))
            else:
                out.append(bilgi("  " + _sayfa_ac(hedef, liste["sayfalar"][hedef])))
        except Exception as e:
            # Bir adım düşerse düzenin kalanı kurulmaya devam eder.
            out.append(uyari(f"  {hedef} açılamadı: {e}"))
    log.yaz("bilgisayar", olay="duzen", ad=ad, adim=len(duzenler[ad]["adimlar"]))
    return out
