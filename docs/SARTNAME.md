# VENÜS — Kişisel AI Çalışma Ortamı
### Şartname v2 · Ağustos 2026

---

## 0. TANIM

Venüs, kullanıcının makinesinde yaşayan, kullanıcıyı tanıyan ve zamanla öğrenen kişisel bir AI çalışma ortamıdır.

**Ne değildir:** chatbot, trading botu, admin paneli, klasik dashboard, Siri kopyası.

**Tek cümlelik hedef:** Kullanıcı bir uygulama açmaz — Venüs'ü uyandırır.

**Bu bir hobi projesidir.** Ticari değil, kullanıcı sayısı bir. Bu, mimari kararların çoğunu basitleştirir ve doküman boyunca böyle varsayılır.

---

## 1. TASARIM İLKELERİ

Bu bölüm dokümanın omurgasıdır. İki madde çeliştiğinde buraya bakılır.

**İ1 — Çalışan küçük, mükemmel büyükten iyidir.**
Her fazın sonunda kullanılabilir bir şey olmalı. "Altyapıyı kuruyorum" fazı bir haftayı geçmez.

**İ2 — Yetenekler daima açık listedir.**
Venüs asla "ne isterse yapabilen" bir şey olmaz. Her yetenek elle yazılır, elle kaydedilir. Model yetenek uydurabilir; sistem uydurulmuş yeteneği çalıştıramaz.

**İ3 — Geri dönülemez işlem onay ister.**
Bkz. Bölüm 2. Bu ilke hiçbir koşulda esnetilmez.

**İ4 — Log önce, hafıza sonra.**
Neyin hatırlanacağını kullanım gösterir. Hafıza mimarisi baştan tasarlanmaz, biriken logdan türetilir.

**İ5 — Sessizlik varsayılandır.**
Ekran normalde boş. Bildirim normalde yok. Bilgi ancak istendiğinde veya gerçekten önemli olduğunda gelir.

**İ6 — Nihai karar her zaman kullanıcınındır.**
Venüs kuralları hatırlatır, uygulamayı zorlamaz.

**İ7 — Sistemi geliştiren araç, sistemin parçası değildir.**
Kod yazma işi Claude Code'a aittir ve Venüs'ün dışındadır. Venüs kendi kodunu çalışırken değiştirmez.

---

## 2. OTONOMİ VE GERİ DÖNÜLEBİLİRLİK

Her yetenek, zorluğuna göre değil **yanlış çalıştığında ne kaybettirdiğine** göre sınıflanır. Sınıf, o yeteneğin ne kadar serbest çalışacağını belirler.

| Sınıf | Anlamı | Örnek | Davranış |
|---|---|---|---|
| **YEŞİL** | Geri dönülebilir / zararsız | okuma, arama, özet, fiyat sorgusu, not | Onaysız çalışır |
| **SARI** | Geri dönülebilir ama iz bırakır | dosya oluşturma, uygulama açma, git commit | Çalışır, logda görünür |
| **TURUNCU** | Zor geri alınır | dosya silme/taşıma, terminal komutu, mesaj gönderme | Her seferinde onay |
| **KIRMIZI** | Geri alınamaz | emir iletimi, para hareketi, toplu silme | v1'de **yok** |

**Kural:** Kırmızı sınıf hiçbir zaman LLM çıktısına bağlanmaz. Bu sınıfa bir yetenek eklenecekse LLM değil, deterministik kod tetikler.

---

## 3. MİMARİ

Sekiz kutulu "core" yerine üç katman. Sebep: sekiz kutu sekiz boş klasör üretir, üç katman çalışan bir sistem üretir.

```
KABUK (arayüz)
  ekran · ses girişi · ses çıkışı · komut satırı
        ↕ websocket
ÇEKİRDEK (yönlendirme)
  niyet çözücü · yetenek kayıt defteri · izin denetimi · log
        ↕
YETENEKLER (iş yapan kod)
  trading · jurnal · not · araştırma · sistem · dosya · takvim
```

