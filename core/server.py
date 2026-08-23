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
from . import bildirim, zamanlayici
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


@app.get("/yetenekler")
async def yetenekler():
    """Niyet çözücü (Faz 3) buradan besleneceği için şimdiden duruyor."""
    return [{"ad": s.ad, "aciklama": s.aciklama, "risk": s.risk.value,
             "kullanim": s.kullanim, "izinler": [i.value for i in s.izinler]}
            for s in hepsi()]


async def _bildirim_pompasi(sock: WebSocket, kuyruk: asyncio.Queue) -> None:
    """Bildirimleri kabuğa iter.

    Ayrı bir görev, çünkü bildirim kullanıcının komutundan bağımsız gelir —
    Venüs komut beklemeden konuşabilir (Bölüm 12).
    """
    while True:
        b = await kuyruk.get()
        # Rozet sayısı bildirimle birlikte gider: kuyruğa alınan bir bildirim
        # ekranı bölmez ama rozetin o anda artması gerekir.
        await sock.send_text(json.dumps({
            "bildirim": True, "seviye": b.seviye, "durum": b.durum,
            "saat": b.saat, "text": b.metin,
            "rozet": len(bildirim.bekleyenler()),
        }))


@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    oturum = uuid.uuid4().hex[:8]
    log.yaz("oturum", olay="acildi", oturum=oturum)

    # Çekirdek bildirimi senkron üretir, websocket'e yazmak async. Araya
    # kuyruk konur; bildirim üreten kod hiçbir zaman ağ için beklemez.
    kuyruk: asyncio.Queue = asyncio.Queue()
    bildirim.dinleyici_ekle(kuyruk.put_nowait)
    pompa = asyncio.create_task(_bildirim_pompasi(sock, kuyruk))

    try:
        # Açılışta bekleyen rozet sayısı gönderilir: kapalıyken biriken
        # bildirimler kaybolmamalı.
        await sock.send_text(json.dumps({"rozet": len(bildirim.bekleyenler())}))
        while True:
            mesaj = json.loads(await sock.receive_text())
            girdi = mesaj.get("cmd", "")
            for satir in await yonlendir(girdi, oturum):
                await sock.send_text(json.dumps(satir))
                await asyncio.sleep(0.015)
            await sock.send_text(json.dumps({"bitti": True,
                                             "rozet": len(bildirim.bekleyenler())}))
    except WebSocketDisconnect:
        log.yaz("oturum", olay="kapandi", oturum=oturum)
    finally:
        bildirim.dinleyici_cikar(kuyruk.put_nowait)
        pompa.cancel()
