"""
Kullanıcının kendi piyasa notları: seviyeler ve HTF bias.

Şartname Bölüm 6 ve Değişmez 4 burada özellikle önemli: **Venüs seviye
belirlemez, bias üretmez.** İkisini de kullanıcı yazar; Venüs saklar,
hatırlatır ve gösterir.

Seviye yaklaşma uyarısı bir sinyal değildir. "Fiyat senin işaretlediğin
yere yaklaştı" der ve susar — ne yön, ne giriş, ne "fırsat".

HTF bias için de aynısı: modele "bias ne olmalı" sorulmaz. Bu dosya
kullanıcının kendi tezini kaydeder. Modelin ürettiği bir bias, logdan
kullanıcının kendi tezinden ayırt edilemez (Bölüm 10) — kaybedilen şey
paradan önce yargı olur.
"""

import json
import uuid
from datetime import date, datetime

from core.registry import Risk, Perm, skill, satir, bilgi, uyari, alan, baslik, bosluk
from core.bildirim import Seviye, bildir, hepsi as bildirim_hepsi
from core.log import VERI
from core.zamanlayici import periyodik
from skills.piyasa import BorsaHatasi, getir

SEVIYELER = VERI / "seviyeler.jsonl"
BIAS = VERI / "bias.jsonl"

# Fiyat seviyeye bu kadar yaklaşınca haber verilir. Sabit; kullanıcı
# istediği hassasiyeti seviyeyi taşıyarak ayarlar.
YAKINLIK_YUZDE = 0.25

YONLER = {"long": "long", "yukari": "long", "yukarı": "long", "boga": "long", "boğa": "long",
          "short": "short", "asagi": "short", "aşağı": "short", "ayi": "short", "ayı": "short",
          "notr": "nötr", "nötr": "nötr", "yok": "nötr", "belirsiz": "nötr"}


def _oku(yol):
    if not yol.exists():
        return []
    out = []
    with yol.open(encoding="utf-8") as f:
        for satir_ in f:
            satir_ = satir_.strip()
            if satir_:
                try:
                    out.append(json.loads(satir_))
                except json.JSONDecodeError:
                    continue
    return out


def _yaz(yol, kayit):
    with yol.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


# ---- seviyeler ----------------------------------------------------------

def acik_seviyeler() -> list[dict]:
    """Silinmemiş seviyeler. Depo append-only; silme bir 'silindi' satırıdır."""
    silinen = {k["sil"] for k in _oku(SEVIYELER) if "sil" in k}
    return [k for k in _oku(SEVIYELER)
            if "sil" not in k and k.get("id") not in silinen]


@skill("seviye", "izlenecek fiyat seviyesi ekle", Risk.SARI, izinler=(Perm.YAZMA,),
       kullanim="seviye <sembol> <fiyat> [not]")
async def _seviye(arg):
    parca = arg.split()
    if len(parca) < 2:
        return [bilgi("kullanım: seviye BTC 95000 haftalık direnç"),
                bilgi("Venüs seviye önermez — işaretlediğin yeri hatırlatır.")]
    try:
        fiyat = float(parca[1].replace(",", "."))
    except ValueError:
        return [uyari(f"fiyat sayı olmalı (bulunan: {parca[1]!r})")]
    if fiyat <= 0:
        return [uyari("fiyat sıfırdan büyük olmalı")]

    kayit = {"id": uuid.uuid4().hex[:4], "t": datetime.now().isoformat(timespec="seconds"),
             "sembol": parca[0].upper(), "fiyat": fiyat, "not": " ".join(parca[2:])}
    _yaz(SEVIYELER, kayit)
    return [bilgi(f"eklendi · {kayit['id']}"),
            alan(kayit["sembol"], f"{fiyat:g}" + (f"   {kayit['not']}" if kayit["not"] else ""))]


@skill("seviyeler", "izlenen fiyat seviyeleri", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="seviyeler")
async def _seviyeler(arg):
    kayitlar = acik_seviyeler()
    if not kayitlar:
        return [bilgi("izlenen seviye yok."), bilgi("örnek: seviye BTC 95000 haftalık direnç")]
    out = [baslik(f"{len(kayitlar)} seviye")]
    for k in kayitlar:
        ek = f"   {k['not']}" if k.get("not") else ""
        out.append(alan(f"{k['id']}  {k['sembol']}", f"{k['fiyat']:g}{ek}"))
    out.append(bosluk())
    out.append(bilgi(f"fiyat %{YAKINLIK_YUZDE:g} yaklaşınca haber verilir · silmek için: "
                     f"seviye-sil <id>"))
    return out