**Katmanların sorumluluğu keskin ayrılır:**
- Kabuk aptaldır. Sadece gösterir ve iletir. İş mantığı içermez.
- Çekirdek karar verir ama iş yapmaz. Hangi yetenek, hangi parametre, izin var mı.
- Yetenekler iş yapar ama bağlam bilmez. Girdi alır, çıktı verir.

Bu ayrım korunursa; arayüz değişse, model değişse, ses eklense mimari bozulmaz.

**Ajan kavramı:** "Trading Agent", "Coding Agent" gibi ayrı süreçler v1'de yoktur. Bunlar yetenek gruplarının etiketidir. Gerçek çoklu ajan mimarisi, tek katman yetersiz kaldığında eklenir — önce değil.

---

## 4. KİMLİK

Venüs'ün karakteri kodda değil, düz metin bir kimlik dosyasındadır. Değiştirmek dosyayı düzenlemektir.

**Karakter:**
- Sakin, kısa, profesyonel. Gereksiz nezaket yok.
- Onaylayıcı değil. Kullanıcıyı memnun etmek görevi değildir.
- Kullanıcının kendi koyduğu kuralların bekçisi.
- Emin olmadığında emin değilim der. Uydurmaz.

**Referans diyalog (kalibrasyon için):**

> — Bugün bir trade daha açacağım.
> — Günlük limitini zaten aştın.
> — Son bir tane.
> — O zaman kendi kuralını çiğniyorsun. Karar senin.

Son cümle önemli: hatırlatır, sonra çekilir. Israr etmez, moralize etmez.

**Dil:** Tek dil seçilir ve tutarlı kullanılır. Karma dil kişiliği bulanıklaştırır. → *Açık karar, Bölüm 14.*

---

## 5. KURALLAR MOTORU

**Bu sistemin çekirdek değeridir.** Hazır hiçbir araçta olmayan tek şey budur; çünkü kurallar kullanıcıya özeldir.

Kullanıcının kendi koyduğu kurallar makine-okunur bir dosyada tutulur:

```yaml
gunluk_islem_limiti: 2
maks_risk_yuzde: 1.0
min_rr: 2.0
izinli_seanslar: [londra, new_york_am]
zorunlu_alanlar: [setup, giris_sebebi, duygu]
yasak: 
  - stop_genisletme
  - kayip_sonrasi_30dk_islem
```

Venüs her jurnal kaydında bu kurallara karşı kontrol eder ve **ihlali kaydeder** — engellemez, kaydeder. Uzun vadede en değerli veri budur: hangi kuralı, hangi durumda, ne sıklıkla çiğniyorsun.

Kurallar motoru LLM'e bağlı değildir. Deterministik kod, deterministik sonuç.

---

## 6. YETENEK SÖZLEŞMESİ

Yeni yetenek eklemek tek bir şey olmalı: bir fonksiyon yazmak.

Her yetenek şunları beyan eder:
- **ad** ve kullanıcıya görünen açıklama
- **parametreler** (tipli)
- **risk sınıfı** (Bölüm 2)
- **gerekli izinler** (Bölüm 9)

Kayıt defteri bu beyanlardan iki şey üretir: kullanıcıya gösterilen yardım listesi, ve niyet çözücüye verilen araç tanımları. Yani yetenek listesi tek yerde yaşar, iki yerde tekrar edilmez.

---

## 7. HAFIZA

İ4 gereği hafıza **fazlara yayılır**, baştan üç katman kurulmaz.

**Aşama 1 — Log.** Her etkileşim düz dosyaya (jsonl) yazılır. Hafıza yok, sadece kayıt. Bu tek başına şaşırtıcı derecede iş görür.

**Aşama 2 — Yapılandırılmış kayıt.** Jurnal, notlar, kurallar, proje bilgileri ayrı dosyalarda. Sorgulanabilir ama "hatırlama" yok — arama var.

