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
- [x] `tamamla` — açık pozisyonu kapatma / kayıt düzeltme (append-only)

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
- [x] Gece dalı + rapor üretimi — `guard/gece`, lab/ worktree
- [x] `onayla` / `reddet` / `ertele` / `geri-al` betikleri — `guard/venus`
- [x] Açılış sağlık kontrolü + otomatik geri dönüş — `guard/venus baslat`
- [x] `GELISIM.md` günlüğü

---

## Trading katmanları *(Memory → Journal → Compliance → Analytics → Review → Coach)*

- [x] `playbook.yaml` — setup tanımları, kontrol listeleri, ceza ağırlıkları
- [x] Genişletilmiş jurnal alanları (SL/TP, HTF, likidite, çıkış sebebi, etiket, görsel)
- [x] Uyum karnesi + kalite skoru (`core/karne.py`)
- [x] Geçmiş yeniden yazılamaz — ORIGINAL / POST-TRADE NOTE ayrımı
- [x] **Analytics** — setup × seans × sembol × RR kırılımı, kalite skoru →
      sonuç korelasyonu, tekrarlanan davranışlar ve birleşik R etkisi
- [x] **Review** — plan ↔ gerçek karşılaştırması, sonradan eklenen gerekçe tespiti
- [x] **Coach** — sabit şablonlu sorgulama, LLM yok *(kullanıcı kararı)*

## Çalışma ortamı *(şartname Bölüm 0 ve 7)*

- [x] Kalıcı profil — hafıza Aşama 3, gizli hafıza yok
- [x] Çalışma / odak katmanı — `calisma` bölümünün dedektörleri
- [x] Projeler alanı — "dün nerede kaldım"
- [x] Sabah brifingi + gün kapanışı
- [ ] **Finans alanı** — Bölüm 7'nin saydığı dördüncü alan, hiç yok
- [ ] Odak ↔ jurnal bağı — trading seansı da bir odak seansı mı?

## Öğrenme koçu *(hedef: 1 ayda İngilizce A2, 2 ayda ICT mentorship)*

- [x] Aralıklı tekrar motoru — SM-2, deterministik cevap denetimi (`core/ogrenme.py`)
- [x] Hedefler ve tempo — gereken hız ↔ fiili hız (`core/hedef.py`, `hedefler.yaml`)
- [x] Çalışma oturumu — `calis` / `cevap`; denemeden not vermek engellendi
- [x] Kart üretici — modelin tek işi kart yazmak, değerlendirme ona dönmez
- [x] Model kartı işareti — `[model]` + ilk sorulduğunda "cevap yanlışsa sil"
- [ ] **Müfredatı gerçek kursuna göre doldur** — `hedefler.yaml`'daki üniteler varsayım
- [ ] Bir hafta gerçekten kullan — tempo ve olgunluk ancak o zaman bir şey söyler
- [ ] Odak seansı ↔ çalışma oturumu bağı: `calis` bir odak seansı sayılmalı mı?

## Fikirler *(sıralanmamış, faz atanmamış)*

-
