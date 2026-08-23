# VENÜS

Kişisel AI çalışma ortamı. Faz 0 (iskelet, köprü, olay günlüğü), Faz 1 (kurallar ve
ihlal denetleyicisi) ve Faz 2'nin (jurnal) **kodu** yazıldı.
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
| `kurallar` | aktif kuralları ve kural dosyasındaki sorunları göster |
| `ihlaller [adet]` | kaydedilmiş kural ihlalleri ve dağılımı |
| `jurnal <alan=değer>` | işlem kaydı ekle, kayıt anında kural denetimi |
| `kayitlar [adet]` | son jurnal kayıtları |
| `kayit <id>` | tek kaydın tamamı |
| `istatistik` | R ortalaması, win rate, setup dağılımı |
| `eksik` | sonuçlanmamış ve zorunlu alanı boş kayıtlar |
| `bildirimler` | bekleyen bildirimler ve günlük bütçe durumu |
| `seans` | killzone saatleri ve şu an açık olan seans |
| `log [adet]` | son olaylar |
| `temizle` | ekranı boşalt (kabukta çalışır, çekirdeğe gitmez) |

## Yapı

```
run.py            başlatıcı — skills/ klasörünü otomatik tarar
core/
  registry.py     yetenek kayıt defteri, risk sınıfları, izinler
  kurallar.py     kurallar.yaml okuyucu + doğrulayıcı
  denetci.py      kural ihlali denetleyicisi (deterministik)
  jurnal.py       işlem kaydı biçimi + jsonl depo
  niyet.py        serbest cümle → yetenek eşlemesi (Faz 3)
  model.py        görev başına model seçimi
  bildirim.py     bildirim seviyeleri + günlük bütçe
  zamanlayici.py  periyodik kontrol çalıştırıcısı
  router.py       yönlendirme, risk kapısı, onay akışı
  log.py          jsonl olay günlüğü
  server.py       fastapi + websocket + kabuk servisi
skills/           her dosya bir yetenek grubu
ui/index.html     kabuk
```

Veri `~/.venus/` altında: `olaylar.jsonl`, `notlar.jsonl`, `jurnal.jsonl`, `ihlaller.jsonl`.
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

## Kurallar ve jurnal

`kurallar.yaml` kullanıcının kendi koyduğu kurallardır. Deterministik kod okur ve
doğrular (`core/kurallar.py`) — LLM'e sorulmaz. Yazım hatası, tip hatası ve dedektörü
olmayan yasak adı `kurallar` komutunda raporlanır; geçersiz satır sessizce yok sayılmaz.

Her jurnal kaydı yazılırken kurallara karşı denetlenir. Venüs ihlali **engellemez,
kaydeder** (şartname Bölüm 5): kayıt her hâlükârda yazılır, ihlaller hem kaydın içinde
hem `ihlaller.jsonl`'da durur. Nihai karar kullanıcınındır.

```
jurnal sembol=XAUUSD yon=long seans=londra risk=1 hedef_r=3 sonuc_r=2.4 \
       setup="sweep → MSS → FVG" giris_sebebi="OTE 0.705" execution=iyi duygu=sakin
```

Giriş serbest cümle değil `alan=değer`: niyet çözücü Faz 3'te geliyor, o zamana kadar
giriş tahmin edilmemeli. `zaman=SS:DD` işlemin zamanını kaydın zamanından ayırır —
gece toplu girilen kayıtlarda "kayıp sonrası bekleme" kuralı yoksa anlamsızlaşır.

## Serbest cümle (Faz 3)

Bilinen bir komut yazarsan doğrudan çalışır — model devreye girmez, gecikme ve
maliyet sıfırdır. Komut olarak tanınmayan bir girdi niyet çözücüye düşer:

```
> bitcoin ne kadar olmuş
→ fiyat BTC
BTC  108,412.5
```

Ne anlaşıldığı her zaman `→` satırında gösterilir; yanlış eşlemeyi görmeden
sonuç almazsın. Modele "ne yapayım" değil "hangi yeteneği hangi parametreyle
çağırayım" sorulur, tek çağrıda — ajan döngüsü yoktur, model hiçbir şey
çalıştırmaz. Kayıt defterinde olmayan bir ad dönerse çağrı reddedilir ve
`Risk.TURUNCU` yetenekler niyetle gelse de onay ister.

### Kurulum

```bash
export ANTHROPIC_API_KEY=sk-ant-...     # console.anthropic.com
python run.py
```

Anahtar yoksa, `anthropic` paketi kurulu değilse ya da ağ düşerse kabuk eskisi
gibi deterministik çalışır ve sebebini söyler. Niyet çözücü bir kolaylıktır,
bağımlılık değildir. `VENUS_NIYET=kapali` ile büsbütün kapatılır.

### Model seçimi

Tek bir "Venüs modeli" yok — her LLM görevi kendi modelini seçer, tablo
`core/model.py`'de:

| görev | varsayılan | ne yapar |
|---|---|---|
| `niyet` | `claude-opus-5` | serbest cümleyi kapalı yetenek listesine eşler |

Değiştirmek için tabloyu düzenle, ya da denemek için:

```bash
VENUS_MODEL_NIYET=claude-haiku-4-5 python run.py   # tek görevi
VENUS_MODEL=claude-sonnet-5 python run.py          # hepsini birden
```

Çağrı başına ~1600 jeton girdi gider (araç listesi + sistem metni). Bu prompt
cache eşiğinin üstünde olduğu için arka arkaya cümlelerde girdi belirgin
ucuzlar. Jeton sayıları `olaylar.jsonl`'a yazılır — maliyet tahmin edilmez,
ölçülür: `log` komutuyla bakılır.

## Sonraki adım

Kod olarak sıradaki **Faz 3 — niyet çözücü**, ama önce iki şey gerekiyor:

1. **`kimlik.md` ve `kurallar.yaml` doldurulmalı** *(kullanıcı)*. İkisi de şu an taslak;
   kurallar.yaml'daki değerler örnektir, denetleyici onlara göre çalışır.
2. **Faz 2'nin bitiş kriteri:** jurnal bir hafta gerçekten kullanılmalı. Kullanılmıyorsa
   ileri gitmek ölü kod üretir — geri dönüp doğru yetenekleri bulmak gerekir.

Faz 3 ayrıca model kararına bağlıdır (şartname Bölüm 15: bulut API mi, lokal model mi).
