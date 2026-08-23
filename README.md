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
| `playbook [setup]` | setup tanımları ve kontrol listeleri |
| `ihlaller [adet]` | kaydedilmiş kural ihlalleri ve dağılımı |
| `jurnal <alan=değer>` | işlem kaydı ekle, kayıt anında kural denetimi |
| `kayitlar [adet]` | son jurnal kayıtları |
| `kayit <id>` | tek kaydın tamamı |
| `tamamla <id> alan=değer` | açık pozisyonu kapat ya da kaydı düzelt |
| `istatistik` | R ortalaması, win rate, setup dağılımı |
| `analiz [görünüm]` | setup/seans/sembol/RR kırılımı, tekrarlanan davranışlar |
| `review [id]` | plan ile gerçeğin karşılaştırması |
| `koc` | tekrarlanan davranışları yüzüne tutar |
| `eksik` | sonuçlanmamış ve zorunlu alanı boş kayıtlar |
| `bildirimler` | bekleyen bildirimler ve günlük bütçe durumu |
| `seans` | killzone saatleri ve şu an açık olan seans |
| `merkez` | Command Center ekranı (ESC ile kapanır) |
| `seviye <sembol> <fiyat>` | izlenecek fiyat seviyesi işaretle |
| `seviyeler` | işaretli seviyeler |
| `bias <sembol> <yön>` | kendi HTF bias notun |
| `beyazliste` | Venüs'ün açabildiği uygulama, sayfa, düzenler |
| `ac <ad>` | kayıtlı uygulama/sayfa aç |
| `duzen <ad>` | kayıtlı çalışma alanı düzenini kur |
| `izinler` | hangi yetenek hangi izni istiyor, hangileri kapalı |
| `log [adet]` | son olaylar |
| `temizle` | ekranı boşalt (kabukta çalışır, çekirdeğe gitmez) |

## Yapı

```
run.py            başlatıcı — skills/ klasörünü otomatik tarar
core/
  registry.py     yetenek kayıt defteri, risk sınıfları, izinler
  kurallar.py     kurallar.yaml okuyucu + doğrulayıcı
  denetci.py      kural ihlali denetleyicisi (deterministik)
  playbook.py     setup tanımları + kontrol listeleri
  karne.py        uyum karnesi ve kalite skoru
  analiz.py       kırılımlar + tekrarlanan davranış analizi
  review.py       plan ↔ gerçek karşılaştırması
  koc.py          sabit şablonlu sorgulama (LLM yok)
  jurnal.py       işlem kaydı biçimi + jsonl depo
  niyet.py        serbest cümle → yetenek eşlemesi (Faz 3)
  model.py        görev başına model seçimi
  bildirim.py     bildirim seviyeleri + günlük bütçe
  zamanlayici.py  periyodik kontrol çalıştırıcısı
  sembol.py       konuşma tanıma sembol düzeltmesi
  kanal.py        kabuğa itme kanalı (bildirim + bağlam)
  izin.py         izin denetimi (guard/izinler.yaml)
guard/            ajanın yazma alanı DIŞINDA — izin + beyaz liste
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

## Playbook ve kalite karnesi

`kurallar.yaml` "neyi asla yapma" der. `playbook.yaml` "bir işlemin geçerli
sayılması için ne görmüş olman gerekir" der. İkisi birlikte her kayda bir karne
çıkarır:

```
karne · 5/11 · kalite 0/100
  ✓ zorunlu_alanlar      uygun
  ✗ maks_risk_yuzde      risk %4 — limit %1
  ✗ izinli_seanslar      izinli olmayan seans: asya
  ✗ liquidity_sweep      Likidite süpürüldü mü?