**Aşama 3 — Kalıcı profil.** Kullanıcı hakkında öğrenilenler ayrı bir dosyada birikir: tercihler, çalışma şekli, tekrarlayan hatalar. **Her kayıt kullanıcı tarafından görülebilir, düzenlenebilir, silinebilir.** Gizli hafıza yok.

**Aşama 4 — Anlamsal geri getirme.** Ancak dosyalar elle taranamayacak kadar büyüdüğünde. Muhtemelen aylar sonra, belki hiç.

Proje bazlı ayrım (trading / projeler / finans / kişisel) Aşama 2'den itibaren klasör düzeyinde uygulanır.

---

## 8. SES

Ses bir **giriş yöntemidir**, yetenek değildir. Sistemin ne yapabildiğini değiştirmez.

**Zincir:** uyandırma kelimesi → konuşmadan metne → niyet çözme → yetenek → metinden konuşmaya

**Bilinen zorluklar:**
- Uyandırma kelimesi kısa ve yaygın hecelerden oluşursa yanlış tetiklenir. "Venüs" yerine "Hey Venüs" tercih edilir.
- Türkçe konuşma tanıma sembolleri bozar (BTC → "bitisi"). Bu yüzden niyet çözücü serbest metne değil, kapalı yetenek listesine eşler.
- Sürekli açık mikrofon + her cümleyi buluta yollama = pil ve fatura. Uyandırma kelimesi lokal çalışmalıdır.
- Gerçekçi gecikme: 2–3 saniye. Film hissi olmayacak.

Sesli cevap doğal olmalı, komut okuyucu gibi değil.

---

## 9. BİLGİSAYAR KONTROLÜ

Sistemin **en riskli** bölümü. Bu yüzden fazlarda en sonda.

**İzin modeli:** OKUMA · YAZMA · ÇALIŞTIRMA · SİLME · TARAYICI · İLETİŞİM

Her yetenek hangi izinlere ihtiyaç duyduğunu beyan eder. Kullanıcı izinleri tek ekrandan görür ve kapatabilir.

**v1 kapsamı (beyaz listeli):** kayıtlı uygulamayı açma, kayıtlı sayfayı açma, tanımlı çalışma alanı düzeni kurma, dosya okuma, dosya oluşturma.

**v1 kapsamı dışı:** serbest terminal komutu, klavye/mouse simülasyonu, dosya silme/taşıma, uygulama kapatma.

Sebep: serbest terminal + mouse kontrolü, sistemi asistan olmaktan çıkarıp makinede tam yetkili bir sürece dönüştürür. Bu yetki, aylarca güvenilir çalışmayla hak edilir.

**Çalışma alanı örneği** (izinli, deterministik):
> "Venüs, trading ortamımı aç" → TradingView + ilgili sembol + jurnal + haber ekranı, tanımlı pencere düzeninde.

---

## 10. TRADING MODÜLÜ

Bir yetenek grubudur, sistemin merkezi değildir.

**Kapsam:** ICT/SMC çerçevesine göre tarama, işaretleme, hatırlatma, jurnal.
İzlenen kavramlar: likidite (BSL/SSL), EQH/EQL, BOS, CHoCH, MSS, FVG, order block, OTE, killzone, HTF bias, haber, R:R.

**Kesin sınır:** Venüs sinyal üretmez, emir iletmez, yön önermez.

Sebep teknik değil epistemiktir: dil modeli en makul görünen açıklamayı üretmek üzere eğitilmiştir. Grafiğe bakıp "sweep oldu, FVG'ye dönüş bekliyorum" diyen ikna edici bir metin üretir — ve bu metnin gerçekten yapıyı görmekten mi, yoksa örüntü tamamlamaktan mı geldiği **logdan ayırt edilemez**. Kullanıcı zamanla modelin gerekçesini kendi tezi sanmaya başlar. Kaybedilen şey paradan önce yargıdır.

