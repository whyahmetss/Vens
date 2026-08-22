# VENÜS — proje yönergesi

Bu dosya, bu repoda çalışan her AI oturumu için bağlayıcıdır.
Tam şartname: `docs/SARTNAME.md`. Çelişki halinde şartname geçerlidir.

---

## Proje nedir

Kullanıcının makinesinde yaşayan kişisel AI çalışma ortamı. Tek kullanıcılı, hobi projesi.
Chatbot değil, trading botu değil, dashboard değil.

**Şu an:** Faz 0 tamamlandı. Deterministik kabuk çalışıyor, yapay zekâ henüz yok.

---

## Değişmezler

Bunlar tartışmaya açık değildir. Bir görev bunlardan biriyle çelişiyorsa **görevi yapma, kullanıcıya sor.**

1. **Yetenekler açık listedir.** Serbest komut çalıştırma, dinamik kod üretip çalıştırma, `eval`/`exec` yok. Model yetenek uydurabilir; sistem uydurulmuş yeteneği çalıştıramaz.
2. **Her yetenek risk sınıfı ve izin beyan eder.** Beyansız yetenek eklenmez.
3. **`Risk.KIRMIZI` yetenek eklenmez.** Emir iletimi, para hareketi, toplu silme — v1'de yok. Kayıt defteri zaten reddediyor, bu korumayı kaldırma.
4. **Trading tarafında sinyal üretilmez.** Yön önerisi, giriş/çıkış tavsiyesi, "al/sat" çıktısı yok. Meşru rol: tarama, hatırlatma, jurnal, istatistik.
5. **Sunucu `127.0.0.1`'e bağlıdır.** Kimlik doğrulama eklenmeden `0.0.0.0`'a açma.
6. **Katman sınırları korunur.** Kabuk iş mantığı içermez. Çekirdek iş yapmaz. Yetenek bağlam bilmez.
7. **Her şey loglanır.** Yeni yetenek eklerken log çağrısını atlama.
8. **Venüs kendi kodunu çalışırken değiştirmez.** (Faz 8'deki öneri döngüsü ayrı ve `guard/` korumalıdır.)

---

## Mimari

```
KABUK (ui/)          gösterir ve iletir — iş mantığı yok
      ↕ websocket
ÇEKİRDEK (core/)     yönlendirir, izin denetler, loglar — iş yapmaz
      ↕
YETENEKLER (skills/) iş yapar — bağlam bilmez
```

Yeni dosya eklerken bu üçünden hangisine ait olduğuna karar ver. Arada kalıyorsa muhtemelen yanlış bölünmüştür.

---

## Yetenek sözleşmesi

```python
from core.registry import Risk, Perm, skill, satir, bilgi, uyari

@skill("ad", "kısa açıklama", Risk.YESIL,
       izinler=(Perm.OKUMA,), kullanim="ad <arg>", takma_adlar=("a",))
async def _ad(arg: str):
    return [satir("çıktı")]
```

`skills/` içindeki her `.py` otomatik yüklenir. Kayıt için ekstra işlem gerekmez.

**Risk sınıfı seçimi** — zorluğa göre değil, *yanlış çalışırsa ne kaybettirdiğine* göre:

| sınıf | anlam | örnek |
|---|---|---|
| `YESIL` | geri dönülebilir / zararsız | okuma, arama, hesap |
| `SARI` | iz bırakır | dosya oluşturma, kayıt yazma |
| `TURUNCU` | zor geri alınır → onay ister | silme, taşıma, mesaj gönderme |
| `KIRMIZI` | geri alınamaz | **yasak** |

Emin değilsen bir üst sınıfı seç.

---

## Faz planı

Sıra bağlayıcıdır. Bir fazın bitiş kriteri sağlanmadan sonrakine geçme.

| faz | iş | bitiş kriteri |
|---|---|---|
| 0 ✅ | iskelet, kayıt defteri, köprü, log | komut → gerçek çıktı → log |
| 1 | kimlik + kurallar + ihlal denetleyici | kural ihlali tespit ediliyor ve karaktere uygun söyleniyor |
| 2 | jurnal (kayıt, listeleme, istatistik) | **bir hafta gerçekten kullanılıyor** |
| 3 | niyet çözücü (LLM) | 10 farklı serbest cümle doğru yeteneği çağırıyor |
| 4 | ses (STT / TTS / uyandırma) | klavyeye dokunmadan komut çalışıyor |
| 5 | arayüz (HUD, paneller, bağlam) | bitiş kriteri yok, sürekli |
| 6 | trading taraması | killzone başlangıcında doğru zamanda uyarıyor |
| 7 | bilgisayar kontrolü (beyaz listeli) | tek komutla çalışma ortamı kuruluyor |
| 8 | gece vardiyası | bir hafta okunabilir rapor + en az bir onaylı değişiklik |

**Faz 2'nin kriteri özellikle önemlidir.** Jurnal kullanılmıyorsa ileri gitmek projeyi büyütmez, sadece ölü kod üretir. O durumda geri dön ve doğru yetenekleri bul.

---

## Faz notları

**Faz 1** — `kimlik.md` ve `kurallar.yaml` zaten repoda, doldurulmayı bekliyor.
Kural denetleyici **deterministik koddur**, LLM'e sorulmaz.

**Faz 3** — Niyet çözücüye "ne yapayım" sorulmaz, "hangi yeteneği hangi parametreyle çağırayım" sorulur. Araç tanımları `/yetenekler` endpoint'inden üretilir, elle tekrar yazılmaz. Model listede olmayan bir şey döndürürse çağrı reddedilir.

**Faz 4** — Uyandırma kelimesi lokal çalışmalı; sürekli açık mikrofonu buluta bağlama. Türkçe konuşma tanıma sembolleri bozar (BTC → "bitisi"), bu yüzden serbest metne değil kapalı yetenek listesine eşlenir.

**Faz 6** — Sinyal değil hatırlatma. Bkz. Değişmez 4.

**Faz 7** — Beyaz liste: kayıtlı uygulama açma, kayıtlı sayfa açma, çalışma alanı düzeni, dosya okuma/oluşturma.
**Kapsam dışı:** serbest terminal komutu, klavye/mouse simülasyonu, dosya silme/taşıma.

**Faz 8** — `guard/` dizini ajanın yazma alanı dışındadır. Onay betikleri, geri alma betiği, izin ve kural dosyaları oradadır. Gece çalışması `backlog.md`'den **tek** görev çeker; açık uçlu "kendini geliştir" hedefi verilmez.

---

## Çalışma biçimi

- **Bir oturumda bir görev.** Faz bitirmeye çalışma, madde bitir.
- **Yazdığın kodu çalıştır.** `python smoke.py` her yeteneği çağırır; yeni yetenek eklediysen oraya da ekle.
- **Kullanıcıya soru sor.** Şartnamede karşılığı olmayan bir tasarım kararı çıktıysa varsayım yapma.
- **Küçük commit.** Bir commit bir iş. Türkçe mesaj, faz numarasıyla: `Faz 1: kural denetleyici`.
- **Diff'i küçük tut.** İncelenemeyen değişiklik onaylanmış sayılmaz.

## Kod tarzı

- Türkçe: değişken, fonksiyon, çıktı metinleri, yorumlar, commit mesajları.
- İngilizce kalır: kütüphane API'leri, `async`/`await` gibi dil anahtar kelimeleri.
- Yorum "ne yaptığını" değil "neden böyle yapıldığını" anlatır.
- Bağımlılık eklemeden önce sor. Şu an: fastapi, uvicorn, httpx, psutil.

## Yapma

- Boş iskelet dosya üretme (`pass` içeren agent sınıfları vb.). Çalışmayan kod eklenmez.
- Şartnamede olmayan özellik ekleme.
- Kimlik doğrulama, çoklu kullanıcı, dağıtım altyapısı kurma — tek kullanıcı var, localhost'ta.
- Test/CI/Docker/type-checking altyapısı kurma. Hobi projesi, `smoke.py` yeterli.
- Risk veya izin kontrolünü "geçici olarak" atlama.
