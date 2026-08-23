# Görev listesi

Claude Code bir oturumda **tek madde** alır. Faz 8'de gece vardiyası da buradan çeker.
Açık uçlu "kendini geliştir" hedefi verilmez — kaynak bu dosyadır.

---

## Faz 1 — kimlik ve kurallar

- [x] `kimlik.md` doldurulacak — hitap kararı verildi, çözücünün okumadığı not edildi
- [x] `kurallar.yaml` doldurulacak — ICT yerleşik değerleri, her satır gerekçeli
- [x] `core/kurallar.py` — yaml okuyucu + doğrulayıcı
- [x] `skills/kural.py` — `kurallar` komutu, aktif kuralları listeler
- [x] Kural ihlali tespiti (deterministik, LLM yok)
- [x] İhlaller `~/.venus/ihlaller.jsonl` dosyasına yazılır

## Faz 2 — jurnal

- [x] `skills/jurnal.py` — kayıt ekleme, zorunlu alan kontrolü
- [x] Jurnal listeleme ve tek kayıt görüntüleme
- [x] Kayıt anında kural denetimi
- [x] `istatistik` — R ortalaması, win rate, setup dağılımı
- [x] Eksik jurnal hatırlatması

## Faz 3 — niyet çözücü

- [x] Model seçimi — görev başına tablo, `core/model.py` *(kullanıcı kararı)*
- [x] `core/niyet.py` — `/yetenekler`den araç tanımı üretimi
- [x] Liste dışı yetenek dönerse reddetme
- [x] Kabukta serbest cümle girişi

## Faz 4 — ses

- [x] Konuşmadan metne — bas-konuş (tarayıcı)
- [x] Metinden konuşmaya — tarayıcıda yerel, KRİTİK/YÜKSEK bildirimler
- [ ] Uyandırma kelimesi (lokal) — **yapılmadı:** tarayıcı tanıması sesi buluta
      yollar, sürekli açık bırakmak Bölüm 8'i çiğner. Lokal bir uyandırma
      motoru (openWakeWord vb.) gerekir — yeni bağımlılık, kullanıcı kararı.
- [x] Sembol düzeltme katmanı (BTC → "bitisi" sorunu)

## Faz 5 — arayüz

- [x] Bağlam panelleri — bağlam şeriti, söylenecek şey varsa belirir
- [x] Command Center ekranı — `merkez`, ESC ile kapanır
- [x] Bildirim seviyeleri + günlük bütçe
- [x] Açılış sekansı iyileştirme — satırlar gerçek durumu ölçer

## Faz 6 — trading taraması

- [x] Seans / killzone hatırlatıcı *(sinyal değil, hatırlatma)*
- [x] Seviye yaklaşma uyarısı — kullanıcının işaretlediği seviyeler
- [x] HTF bias notu — kullanıcı yazar, Venüs saklar *(Değişmez 4)*

## Faz 7 — bilgisayar kontrolü

- [x] Beyaz liste tanımı — `guard/beyazliste.yaml`
- [x] Uygulama / sayfa açma — `ac <ad>`, yalnızca listedekiler
- [x] Çalışma alanı düzeni — `duzen <ad>`

## Faz 8 — gece vardiyası

- [x] `guard/` dizini ve izin ayrımı — izin ve beyaz liste dosyaları orada
- [ ] Gece dalı + rapor üretimi
- [ ] `onayla` / `reddet` / `ertele` / `geri-al` betikleri
- [ ] Açılış sağlık kontrolü + otomatik geri dönüş
- [ ] `GELISIM.md` günlüğü

---

## Fikirler *(sıralanmamış, faz atanmamış)*

-
