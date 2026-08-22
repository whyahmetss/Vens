import json
from datetime import datetime

from core.registry import Risk, Perm, skill, satir, bilgi, uyari
from core.log import VERI

NOTLAR = VERI / "notlar.jsonl"


@skill("not", "hızlı not düş", Risk.SARI, izinler=(Perm.YAZMA,),
       kullanim="not <metin>", takma_adlar=("n",))
async def _not(arg):
    metin = arg.strip()
    if not metin:
        return [uyari("kullanım: not fed toplantısı 21:00")]
    kayit = {"t": datetime.now().isoformat(timespec="seconds"), "metin": metin}
    with NOTLAR.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    return [bilgi("kaydedildi.")]


@skill("notlar", "son notlar", Risk.YESIL, izinler=(Perm.OKUMA,),
       kullanim="notlar [adet]")
async def _notlar(arg):
    if not NOTLAR.exists():
        return [bilgi("henüz not yok.")]
    try:
        n = int(arg.strip()) if arg.strip() else 12
    except ValueError:
        n = 12
    rows = []
    with NOTLAR.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        return [bilgi("henüz not yok.")]
    return [satir(f"  {r['t'][5:16].replace('T', ' ')}  {r['metin']}") for r in rows[-n:]]