**Venüs'ün trading'de meşru rolü:** hazırlık (seans başladı, seviye yaklaştı), disiplin (limit aşıldı, jurnal eksik), analiz (geçmiş performans).

---

## 11. JURNAL

Her işlem kaydı:

```
XAUUSD · 18 AUG 2026 · +2.4R
SETUP     : Liquidity Sweep → MSS → FVG
SEANS     : London
GİRİŞ     : OTE 0.705
EXECUTION : iyi
DUYGU     : sabırsız
KURAL     : ✓ limit  ✓ risk  ✗ erken çıkış
VENÜS     : "Giriş geçerliydi. Çıkış erkendi."
```

**Zamanla üretilecek analizler:** en iyi/en kötü setup, en kârlı seans, en sık hata, erken giriş oranı, revenge trading, overtrading, stop değiştirme sıklığı, model uyumu, ortalama R, win rate, expectancy.

Bunlar için tek gereksinim: **yeterli sayıda dolu kayıt.** Analiz kodu bir günlük iş; veri aylar alır. Bu yüzden jurnal ilk fazlardadır.

---

## 12. PROAKTİFLİK

Venüs komut beklemeden konuşabilir. Ama bir **bildirim bütçesi** vardır — aşılırsa kullanıcı sistemi susturur ve proje ölür.

| Seviye | Ne zaman | Nasıl |
|---|---|---|
| KRİTİK | Kural ihlali anı, sistem sorunu | Kesintili, sesli |
| YÜKSEK | Killzone başlangıcı, toplantı | Görsel + kısa ses |
| NORMAL | Jurnal eksik, hatırlatma | Sessiz rozet |
| DÜŞÜK | Bilgi | Sadece log |

**Günlük bütçe:** en fazla 3 KRİTİK+YÜKSEK. Aşılırsa kuyruğa alınır.

---

## 13. ARAYÜZ

**Varsayılan durum minimal:** Venüs çekirdeği, saat/tarih, sistem durumu, aktif görev, bildirim sayısı. Başka hiçbir şey.

Paneller **bağlama göre** açılır, hep açık durmaz. Kullanıcı konuştuğunda arayüz canlanır.

**Palet:** siyah · koyu gri · beyaz · neon yeşil `#00FF41`
Neon yeşil vurgu rengidir — durum, aktif eleman, uyarı. Gövde metni değil.

**Dil:** holografik HUD, cam paneller, tarama efektleri, terminal tipografisi, sinematik açılış sekansı, yumuşak geçişler. Iron Man kopyası değil, özgün estetik.

**Command Center** (aktif görev, agent durumu, piyasa, son aktiviteler, hafıza, bildirimler, sistem) ayrı bir ekrandır ve **çağrılınca** açılır.

**Erişilebilirlik:** hareket azaltma tercihi olan sistemlerde animasyonlar kapanır.

---

## 14. FAZ PLANI

Her faz **bitiş kriteri** ile tanımlıdır. Kriter sağlanmadan sonraki faza geçilmez.

**FAZ 0 — Temel** *(1 akşam)*
Repo, kabuk, çekirdek, websocket köprüsü, 3 yetenek, log.
✅ *Bitti:* Komut yazılıyor, gerçek çıktı geliyor, her şey loglanıyor.

**FAZ 1 — Kimlik ve kurallar** *(1 akşam)*
Kimlik dosyası, kurallar dosyası, kural denetleyici.
✅ *Bitti:* Kural ihlali tespit ediliyor ve karakterine uygun dille söyleniyor.

**FAZ 2 — Jurnal** *(2 akşam)*
Kayıt, listeleme, kural kontrolü, temel istatistik.
✅ *Bitti:* Bir hafta boyunca gerçekten kullanılıyor. **Kullanılmıyorsa ilerlenmez.**

**FAZ 3 — Niyet çözücü** *(1–2 akşam)*
Serbest cümle → yetenek çağrısı. Yetenek listesi kapalı.
✅ *Bitti:* "Dünkü işlemleri göster" gibi 10 farklı cümle doğru yeteneği çağırıyor.