```

Skor deterministiktir: 100'den başlar, her ihlal ve her işaretlenmemiş kontrol
maddesi kendi ağırlığı kadar düşürür. Ağırlıklar `playbook.yaml`'da. Modele
hiçbir şey sorulmaz — aynı kayıt her zaman aynı skoru verir.

Setup'a özel `min_rr` global kuralı **yalnızca sıkılaştırabilir.** Daha gevşek
bir değer yok sayılır ve `playbook` uyarır.

**Venüs grafiği göremez.** "liquidity_sweep ✓" onun doğrulaması değil, senin
beyanın. Değeri şuradan gelir: beyanı sonucu bilmeden verirsin ve kilitlenir.

## Analiz

`istatistik` "ne oldu" der. `analiz` "neden oldu ve tekrar mı ediyor" der:

```
SEANS
  new_york_am    21 işlem   +27.8R   ort +1.32R   %86
  asya            9 işlem    -8.0R   ort -0.89R   %0

KALİTE SKORU → SONUÇ
  90 – 100       18 işlem   +26.9R   ort +1.49R   %83
  0 – 49          9 işlem    -8.0R   ort -0.89R   %0
  → fark         90-100 ile 0-49 arası +2.38R/işlem

TEKRARLANAN DAVRANIŞLAR
  fomo (senin etiketin)              9x   0K / 9Z   -8.0R
  izinli_seanslar (denetçi yakaladı) 9x   0K / 9Z   -8.0R
  → zararlı davranışların birleşik etkisi  -9.1R  (20 işlem)
```

Görünümler: `analiz setup | seans | sembol | rr | skor | hata`

Üç şeye dikkat:

**Kalite skoru → sonuç kırılımı**, playbook'un gerçekten bir şey ölçüp
ölçmediğinin tek objektif kanıtıdır. Yüksek skorlu işlemler daha iyi sonuç
vermiyorsa kontrol listeni gözden geçirmen gerekir — Venüs bunu söyler.

**Davranışların R'leri toplanmaz.** Tek bir kötü işlem hem "fomo" hem "izinli
olmayan seans" hem "risk aşımı" olabilir; satırları toplarsan aynı zararı üç kez
sayarsın. Birleşik etki, o davranışlardan en az birinin görüldüğü işlemlerin
toplamıdır.

**Az örnek istatistik değildir.** 5 işlemin altındaki gruplar gösterilir ama
"en iyi / en kötü" sıralamasına girmez.

## Review ve koç

`review <id>` girişte söylediğinle sonra olanı yan yana koyar:

```
PLAN (girişte söylediğin)
  giriş sebebi   OTE 0.705
  htf            haftalık BOS
GERÇEK (sonra olan)
  sonradan not   htf: aslında range içindeydi
KARŞILAŞTIRMA
  plan       hedef 3R, sonuç +0.60R — planın %20'inde kapattın
  kontrol    2/4 madde işaretsizdi: fvg, ote
  sonradan   1 işlem sonrası not var — girişte söylemediğin bir şeyi
             sonradan eklemek istemişsin
```

`koc` istatistiği soru olarak önüne koyar:

```
fomo  (senin etiketin)
  son 42 işleminde 9 kez görüldü
  9 zarar / 0 kâr
  toplam etki -8.0R
  aynı işlemler şu adlarla da görünüyor: maks_risk_yuzde, izinli_seanslar, seans: asya
  Bu davranışı sürdürmek için istatistiksel gerekçen nedir?
