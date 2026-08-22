"""
Kabuk ile çekirdek arasındaki köprü.

Şartname Bölüm 3: kabuk aptaldır, sadece gösterir ve iletir.
Sunucu yalnızca 127.0.0.1'e bağlanır — dışarı açık değildir.
"""

from __future__ import annotations
import asyncio, json, uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from . import log
from .router import yonlendir
from .registry import hepsi

UI = Path(__file__).resolve().parent.parent / "ui" / "index.html"

app = FastAPI(title="VENÜS")


@app.get("/")
async def kabuk():
    return FileResponse(UI)


@app.get("/yetenekler")
async def yetenekler():
    """Niyet çözücü (Faz 3) buradan besleneceği için şimdiden duruyor."""
    return [{"ad": s.ad, "aciklama": s.aciklama, "risk": s.risk.value,
             "kullanim": s.kullanim, "izinler": [i.value for i in s.izinler]}
            for s in hepsi()]


@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    oturum = uuid.uuid4().hex[:8]
    log.yaz("oturum", olay="acildi", oturum=oturum)
    try:
        while True:
            mesaj = json.loads(await sock.receive_text())
            girdi = mesaj.get("cmd", "")
            for satir in await yonlendir(girdi, oturum):
                await sock.send_text(json.dumps(satir))
                await asyncio.sleep(0.015)
            await sock.send_text(json.dumps({"bitti": True}))
    except WebSocketDisconnect:
        log.yaz("oturum", olay="kapandi", oturum=oturum)
