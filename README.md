# VENÜS — Faz 0

Kişisel AI çalışma ortamı. Bu sürüm **Faz 0**: iskelet, köprü, üç yetenek grubu, olay günlüğü.
Henüz yapay zekâ yok — o Faz 3'te (niyet çözücü) geliyor. Şu an deterministik bir kabuk.

## Çalıştırma

```bash
pip install -r requirements.txt
python run.py
```

Sonra: **http://127.0.0.1:8712**

Sunucu yalnızca `127.0.0.1`'e bağlanır. Dışarı açık değildir, bu yüzden kimlik doğrulama yoktur.
Dışarı açacaksan (telefondan erişim) önce kimlik doğrulama gerekir — bkz. şartname Bölüm 15.

## Komutlar

| komut | ne yapar |
|---|---|
| `yardim` | yetenek listesi, risk işaretleriyle |
| `saat` | zaman damgası |
| `sistem` | cpu / bellek / disk |
| `not <metin>` | hızlı not |
| `notlar [adet]` | son notlar |
| `fiyat <sembol>` | canlı spot fiyat (`fiyat BTC`) |
| `log [adet]` | son olaylar |
| `temizle` | ekranı boşalt (kabukta çalışır, çekirdeğe gitmez) |

## Yapı

```
run.py            başlatıcı — skills/ klasörünü otomatik tarar
core/
  registry.py     yetenek kayıt defteri, risk sınıfları, izinler
  router.py       yönlendirme, risk kapısı, onay akışı
  log.py          jsonl olay günlüğü
  server.py       fastapi + websocket + kabuk servisi
skills/           her dosya bir yetenek grubu
ui/index.html     kabuk
```

Veri `~/.venus/` altında: `olaylar.jsonl`, `notlar.jsonl`.
`VENUS_VERI` ortam değişkeniyle değiştirilebilir.

## Yeni yetenek eklemek

`skills/` içine bir `.py` koy. Kayıt otomatik.

```python
from core.registry import Risk, Perm, skill, satir, bilgi

@skill("selam", "örnek yetenek", Risk.YESIL,
       izinler=(Perm.OKUMA,), kullanim="selam <ad>")
async def _selam(arg):
    return [satir(f"merhaba {arg or 'yabancı'}")]
```

**Risk sınıfı ve izinler zorunludur** (şartname Bölüm 2 ve 6).
`Risk.TURUNCU` işaretli yetenekler çalışmadan önce kullanıcıdan onay ister.
`Risk.KIRMIZI` kayıt sırasında reddedilir — v1'de yoktur.

## Test

```bash
python smoke.py
```

Her yeteneği çağırır, çıktısını basar. Faz 8'deki gece vardiyasının açılış
sağlık kontrolü bunun üstüne kurulacak.

## Sonraki adım

**Faz 1 — kimlik ve kurallar.** Venüs'ün karakter dosyası ve trading kuralları,
ardından kural ihlali denetleyicisi. Şartname Bölüm 4 ve 5.
