#!/usr/bin/env python3
"""
VENÜS — başlatıcı.

    python run.py

Yetenekler skills/ klasöründen otomatik yüklenir.
Yeni yetenek eklemek = klasöre bir .py dosyası koymak.
"""

import importlib, pkgutil, sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))

HOST, PORT = "127.0.0.1", 8712


def yetenekleri_yukle() -> int:
    import skills
    sayac = 0
    for m in pkgutil.iter_modules(skills.__path__):
        importlib.import_module(f"skills.{m.name}")
        sayac += 1
    return sayac


def main():
    import uvicorn
    from core.registry import REGISTRY
    from core import log

    modul = yetenekleri_yukle()
    log.yaz("baslangic", modul=modul, yetenek=len(REGISTRY))

    print(f"\n  VENÜS · {len(REGISTRY)} yetenek, {modul} modül")
    print(f"  veri  → {log.VERI}")
    print(f"  kabuk → http://{HOST}:{PORT}\n")

    uvicorn.run("core.server:app", host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
