# guard/ — koruma alanı

Bu dizin **ajanın yazma alanı dışındadır** (CLAUDE.md Değişmez 8, şartname Bölüm 18).

Buradaki dosyalar Venüs'ün ne yapmasına izin verildiğini tanımlar. Venüs
bunları **okur, yazmaz**. Gece vardiyası (Faz 8) da buraya dokunamaz —
kendi iznini genişletebilen bir sistem, izin sistemi değildir.

| dosya | ne yapar |
|---|---|
| `beyazliste.yaml` | Venüs'ün açabileceği uygulama, sayfa ve düzenler |
| `izinler.yaml` | kapatılmış izinler — burada yazan izin hiçbir yetenekte çalışmaz |

Bir şeyi Venüs'ün yapabilmesini istiyorsan buraya **sen** yazarsın.
Venüs'e söylemek yetmez; dosyada yoksa çalışmaz.