```

**Şablonlar sabittir ve `core/koc.py`'de görünür — LLM kullanılmaz.** Sebep
Bölüm 10'daki gerekçenin aynısı: modelin ürettiği ikna edici bir cümle, logdan
senin kendi çıkarımından ayırt edilemez. Koç seni ikna etmez, sayıyı önüne koyar.

Kural: **koç asla "şunu yap" demez.** Her şablon bir soruyla ya da çıplak bir
sayıyla biter. Yeni şablon eklerken bu doğrulanmalı.

Örtüşen bulgular teke iner: aynı 9 kötü işlem "fomo", "risk aşımı", "izinsiz
seans" ve "min_rr" olarak dört kez sorulursa tek problem dört sorun gibi görünür.

Eşikler gürültüyü keser — 4 tekrardan az, 5 işlemden küçük grup ya da 1R'den
düşük etki bulgu sayılmaz. Az örneğe dayanarak birini sorguya çekmek, onu
gürültüye göre davranmaya iter.

## Geçmiş yeniden yazılamaz

Kayıt yazıldıktan sonra girişteki gerekçe değişmez. `tamamla` yalnızca girişte
bilinmesi **imkânsız** olan ve hâlâ **boş** olan alanları doldurur:

```
sonuc_r · cikis_sebebi · execution · gorsel · etiket
```

Başka bir alana yazmak üzerine yazmaz, işlem sonrası nota döner:

```
ORIGINAL
  giriş     OTE 0.705
  plan      long  risk %5  hedef 3R
POST-TRADE NOTE
  08-23 06:13   risk: 1.0 · htf: aslında bullish idi
```

"Aslında HTF de uygundu" demek meşrudur; onu girişteki gerekçenmiş gibi
göstermek değildir. Sonradan hikâye uydurulamaz.

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

## Gece vardiyası (Faz 8)

Venüs kendi kodunu **çalışırken değiştirmez**. Ayrı bir kopyada çalışıp değişiklik
önerir; onay senindir.

```
guard/gece            gece koşusu: backlog'dan TEK madde, lab/ kopyası, rapor
guard/venus durum     bekleyen gece dalları, son geri dönüş noktası
guard/venus onayla    birleştir, iyi nokta işaretle, GELISIM.md'ye yaz
guard/venus reddet    dalı sil, sebebi backlog'a düş
guard/venus ertele    dala dokunma
guard/venus geri-al   son bilinen iyi noktaya dön
guard/venus baslat    sağlık kontrolü + gerekirse geri dönüş + Venüs
```

`guard/` **ajanın yazma alanı dışındadır.** İzin ve sınır dosyaları orada durur.
`guard/venus` saf bash + git'tir: `geri-al` Venüs açılmadığında da çalışmak
zorundadır — sistemin bozulduğu an, tam olarak ona ihtiyaç duyulan andır.

Korumalar (Bölüm 18.4-18.6), hepsi sınandı:

- **guard/'a dokunan dal tartışmasız reddedilir.** Asıl risk ajanın hatalı kod
  yazması değil, kendi denetim mekanizmasını değiştirmesidir.
- **Diff üst sınırı** (varsayılan 400 satır) — incelenemeyen değişiklik
  onaylanmış sayılmaz.
- **Gecede tek görev.** Bekleyen dal varken yeni koşu başlamaz.
- **Merge sonrası sağlık kontrolü.** Geçmezse birleştirme otomatik geri alınır.
- **Onaylamama günü** (varsayılan pazar) — o gün hiçbir şey merge edilmez.
  Bu döngünün en olası başarısızlığı teknik değil insani: raporu okumadan
  onaylamaya başlamak.

Ajanı sen tanımlarsın (`guard/ayar.conf` → `VENUS_AJAN`). Tanımlı değilse gece
koşusu görevi seçer, kopyayı ve rapor iskeletini hazırlar, kod yazmaz.

## Sonraki adım

Kod olarak sıradaki **Faz 3 — niyet çözücü**, ama önce iki şey gerekiyor:

1. **`kimlik.md` ve `kurallar.yaml` doldurulmalı** *(kullanıcı)*. İkisi de şu an taslak;
   kurallar.yaml'daki değerler örnektir, denetleyici onlara göre çalışır.
2. **Faz 2'nin bitiş kriteri:** jurnal bir hafta gerçekten kullanılmalı. Kullanılmıyorsa
   ileri gitmek ölü kod üretir — geri dönüp doğru yetenekleri bulmak gerekir.

Faz 3 ayrıca model kararına bağlıdır (şartname Bölüm 15: bulut API mi, lokal model mi).
