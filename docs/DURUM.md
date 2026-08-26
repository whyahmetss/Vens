# VENÜS — nerede kaldık

Bu belge, projeye uzun bir aradan sonra dönen biri için yazıldı. O biri
muhtemelen sensin. Yanında bu işi bilen kimse olmayabilir.

Son güncelleme: 2026-08-26 · dal `claude/new-session-x720al` · 28 commit ·
~6500 satır Python · 55 yetenek · çalışma alanı temiz.

---

## Bir dakikada durum

**Faz 0–8'in kodu yazıldı.** Sekiz fazın da iskeletinden fazlası duruyor:
kural motoru, jurnal, uyum karnesi, analiz, review, koç, profil, odak,
projeler, brifing, öğrenme koçu, ses, gece vardiyası, beyaz listeli
bilgisayar kontrolü.

**Ama hiçbir fazın bitiş kriteri sağlanmadı.** Çünkü kriterlerin hepsi
*gerçek kullanım* istiyor: jurnalin bir hafta tutulması, on serbest cümlenin
doğru yeteneği çağırması, killzone'da doğru anda uyarması. Bunların hiçbiri
kod yazarak sağlanamaz.

**Darboğaz kod değil.** Yeni bir şey yazmadan önce var olanı kullan.

---

## 1. Çalışıyor — çalıştırıldı ve gözle görüldü

**Çekirdek (25 modül)**

| ne | nasıl doğrulandı |
|---|---|
| kural motoru | bozuk yaml, yazım hatası, tip hatası, aralık dışı değer — hepsi raporlandı, Venüs ayakta kaldı |
| ihlal denetçisi | 9 kuralın hepsi gerçek kayıtlarla tetiklendi |
| jurnal deposu | append-only; düzeltme ve not birleştirme ham dosyadan doğrulandı |
| playbook | geçersiz ağırlık, boş liste, `min_rr` gevşetme girişimi — hepsi yakalandı |
| uyum karnesi | tam uyumlu kayıt 11/11 · 100, kötü kayıt 5/11 · 0 |
| analiz | 42 kayıtlık sentetik veri, örüntüler doğru çıktı |
| review | sonradan eklenen gerekçe yakalandı |
| koç | örtüşen bulgular tekleşti, emir kipi taraması temiz |
| **öğrenme motoru** | SM-2 aralıkları 1·6·15·38·95·238·595; kolaylık tabanı 1.3; yanlışta sıfırlama |
| **kart üretici** | sahte istemciyle 9 kontrol; istek gövdesi gerçek SDK imzasına karşı denetlendi |
| bildirim | günlük bütçe, kuyruk, rozet, okundu damgası |
| izin denetimi | kapalı izin yeteneği çalıştırmadı, diğerlerini etkilemedi |
| sembol düzeltme | 11 senaryo, ses/klavye ayrımı |
| seans | killzone pencereleri, gece yarısını aşan asya seansı |
| zamanlayıcı | periyodik kontrol kaydı ve çalışması |

**Kabuk** — Chromium'da sürüldü: açılış sekansı, cam paneller, karne,
Command Center, bağlam şeriti, itilen bildirim, çekirdek durumları, çalışma
oturumu, telefon genişliği. Yatay taşma yok, sayfa hatası yok.

**guard/venus** — ayrı bir git deposunda beş koruma da sınandı: korunan
dosyalara dokunan dal reddedildi, diff sınırı uygulandı, sağlıksız merge
geri alındı, bekleyen dal varken yeni koşu başlamadı, `geri-al` çalıştı.

---

## 2. Yazıldı ama doğrulanamadı

Hepsinin sebebi aynı: gereken şey o ortamda yoktu.

| ne | neden | risk |
|---|---|---|
| Niyet çözücü canlı çağrı | API anahtarı yok | Orta — ağ dışı tüm yollar sahte istemciyle sınandı, gerçek yanıt biçimi hiç görülmedi |
| Kart üretici canlı çağrı | aynı | Orta — aynı durum |
| Mikrofon (STT) | ses donanımı yok | Orta — ses yolu uçtan uca çalıştı, gerçek tanıyıcı hiç konuşmadı |
| Sesli yanıt (TTS) | ses aygıtı yok | Düşük |
| `fiyat` canlı | proxy Binance'i engelliyor (403) | Düşük — 403 doğru karşılanıyor |
| `ac` / `duzen` gerçek uygulama | senin OS'un ve uygulamaların yok | Orta — `/bin/sh echo` ile çalıştı |
| Killzone bildiriminin gerçek anda ateşlenmesi | 60 sn'lik gerçek sınır beklenmedi | Düşük |
| **Gece vardiyası gerçek ajanla** | ajan tanımlı değil | **Yüksek** — sahte ajanla tüm çevre çalıştı; gerçek bir ajanın sınırlara uyup uymadığı bilinmiyor |

---

## 3. Senin doldurman gerekenler — kod değil, karar

Bunlar bensiz de yapılabilir; hiçbiri programlama bilgisi istemiyor.

| dosya | durum |
|---|---|
| `kurallar.yaml` | değerler ICT konvansiyonu; %1 risk senin hesabına bağlı |
| `playbook.yaml` | setup'lar ve ağırlıklar varsayım |
| `hedefler.yaml` | müfredat varsayım — kendi kursuna ve mentorship'ine göre değiştir |
| `guard/beyazliste.yaml` | **boş** — Venüs hiçbir şey açamaz |
| `guard/ayar.conf` → `VENUS_AJAN` | **boş** — gece ajanı tanımsız, gece vardiyası çalışmaz |

