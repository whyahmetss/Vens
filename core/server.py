"""
Kabuk ile çekirdek arasındaki köprü.

Şartname Bölüm 3: kabuk aptaldır, sadece gösterir ve iletir.
Sunucu yalnızca 127.0.0.1'e bağlanır — dışarı açık değildir.
"""

from __future__ import annotations
import asyncio, json, uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from . import log
from . import bildirim, kanal, zamanlayici
from .router import yonlendir
from .registry import hepsi

UI = Path(__file__).resolve().parent.parent / "ui" / "index.html"


@asynccontextmanager
async def _omur(app: FastAPI):
    # Periyodik kontroller ancak olay döngüsü varken başlatılabilir. Yetenekler
    # bu noktada yüklenmiş olur, yani @periyodik kayıtları tamamdır.
    adet = zamanlayici.baslat()
    log.yaz("baslangic", kontrol=adet)
    yield
    zamanlayici.durdur()


app = FastAPI(title="VENÜS", lifespan=_omur)


@app.get("/")
async def kabuk():
    return FileResponse(UI)


def _acilis() -> list[dict]:
    """Açılış sekansının satırları. Sabit metin değil, gerçek durum.

    Sinematik açılış (Bölüm 13) uydurulmuş bir yükleme çubuğu değildir;
    her satır o an gerçekten ölçülen bir şeyi söyler.
    """
    from .kurallar import yukle as kural_yukle
    from .zamanlayici import KONTROLLER

    k = kural_yukle()
    satirlar = [
        {"ad": "yetenek kayıt defteri", "deger": f"{len(hepsi())} yetenek"},
        {"ad": "kural dosyası",
         "deger": f"{len(k.tum())} kural" if k.okundu else "OKUNAMADI",
         "uyari": not k.okundu or bool(k.sorunlar)},
        {"ad": "olay günlüğü", "deger": log.VERI.name},
        {"ad": "periyodik kontrol", "deger": f"{len(KONTROLLER)} kontrol"},
    ]
    try:
        from . import niyet
        satirlar.append({"ad": "niyet çözücü",
                         "deger": niyet.model() if niyet.acik_mi() else "kapalı",
                         "uyari": not niyet.acik_mi()})
    except Exception:
        pass
    return satirlar


def _baglam() -> list[dict]:
    """Bağlam şeritinin içeriği. Yeteneği yüklüyse ondan alınır, yoksa boş.

    Köprü bağlamın NE olduğunu bilmez, yalnızca taşır (Değişmez 6).
    """
    try:
        from skills.merkez import baglam
    except Exception:
        return []
    try:
        return baglam()
    except Exception as e:
        log.yaz("baglam", sonuc="hata", hata=repr(e))
        return []


@app.get("/yetenekler")
async def yetenekler():
    """Niyet çözücü (Faz 3) buradan besleneceği için şimdiden duruyor."""
    return [{"ad": s.ad, "aciklama": s.aciklama, "risk": s.risk.value,
             "kullanim": s.kullanim, "izinler": [i.value for i in s.izinler]}
            for s in hepsi()]


async def _pompa(sock: WebSocket, kuyruk: asyncio.Queue) -> None:
    """Çekirdeğin ittiği mesajları kabuğa taşır.

    Ayrı bir görev, çünkü bunlar kullanıcının komutundan bağımsız gelir —
    Venüs komut beklemeden konuşabilir (Bölüm 12).
    """
    while True:
        m = dict(await kuyruk.get())
        # Rozet bildirimle birlikte gider: kuyruğa alınan bildirim ekranı
        # bölmez ama rozetin o anda artması gerekir.
        if m.get("bildirim"):
            m["rozet"] = len(bildirim.bekleyenler())
        await sock.send_text(json.dumps(m))


@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    oturum = uuid.uuid4().hex[:8]
    log.yaz("oturum", olay="acildi", oturum=oturum)

    # Çekirdek bildirimi senkron üretir, websocket'e yazmak async. Araya
    # kuyruk konur; bildirim üreten kod hiçbir zaman ağ için beklemez.
    kuyruk: asyncio.Queue = asyncio.Queue()
    kanal.abone(kuyruk.put_nowait)
    pompa = asyncio.create_task(_pompa(sock, kuyruk))

    try:
        # Açılışta bekleyen rozet sayısı gönderilir: kapalıyken biriken
        # bildirimler kaybolmamalı.
        await sock.send_text(json.dumps({"rozet": len(bildirim.bekleyenler()),
                                         "baglam": _baglam(),
                                         "acilis": _acilis()}))
        while True:
            mesaj = json.loads(await sock.receive_text())
            girdi = mesaj.get("cmd", "")
            kaynak = "ses" if mesaj.get("ses") else "klavye"
            for satir in await yonlendir(girdi, oturum, kaynak):
                await sock.send_text(json.dumps(satir))
                await asyncio.sleep(0.015)
            await sock.send_text(json.dumps({"bitti": True,
                                             "rozet": len(bildirim.bekleyenler()),
                                             "baglam": _baglam()}))
    except WebSocketDisconnect:
        log.yaz("oturum", olay="kapandi", oturum=oturum)
    finally:
        kanal.cik(kuyruk.put_nowait)
        pompa.cancel()
