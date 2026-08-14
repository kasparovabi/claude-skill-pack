# Koordinat ölçeği ve uzun tekrarlı GUI işleri

Doğrulandığı oturum: 2026-08-05, Chrome + LinkedIn, ~40 maddelik liste budama.

## Sorun

`computer_use capture` iki farklı uzayda sayı döndürüyor ve bunlar aynı değil:

- Ekran görüntüsünün boyutu: örn. `1455 x 795`
- AX `bounds` uzayı: örn. `[802, -1050, 1920, 1049]` (negatif y dahil)

Ekran görüntüsüne bakıp okuduğun koordinatı doğrudan `coordinate=[x,y]` olarak
verirsen tıklama ıskalar. Bu oturumda ölçek **1.32** çıktı, yani her tıklama sistematik
olarak yanlış yere gitti ve bir süre "tıklama çalışmıyor" sanıldı.

## Çözüm A — ölçeği hesapla

Dönüşüm deterministik, bir kez hesaplayıp tüm oturumda kullan:

```python
ax_x, ax_y, ax_w, ax_h = 802, -1050, 1920, 1049   # capture'ın bounds alanı
img_w, img_h = 1455, 795                          # capture'ın width/height'ı
sx, sy = ax_w / img_w, ax_h / img_h               # -> 1.3196, 1.3195

def gercek(gx, gy):
    return (round(ax_x + gx * sx), round(ax_y + gy * sy))
```

## Çözüm B — pencereyi görüntü boyutuna yaklaştır (tercih edilen)

AppleScript ile pencereyi küçültünce ölçek ~1'e iner ve ekran görüntüsünden okunan
koordinat doğrudan çalışır:

```applescript
tell application "Google Chrome"
  set bounds of window id 444136678 to {0, 0, 1512, 940}
end tell
```

Uzun tekrarlı işlerde bu yaklaşım çok daha ucuz: her adımda tam AX capture alıp index
çözmek yerine sabit koordinatlarla döngü kurabilirsin. Pencere her yeniden
boyutlandığında ölçeği yeniden doğrula.

## Sayfa kaydırma tutmadığında

Bazı web uygulamalarında (özellikle sanal listeler / iç scroll panelleri) hem fare
tekerleği hem `pagedown` sonuçsuz kalabiliyor. İki işleyen kaçış yolu:

1. **Zoom out.** `keystroke "-" using command down` birkaç kez — daha çok satır tek
   ekrana sığar, kaydırmaya gerek kalmaz.
   ```applescript
   tell application "System Events"
     tell process "Google Chrome"
       set frontmost to true
       repeat 4 times
         keystroke "-" using command down
         delay 0.35
       end repeat
     end tell
   end tell
   ```
2. **Silme/işleme sırasını kendi lehine kullan.** Liste maddelerini tek tek
   işliyorsan, bir madde kalkınca sonrakiler yukarı kayar. Hep aynı konumdan çalış;
   kaydırmaya hiç ihtiyaç duymazsın.

## AX ağacı sadece görüneni verir

Ekranda olmayan liste maddeleri AX çıktısında **yok**. 80 maddelik bir listede tam
envanter çıkarmaya çalışıp 20 madde görmek normaldir, hata değil. Tam listeye ihtiyacın
varsa önce zoom out yap, sonra capture al.

## `keys` isim tuzakları

`computer_use action=key` bazı isimleri tanımıyor. Bu oturumda gözlenen:

| Çalışmayan | Çalışan |
|---|---|
| `page_down` | `pagedown` |
| `cmd+minus` | AppleScript `keystroke "-" using command down` |

Ret aldığında ismi değiştirip bir kez daha dene, aynı ismi tekrarlama.

## Otomatik tamamlamalı alanı temizleme

`cmd+a` bu tür alanlarda çoğu zaman çalışmıyor (tek karakter siliyor ya da hiç).
Backspace döngüsü de odak kaydığında boşa gidiyor. **En güvenilir yol `set_value`**:
alanı istediğin metinle tek seferde değiştirir, önceki bozuk içeriği siler.

```
computer_use(action="set_value", element=66, value="AI Agents", pid=..., window_id=...)
```

`set_value` hata verirse (`AXValue failed with error -25202`) element index bayatlamıştır
— taze capture al, index'i yeniden çöz.
