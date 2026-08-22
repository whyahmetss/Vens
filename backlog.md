# Görev listesi

Claude Code bir oturumda **tek madde** alır. Faz 8'de gece vardiyası da buradan çeker.
Açık uçlu "kendini geliştir" hedefi verilmez — kaynak bu dosyadır.

---

## Faz 1 — kimlik ve kurallar

- [ ] `kimlik.md` doldurulacak *(kullanıcı yapar)*
- [ ] `kurallar.yaml` doldurulacak *(kullanıcı yapar)*
- [ ] `core/kurallar.py` — yaml okuyucu + doğrulayıcı
- [ ] `skills/kural.py` — `kurallar` komutu, aktif kuralları listeler
- [ ] Kural ihlali tespiti (deterministik, LLM yok)
- [ ] İhlaller `~/.venus/ihlaller.jsonl` dosyasına yazılır

## Faz 2 — jurnal

- [ ] `skills/jurnal.py` — kayıt ekleme, zorunlu alan kontrolü
- [ ] Jurnal listeleme ve tek kayıt görüntüleme
- [ ] Kayıt anında kural denetimi
- [ ] `jurnal istatistik` — R ortalaması, win rate, setup dağılımı
- [ ] Eksik jurnal hatırlatması

## Faz 3 — niyet çözücü

- [ ] Model seçimi *(kullanıcı kararı — bkz. şartname Bölüm 15)*
- [ ] `core/niyet.py` — `/yetenekler`den araç tanımı üretimi
- [ ] Liste dışı yetenek dönerse reddetme
- [ ] Kabukta serbest cümle girişi

## Faz 4 — ses

- [ ] Konuşmadan metne
- [ ] Metinden konuşmaya
- [ ] Uyandırma kelimesi (lokal)
- [ ] Sembol düzeltme katmanı (BTC → "bitisi" sorunu)

## Faz 5 — arayüz

- [ ] Bağlam panelleri
- [ ] Command Center ekranı
- [ ] Bildirim seviyeleri + günlük bütçe
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
