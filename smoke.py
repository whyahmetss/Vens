import asyncio, sys
sys.path.insert(0, ".")
from run import yetenekleri_yukle
yetenekleri_yukle()
from core.registry import REGISTRY
from core.router import yonlendir

async def main():
    print("yetenekler:", sorted(REGISTRY))
    for cmd in ["yardim", "saat", "sistem", "not test kaydi", "notlar", "fiyat BTC", "log 5", "zirva"]:
        out = await yonlendir(cmd, "smoke")
        print(f"\n$ {cmd}")
        for l in out[:6]:
            print("   ", l["text"])
asyncio.run(main())
