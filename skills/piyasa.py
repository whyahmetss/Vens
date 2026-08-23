import httpx

from core.registry import Risk, Perm, skill, satir, bilgi, uyari

BORSA = "https://api.binance.com/api/v3/ticker/24hr"


KOTASYONLAR = ("USDT", "USDC", "TRY", "BTC", "ETH")


def _sembol(giris: str) -> str:
    s = giris.strip().upper().replace(" ", "").replace("/", "")
    # "BTC" tek başına bir çift değil, taban varlıktır. Sadece kotasyondan
    # UZUN olan girdiler tam çift sayılır: "BTCUSDT" evet, "BTC" hayır.
    for q in KOTASYONLAR:
        if s.endswith(q) and len(s) > len(q):
            return s
    return s + "USDT"


class BorsaHatasi(Exception):
    """Fiyat alınamadı. Sebebi kullanıcıya gösterilebilir tek cümledir."""


async def getir(giris: str) -> tuple[str, dict]:
    """Tek sembolün 24s verisi. Seviye takibi de buradan besleniyor —
    borsa erişimi tek yerde dursun, iki yerde tekrar edilmesin."""
    sym = _sembol(giris)
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(BORSA, params={"symbol": sym})
    except Exception as e:
        raise BorsaHatasi(f"borsaya ulaşılamadı: {e}") from e

    if r.status_code == 451:
        raise BorsaHatasi("borsa bu konumdan erişimi kısıtlıyor (451)")
    if r.status_code != 200:
        raise BorsaHatasi(f"sembol bulunamadı: {sym}  ({r.status_code})")
    return sym, r.json()


@skill("fiyat", "canlı spot fiyat", Risk.YESIL, izinler=(Perm.AG,),
       kullanim="fiyat <sembol>", takma_adlar=("p",))
async def _fiyat(arg):
    if not arg.strip():
        return [uyari("kullanım: fiyat BTC")]
    try:
        sym, d = await getir(arg)
    except BorsaHatasi as e:
        out = [uyari(str(e))]
        if "451" in str(e):
            out.append(bilgi("VPN gerekebilir ya da başka bir veri kaynağına geçilmeli."))
        return out

    son = float(d["lastPrice"])
    chg = float(d["priceChangePercent"])
    ok = "▲" if chg >= 0 else "▼"
    return [
        satir(f"{sym}  {son:,.4f}".rstrip("0").rstrip(".")),
        satir(f"  24s    {ok} %{chg:+.2f}", "" if chg >= 0 else "warn"),
        bilgi(f"  aralık {float(d['lowPrice']):,.2f} — {float(d['highPrice']):,.2f}"),
        bilgi(f"  hacim  {float(d['quoteVolume']):,.0f} USDT"),
    ]