@skill("seviye-sil", "seviyeyi kaldır", Risk.TURUNCU, izinler=(Perm.SILME,),
       kullanim="seviye-sil <id>")
async def _seviye_sil(arg):
    kimlik = arg.strip().lower()
    if not kimlik:
        return [uyari("kullanım: seviye-sil <id>")]
    if not any(k.get("id") == kimlik for k in acik_seviyeler()):
        return [uyari(f"seviye bulunamadı: {kimlik}")]
    _yaz(SEVIYELER, {"sil": kimlik, "t": datetime.now().isoformat(timespec="seconds")})
    return [bilgi(f"kaldırıldı · {kimlik}")]


def _bildirildi_mi(kimlik: str, gun: date) -> bool:
    kaynak = f"seviye:{kimlik}:{gun.isoformat()}"
    return any(b.kaynak == kaynak for b in bildirim_hepsi())


@periyodik(60, ad="seviye")
async def _seviye_kontrolu():
    """Fiyat işaretlenen seviyeye yaklaştıysa bir kez haber verir.

    Tekrar koruması bildirim deposundan okunur: gün içinde yeniden başlatmak
    aynı seviyeyi ikinci kez bildirmemeli.
    """
    kayitlar = acik_seviyeler()
    if not kayitlar:
        return
    bugun = date.today()
    bakilan: dict[str, float] = {}

    for k in kayitlar:
        if _bildirildi_mi(k["id"], bugun):
            continue
        sembol = k["sembol"]
        if sembol not in bakilan:
            try:
                _, d = await getir(sembol)
                bakilan[sembol] = float(d["lastPrice"])
            except (BorsaHatasi, KeyError, ValueError):
                bakilan[sembol] = 0.0     # bu turda atla, bir sonrakinde yine dene
        son = bakilan[sembol]
        if not son:
            continue

        uzaklik = abs(son - k["fiyat"]) / k["fiyat"] * 100
        if uzaklik <= YAKINLIK_YUZDE:
            ek = f" · {k['not']}" if k.get("not") else ""
            bildir(Seviye.YUKSEK,
                   f"{sembol} {k['fiyat']:g} seviyesine yaklaştı (şu an {son:g}){ek}",
                   f"seviye:{k['id']}:{bugun.isoformat()}")


# ---- HTF bias -----------------------------------------------------------

def son_bias() -> dict[str, dict]:
    """Sembol başına en son yazılan bias."""
    out: dict[str, dict] = {}
    for k in _oku(BIAS):
        out[k["sembol"]] = k
    return out


@skill("bias", "kendi HTF bias notunu kaydet", Risk.SARI, izinler=(Perm.YAZMA,),
       kullanim="bias <sembol> <long|short|nötr> [gerekçe]")
async def _bias(arg):
    parca = arg.split()
    if not parca:
        mevcut = son_bias()
        if not mevcut:
            return [bilgi("kayıtlı bias yok."),
                    bilgi("örnek: bias BTC long haftalık BOS sonrası"),
                    bilgi("Bu senin tezin. Venüs bias üretmez (Değişmez 4).")]
        out = [baslik("HTF bias — senin notun")]
        for s, k in sorted(mevcut.items()):
            ek = f"   {k['gerekce']}" if k.get("gerekce") else ""
            out.append(alan(f"{s}  {k['t'][5:10]}", f"{k['yon']}{ek}"))
        return out

    if len(parca) < 2:
        return [uyari("kullanım: bias BTC long haftalık BOS sonrası")]
    yon = YONLER.get(parca[1].lower())
    if yon is None:
        return [uyari(f"yön long / short / nötr olmalı (bulunan: {parca[1]!r})")]

    kayit = {"t": datetime.now().isoformat(timespec="seconds"),
             "sembol": parca[0].upper(), "yon": yon, "gerekce": " ".join(parca[2:])}
    _yaz(BIAS, kayit)
    return [bilgi("kaydedildi — bu senin tezin, Venüs'ün değil."),
            alan(kayit["sembol"], kayit["yon"] +
                 (f"   {kayit['gerekce']}" if kayit["gerekce"] else ""))]
