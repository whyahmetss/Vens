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

- [ ] Konuşmadan metne
- [ ] Metinden konuşmaya
- [ ] Uyandırma kelimesi (lokal)
- [ ] Sembol düzeltme katmanı (BTC → "bitisi" sorunu)

## Faz 5 — arayüz

- [ ] Bağlam panelleri
- [ ] Command Center ekranı
- [x] Bildirim seviyeleri + günlük bütçe
- [ ] Açılış sekansı iyileştirme

## Faz 6 — trading taraması

- [ ] Seans / killzone hatırlatıcı
- [ ] Seviye yaklaşma uyarısı
- [ ] HTF bias notu *(bilgi, öneri değil)*

## Faz 7 — bilgisayar kontrolü

- [ ] Beyaz liste tanımı
- [ ] Uygulama / sayfa açma
- [ ] Çalışma alanı düzeni

## Faz 8 — gece vardiyası

- [ ] `guard/` dizini ve izin ayrımı
- [ ] Gece dalı + rapor üretimi
- [ ] `onayla` / `reddet` / `ertele` / `geri-al` betikleri
- [ ] Açılış sağlık kontrolü + otomatik geri dönüş
- [ ] `GELISIM.md` günlüğü

---

## Fikirler *(sıralanmamış, faz atanmamış)*

-
