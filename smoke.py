import asyncio, sys
sys.path.insert(0, ".")


def _duz(l):
    """Kabuk satırının metin karşılığı. Hizalama kabuğun işi; burada kaba dök."""
    if "etiket" in l:
        return f"{l['etiket']:<26} {l['deger']}"
    if "baslik" in l:
        return f"[{l['baslik']}]"
    if "bosluk" in l:
        return ""
    return l.get("text", "")


from run import yetenekleri_yukle
yetenekleri_yukle()
from core.registry import REGISTRY
from core.router import yonlendir
from core import kurallar

async def main():
    print("yetenekler:", sorted(REGISTRY))
    for cmd in ["yardim", "saat", "sistem", "not test kaydi", "notlar", "fiyat BTC", "kurallar",
                'jurnal sembol=XAUUSD yon=long seans=londra risk=1 hedef_r=3 sonuc_r=2.4 '
                'setup="sweep → MSS → FVG" giris_sebebi="OTE 0.705" duygu=sakin',
                "kayitlar", "tamamla", "ihlaller", "istatistik", "eksik",
                "bildirimler", "seans", "seviyeler", "bias", "merkez", "beyazliste", "izinler",
                "log 5", "zirva"]:
        out = await yonlendir(cmd, "smoke")
        print(f"\n$ {cmd}")
        for l in out[:6]:
            print("   ", _duz(l))

    k = kurallar.yukle()
    print(f"\n# kurallar  ({k.dosya.name}, okundu={k.okundu}, {len(k.tum())} kural)")
    for yol, deger in k.tum().items():
        print(f"    {yol:<34} {deger}")
    for s in k.sorunlar:
        print(f"    ! {s}")

asyncio.run(main())
