"""
Yönlendirici — çekirdeğin karar veren parçası.

Şartname Bölüm 3: çekirdek karar verir ama iş yapmaz.
Hangi yetenek, hangi parametre, izin var mı, onay gerekir mi.
"""

from __future__ import annotations
import inspect, time

from . import izin, log, niyet, sembol
from .registry import Risk, bul, satir, uyari, bilgi

# Bekleyen onaylar: oturum -> (yetenek, argüman)
_BEKLEYEN: dict[str, tuple] = {}


async def _cagir(s, arg: str):
    sonuc = s.fn(arg)
    if inspect.isawaitable(sonuc):
        sonuc = await sonuc
    return sonuc or []


async def yonlendir(girdi: str, oturum: str = "yerel",
                    kaynak: str = "klavye") -> list[dict]:
    girdi = girdi.strip()
    if not girdi:
        return []

    # Sembol düzeltmesi YALNIZCA sesten gelene uygulanır (Bölüm 8). Klavyeden
    # "bitisi" yazan kullanıcı onu kastetmiştir.
    onek: list[dict] = []
    if kaynak == "ses":
        yeni_girdi, degisiklikler = sembol.duzelt(girdi)
        if degisiklikler:
            log.yaz("ses", olay="sembol_duzeltildi", ham=girdi,
                    duzeltilmis=yeni_girdi, degisiklik=degisiklikler)
            onek.append(bilgi("duydum: " + ", ".join(
                f"{a} → {b}" for a, b in degisiklikler)))
            girdi = yeni_girdi

    # --- bekleyen onay var mı? ---
    if oturum in _BEKLEYEN:
        s, arg = _BEKLEYEN.pop(oturum)
        if girdi.lower() in ("e", "evet", "onayla", "y", "yes"):
            log.yaz("onay", yetenek=s.ad, arg=arg, sonuc="kabul")
            return await _calistir(s, arg)
        log.yaz("onay", yetenek=s.ad, arg=arg, sonuc="ret")
        return [bilgi("iptal edildi.")]

    komut, _, arg = girdi.partition(" ")
    s = bul(komut)

    if s is None:
        return onek + await _niyet_yolu(girdi, komut, oturum)

    return onek + await _risk_kapisi(s, arg, oturum)


async def _risk_kapisi(s, arg: str, oturum: str) -> list[dict]:
    """Bölüm 2 ve 9. Niyet çözücüyle gelen çağrı da buradan geçer — atlanabilir yol yok."""
    # İzin kapısı riskten önce gelir: kapatılmış izin isteyen yetenek onaya
    # bile sunulmaz (Bölüm 9).
    engelli = izin.engel(s.izinler)
    if engelli:
        log.yaz("izin", olay="reddedildi", yetenek=s.ad, izin=engelli)
        return [uyari(f"'{s.ad}' çalışmadı — kapalı izin: {', '.join(engelli)}"),
                bilgi("izinler guard/izinler.yaml dosyasından açılır.")]

    if s.risk is Risk.TURUNCU:
        _BEKLEYEN[oturum] = (s, arg)
        log.yaz("onay_istendi", yetenek=s.ad, arg=arg)
        return [uyari(f"'{s.ad}' geri alınması zor bir işlem."),
                satir("onaylıyor musun? (evet / hayır)")]

    return await _calistir(s, arg)


async def _niyet_yolu(girdi: str, komut: str, oturum: str) -> list[dict]:
    """Bilinen komut yoksa serbest cümle kabul edilir (Faz 3).

    Deterministik yol her zaman önce denenir: bilinen komut modele hiç
    gitmez — gecikme de maliyet de sıfır kalır.
    """
    if not niyet.acik_mi():
        log.yaz("komut", girdi=girdi, sonuc="bilinmeyen")
        return [uyari(f"bilinmeyen komut: {komut}"),
                bilgi('"yardim" yazarak listeye bak.'),
                bilgi(f"serbest cümle için: {niyet.neden_kapali()}")]

    n = await niyet.coz(girdi)
    if n.yetenek is None:
        log.yaz("komut", girdi=girdi, sonuc="niyet_yok", sebep=n.hata)
        return [uyari(n.hata or "anlaşılmadı."),
                bilgi('"yardim" yazarak yetenek listesine bak.')]

    s = bul(n.yetenek)
    if s is None:      # coz() zaten denetliyor; ikinci kapı ucuz
        return [uyari(f"kayıtlı olmayan yetenek: {n.yetenek}")]

    # Ne anlaşıldığı her zaman gösterilir: kullanıcı yanlış eşlemeyi görmeli.
    return [bilgi(f"→ {n.komut}")] + await _risk_kapisi(s, n.arg, oturum)


async def _calistir(s, arg: str) -> list[dict]:
    t0 = time.perf_counter()
    try:
        cikti = await _cagir(s, arg)
        ms = int((time.perf_counter() - t0) * 1000)
        log.yaz("komut", yetenek=s.ad, arg=arg, risk=s.risk.value,
                sonuc="basarili", ms=ms, satir_sayisi=len(cikti))
        return cikti
    except Exception as e:
        log.yaz("komut", yetenek=s.ad, arg=arg, risk=s.risk.value,
                sonuc="hata", hata=repr(e))
        return [uyari(f"hata: {e}")]