**FAZ 4 — Ses** *(2 akşam)*
Konuşmadan metne, metinden konuşmaya, uyandırma kelimesi.
✅ *Bitti:* "Hey Venüs" → cevap → yetenek çalışıyor, klavyeye dokunulmadan.

**FAZ 5 — Arayüz** *(sürekli)*
HUD, paneller, açılış sekansı, bağlam farkındalığı.
✅ *Bitti:* Kriter yok — bu faz hiç bitmez, keyif için yapılır.

**FAZ 6 — Trading taraması** *(2–3 akşam)*
Seans hatırlatma, seviye uyarısı, HTF bias notu.
✅ *Bitti:* Killzone başlangıcında doğru zamanda uyarıyor.

**FAZ 7 — Bilgisayar kontrolü** *(beyaz listeli)*
Çalışma alanı açma, uygulama/sayfa başlatma.
✅ *Bitti:* Tek komutla trading ortamı kuruluyor.

**FAZ 8 — Gece vardiyası (kendini geliştirme)** *(kapsamlı, bkz. Bölüm 18)*
Venüs, kullanıcı yokken kendi kod tabanı üzerinde çalışır; sabah rapor sunar, onay alırsa güncelleme uygulanır.
✅ *Bitti:* Bir hafta boyunca her sabah okunabilir bir rapor geliyor ve en az bir değişiklik onaylanıp sorunsuz uygulanmış oluyor.

**FAZ 9+ — Hafıza katmanları, otomasyon, çoklu cihaz**
İhtiyaç doğduğunda. Önce değil.

---

## 15. AÇIK KARARLAR

Bunlar kararlaşmadan Faz 3'e geçilemez:

