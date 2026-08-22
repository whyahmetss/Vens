import asyncio, sys
sys.path.insert(0, ".")
from run import yetenekleri_yukle
yetenekleri_yukle()
from core.registry import REGISTRY
from core.router import yonlendir
from core import kurallar

async def main():
    print("yetenekler:", sorted(REGISTRY))
    for cmd in ["yardim", "saat", "sistem", "not test kaydi", "notlar", "fiyat BTC", "log 5", "zirva"]:
        out = await yonlendir(cmd, "smoke")
        print(f"\n$ {cmd}")
        for l in out[:6]:
            print("   ", l["text"])

    k = kurallar.yukle()
    print(f"\n# kurallar  ({k.dosya.name}, okundu={k.okundu}, {len(k.tum())} kural)")
    for yol, deger in k.tum().items():
        print(f"    {yol:<34} {deger}")
    for s in k.sorunlar:
        print(f"    ! {s}")

asyncio.run(main())