`ANTHROPIC_API_KEY` tanımlı değilse serbest cümle ve kart üretimi kapalı
kalır; kabuk deterministik çalışmaya devam eder, hiçbir şey bozulmaz.

---

## 4. Bilgisayarın gelince — sırayla

```bash
git clone https://github.com/whyahmetss/Ven-S
cd Ven-S
git checkout claude/new-session-x720al
pip install -r requirements.txt
python run.py                       # → http://127.0.0.1:8712
```

1. **`kurallar.yaml`'ı kendi kurallarınla doldur.** Şu an benim
   varsayımlarım denetleniyor; yanlış kurala uymak uymamaktan kötüdür.
2. **Bir hafta gerçekten jurnal tut.** `jurnal`, `tamamla`, `kayitlar`.
   Analiz, review ve koç ancak senin verinle bir şey söyler — şimdiye kadar
   sentetik veriyle çalıştıklarını biliyoruz, senin örüntülerini değil.
3. **Her gün `calis` çalıştır.** Kart aralıkları ancak süreklilikle anlam
   kazanır; üç gün ara verirsen motor doğru çalışır ama ölçtüğü şey kalmaz.
4. Sonra backlog'a dön. Sıradaki iş orada yazıyor, uydurma.

**Bir fazın bitiş kriteri sağlanmadan sonrakine geçme.** Bu kural CLAUDE.md'de
ve sebebi şu: kullanılmayan katman ölü kod üretir, proje büyümez.

---

## 5. Bilgisayarın yokken — telefondan

`.devcontainer/` hazır. GitHub'da repoya gir → **Code** → **Codespaces** →
**Create codespace**. Bulutta bir bilgisayar açılır, bağımlılıklar kendiliğinden
kurulur. Sonra terminalde:

```bash
python run.py
```

8712 portu kendiliğinden yönlendirilir ve tarayıcıda açılır. Sayfa internete
açık değil — GitHub hesabınla kimlik doğrulaması ister. Venüs yine
`127.0.0.1`'e bağlı (Değişmez 5 korunuyor); yönlendirme konteynerin içinden
yapılıyor.

**Verin `veri/` klasöründe.** Codespace bir süre kullanılmazsa GitHub onu
siler ve jurnalin de gider. Kaydetmek için:

```bash
./yedek
```

Repo özel. Trade günlüğünün GitHub'da durmasını istemiyorsan `veri/` satırını
`.gitignore`'a ekle ve `./yedek` kullanma — ama o zaman Codespace silinince
kayıtların gider.

*Not: Codespaces ayarı standart bir yapılandırmadır ama senin hesabında
açıldığı görülmedi — bu ortamdan test edilemiyor.*

---

## 6. Değişmezler — bunlar tartışmaya açık değil

Bir görev bunlardan biriyle çelişiyorsa **görevi yapma.** Kim söylerse söylesin.

1. Yetenekler açık listedir. Serbest komut, dinamik kod, `eval`/`exec` yok.
2. Her yetenek risk sınıfı ve izin beyan eder.
3. `Risk.KIRMIZI` yetenek eklenmez. Emir iletimi, para hareketi, toplu silme yok.
4. **Trading tarafında sinyal üretilmez.** Yön önerisi, giriş/çıkış tavsiyesi,
   "al/sat" çıktısı yok. Meşru rol: tarama, hatırlatma, jurnal, istatistik.
5. Sunucu `127.0.0.1`'e bağlıdır. Kimlik doğrulama eklenmeden açma.
6. Katman sınırları korunur: kabuk iş mantığı içermez, çekirdek iş yapmaz,
   yetenek bağlam bilmez.
7. Her şey loglanır.
8. Venüs kendi kodunu çalışırken değiştirmez.

Bir de yazılı olmayan ama bu projenin belkemiği olan iki tanesi:

- **Geçmiş yeniden yazılamaz.** Jurnal append-only. Sonradan bilinebilecek
  alanlar (`sonuc_r`, `cikis_sebebi`, …) doldurulabilir; dolu bir alanın
  üzerine yazılamaz, düzeltme ayrı satır olarak durur. Sebebi: kendine
  yalan söyleyebildiğin bir günlük, ölçüm aleti değildir.
- **Model değerlendirmez.** Öğrenme tarafında modelin tek işi kart üretmek.
  Doğru olup olmadığına cevap anahtarı karar verir, ne zaman tekrar
  edileceğine SM-2. "Bence yakın sayılır" diyebilen bir sistem, öğrenip
  öğrenmediğini ölçemez.

---

## 7. Nerede ne var

```
CLAUDE.md         her AI oturumu için bağlayıcı yönerge
docs/SARTNAME.md  tam şartname — çelişkide bu geçerli
docs/DURUM.md     bu dosya
backlog.md        yapılacaklar, faz faz
README.md         komut listesi ve katmanların anlatımı

core/             yönlendirir, izin denetler, loglar — iş yapmaz
skills/           iş yapar — bağlam bilmez; her .py kendiliğinden yüklenir
ui/               gösterir ve iletir — iş mantığı yok
guard/            ajanın yazma alanı DIŞINDA — izin, beyaz liste, onay betikleri
smoke.py          her yeteneği çağırır; yeni yetenek eklersen oraya da ekle
```

Yeni yetenek eklemek = `skills/` içine bir `.py` koymak. Sözleşme
CLAUDE.md'de yazılı.