1. **Model:** Bulut API (akıllı, internet şart, token maliyeti) mi, lokal model (bedava, offline, Türkçe'de daha zayıf) mi?
2. **Dil:** Venüs Türkçe mi konuşur, İngilizce mi? Karma olmayacak.
3. **Erişim:** Sadece bu makine mi, telefondan da erişilecek mi? İkincisi ise servis sürekli açık kalır ve kimlik doğrulama gerekir.
4. **Uyandırma kelimesi:** "Hey Venüs" onaylanıyor mu?
5. **Paketleme:** Tarayıcı yeterli mi, masaüstü uygulaması (Tauri/Electron) şart mı?

---

## 16. v1 KAPSAM DIŞI

Bilinçli olarak ertelenenler — unutulduğu için değil:

- Çoklu ajan orkestrasyonu (tek katman yeterli olduğu sürece)
- Anlamsal hafıza / vektör veritabanı
- Serbest terminal komutu ve klavye/mouse kontrolü
- Otomatik emir iletimi (v1'de **asla**)
- Mobil, saat, kulaklık istemcileri
- Çoklu kullanıcı, kimlik doğrulama, dağıtım
- Venüs'ün kendi kodunu **çalışırken** değiştirmesi (öneri döngüsü için bkz. Bölüm 18)

---

## 17. BAŞARI ÖLÇÜSÜ

Bu proje şu olduğunda başarılıdır:

**Kullanıcı, Venüs'ü kullanmayı hatırlamak zorunda kalmadığında.**

Özellik sayısı, kod satırı veya arayüzün güzelliği ölçü değildir. Ölçü, sistemin günlük akışın parçası haline gelmesidir. Bu olmuyorsa yanlış yetenekler seçilmiştir — daha fazla özellik değil, geri dönüp doğru üç işi bulmak gerekir.

---

## 18. GECE VARDİYASI

Venüs'ün kendi kod tabanını geliştirmesi. **Faz 8'den önce açılmaz** — çünkü bu döngünün güvenliği, önceki fazlarda oturmuş bir log, test ve izin altyapısına dayanır.

İ7 ilkesi burada güncellenir: Venüs kendi kodunu **çalışırken** değiştirmez, ama **ayrı bir kopya üzerinde çalışıp değişiklik önerebilir.**

### 18.1 Üç dizin

```
venus/        ← çalışan sürüm. Ajan için SALT OKUNUR.
lab/          ← ajanın çalışma kopyası. Tek yazabildiği yer.
guard/        ← onay, geri alma, sağlık kontrolü betikleri.
                Ajanın erişimi YOK. Kurallar ve izin dosyaları burada.
```

**Bu ayrım sistemin tek güvenlik dayanağıdır.** Asıl risk ajanın hatalı kod yazması değil, kendi denetim mekanizmasını değiştirmesidir. `guard/` ajanın dünyasının dışındadır.

### 18.2 Gece döngüsü

1. **Görev çekme.** Ajan `backlog.md` dosyasından **tek** madde alır. "Kendini geliştir" gibi açık uçlu hedef verilmez — yönsüz ajan iş uydurur.
2. **Çalışma.** `lab/` içinde, `night/YYYY-MM-DD` dalında. Süre ve token bütçesi sınırlı.
3. **Kanıt üretme.** Değişiklik için test yazar, çalıştırır, çıktıyı kaydeder.
4. **Rapor.** `raporlar/YYYY-MM-DD.md` dosyasına yazar:
   - Hangi görev, neden bu yaklaşım
   - Değişen dosyalar ve satır sayısı
   - **Nasıl kanıtladı** — test çıktısı, öncesi/sonrası davranış
   - Emin olmadığı noktalar
   - Denenip vazgeçilen yollar

### 18.3 Sabah döngüsü

```
guard/venus onayla   → dal merge edilir, servis yeniden başlar
guard/venus reddet   → dal silinir, sebep backlog'a not düşülür
guard/venus ertele   → dal kalır, yarın devam edilir
guard/venus geri-al  → son bilinen iyi commit'e döner
```

`geri-al` komutu **Venüs'ün içinde değildir.** Venüs açılmadığında da çalışması gerekir; sistemin bozulduğu an tam olarak ona ihtiyaç duyulan andır.

### 18.4 Otomatik güvenlik ağı

- **Açılış sağlık kontrolü:** her başlatmada temel testler koşar. Geçemezse Venüs otomatik olarak son iyi sürüme döner ve kullanıcıyı bilgilendirir.
- **Her gün ayrı geri dönüş noktası.** Tek "dünkü yedek" değil — iki gün sonra fark edilen bir hata da geri alınabilir.
- **Diff üst sınırı.** Belirlenen satır sayısını aşan öneri otomatik reddedilir. Sebep: incelenemeyen değişiklik onaylanmış sayılmaz.
- **Gecede tek görev.** Aynı sebep.

### 18.5 Ajanın dokunamayacakları

- `guard/` dizininin tamamı
- İzin sistemi ve risk sınıfı tanımları (Bölüm 2, 9)
- Kurallar dosyası (Bölüm 5)
- Kırmızı sınıf yetenekler
- Kendi bütçe ve sınır ayarları
- Dış ağa yazma (API çağrısı, mesaj, commit push)

### 18.6 Onay tiyatrosu tehlikesi

Bu döngünün en olası başarısızlığı teknik değil insani: kullanıcı bir süre sonra raporu okumadan onaylamaya başlar. O noktada kod tabanı, kimsenin okumadığı ve kimsenin anlamadığı bir yığına dönüşür.

Karşı önlemler: tek görev, sınırlı diff, kanıt zorunluluğu — ve haftada bir **"onaylamama günü"**: hiçbir şey merge edilmez, sadece geriye dönüp birikmiş değişiklikler okunur.

### 18.7 Gelişim günlüğü

Her onaylanan değişiklik `GELISIM.md` dosyasına tek satır düşer. Bu dosya Venüs'ün kendi biyografisidir: ne zaman ne öğrendi, hangi yeteneği kazandı, hangi hatayı düzeltti.

Uzun vadede projenin en keyifli çıktısı bu olacaktır.
