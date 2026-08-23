"""
Bildirim yeteneği — bekleyenleri gösterir ve okundu işaretler.

Şartname Bölüm 12. Kesintili bildirimler zaten ekrana düşer; bu komut
rozette bekleyenler ve bütçe dolduğu için kuyruğa alınanlar içindir.
"""

from core.registry import Risk, Perm, skill, satir, bilgi, uyari, vurgu
from core import bildirim as motor

ISARET = {"kritik": "■", "yuksek": "▲", "normal": "●", "dusuk": "·"}


@skill("bildirimler", "bekleyen bildirimler", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="bildirimler", takma_adlar=("bildirim",))
async def _bildirimler(arg):
    bekleyen = motor.bekleyenler()
    iletilen = motor.bugun_iletilen()
    kalan = max(0, motor.GUNLUK_BUTCE - iletilen)

    if not bekleyen:
        return [bilgi("bekleyen bildirim yok."),
                bilgi(f"günlük bütçe: {iletilen}/{motor.GUNLUK_BUTCE} kullanıldı.")]

    out = [vurgu(f"{len(bekleyen)} bildirim")]
    for b in bekleyen:
        isaret = ISARET.get(b.seviye, "●")
        kuyruk = "  (kuyrukta)" if b.durum == "kuyrukta" else ""
        cizgi = f"  {isaret} {b.saat}  {b.metin}{kuyruk}"
        out.append(uyari(cizgi) if b.seviye in ("kritik", "yuksek") else satir(cizgi))

    out.append(bilgi(""))
    out.append(bilgi(f"günlük bütçe: {iletilen}/{motor.GUNLUK_BUTCE} kullanıldı"
                     + (f", {kalan} kesinti hakkı kaldı." if kalan else
                        " — bugün başka bildirim ekranı bölmez.")))
    motor.okundu()
    return out
