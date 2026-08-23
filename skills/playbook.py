"""
Playbook yeteneği — setup tanımlarını ve kontrol listelerini gösterir.

skills/kural.py'nin kardeşi: çekirdek okur ve doğrular (core/playbook.py),
bu dosya yalnızca sunar. Setup değiştirmek buradan yapılmaz, playbook.yaml
düzenlenir.
"""

from core.registry import Risk, Perm, skill, bilgi, uyari, alan, baslik, bosluk
from core import kurallar as kural_motoru
from core import playbook as motor


@skill("playbook", "setup tanımları ve kontrol listeleri", Risk.YESIL,
       izinler=(Perm.OKUMA,), kullanim="playbook [setup]", takma_adlar=("setuplar",))
async def _playbook(arg):
    pb = motor.yukle(kurallar=kural_motoru.yukle())

    if not pb.okundu:
        out = [uyari("playbook okunamadı — kalite karnesi yalnızca kurallara bakar.")]
        out += [alan(pb.dosya.name, s, "warn") for s in pb.sorunlar]
        return out

    istenen = arg.strip().lower()
    if istenen:
        s = pb.setup(istenen)
        if s is None:
            return [uyari(f"setup bulunamadı: {istenen}"),
                    bilgi("tanımlılar: " + (", ".join(pb.setuplar) or "yok"))]
        out = [baslik(s.baslik)]
        if s.min_rr:
            out.append(alan("asgari R:R", f"{s.min_rr:g}"))
        for m in s.kontrol:
            out.append(alan(f"{m.ad}  -{m.agirlik}", m.soru))
        out.append(bosluk())
        out.append(bilgi("kayıtta işaretlemek için: "
                         f"kontrol={','.join(m.ad for m in s.kontrol)}"))
        return out

    out = []
    if pb.setuplar:
        out.append(baslik(f"{len(pb.setuplar)} setup"))
        for ad, s in pb.setuplar.items():
            ek = f"   min {s.min_rr:g}R" if s.min_rr else ""
            out.append(alan(ad, f"{len(s.kontrol)} madde{ek}   {s.baslik}"))
        out.append(bosluk())
    else:
        out.append(bilgi("tanımlı setup yok — karne yalnızca kurallara bakar."))
        out.append(bilgi(f"doldurmak için: {pb.dosya}"))

    if pb.etiketler:
        out.append(baslik("etiketler"))
        out.append(alan("tanımlı", ", ".join(pb.etiketler)))
        out.append(bosluk())

    if pb.sorunlar:
        out.append(baslik(f"{len(pb.sorunlar)} sorun — bu satırlar yok sayılıyor"))
        out += [uyari(f"  {s}") for s in pb.sorunlar]
        out.append(bosluk())

    out.append(bilgi("Venüs grafiği göremez — kontrol maddeleri senin beyanın. "
                     "Değeri, sonucu bilmeden verilmiş olmasından gelir."))
    return out
