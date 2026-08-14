# Kuramadığın şeyi denetlemek: yazarın kendi deposu en güçlü kaynak

Doğrulandığı oturum: 2026-08-09, \"gauntlet loop\" prompting tekniği.

Bazen değerlendireceğin şey kurup çalıştırabileceğin bir araç değil: bir teknik,
bir yöntem, bir \"şunu yaptım\" iddiası. Kendi makinende ölçemezsin. O zaman
ölçümün yerine geçen tek şey **iddia sahibinin kendi yayımladığı ham veridir.**

## Ana bulgu: iddia sahibi sınırları çoğu zaman kendi yazmıştır

Teknik X'te 3,8 milyon izlenme aldı, demo etkileyiciydi, onlarca kişi tekrar
üretti. Yazarın kendi GitHub deposundaki `Honest assessment` bölümünde şu vardı:

> \"The goal was to match a modern Call of Duty. **It does not.**\"

Puanlar da orada duruyordu: 3,59 → 4,14 → **4,05** (gerileme) → 5,05/10. Durma
koşulu hiç tetiklenmemiş, yazar döngüyü elle durdurmuştu.

Dahası, yazarın kendi \"Process note\" bölümü tekniğin ana iddiasını çürütüyordu:
6 ajan paralel çalışınca kalite +0,46 arttı ama kusur 60→66 **yükseldi**; tek
ajanla sıralı geçişte kalite +1,00 arttı ve kusur 66→26 **düştü**.

**Bunların hiçbiri gizli değildi. Kimse okumamıştı.** Postun tezi bu oldu.

## Yöntem

1. **Birincil kaynağı bul, ikincil anlatıya güvenme.** Video/haber/thread değil,
   yazarın kendi deposu ve kendi yazısı. Bu oturumda videonun kaynak gösterdiği
   makale yanlış çıktı — gerçek kaynak ayrı bir yazıydı.
2. **Depoda şu bölümleri ara:** `Honest assessment`, `Limitations`, `Known issues`,
   `Process note`, `Results`, `Evaluation`. Ham skor tabloları buralarda olur.
3. **İddiayı otoritenin kendi belgesiyle karşılaştır.** Teknik Anthropic'in
   `Building Effective Agents` desenine dayanıyordu ama onun açık tavsiyesine
   (\"sabit iterasyon sınırı koyun\") **aykırıydı**. Bu tür çelişki en güçlü bulgu.
4. **Mühendislik incelemesi olup olmadığını ölç.** X izlenmesi inceleme değildir.
   HN'de kaç puan/yorum aldığına bak; `hn.algolia.com/api/v1/search` tek curl.
   3,8M izlenme vs HN'de 4 puan → \"kimse gerçekten bakmamış\" bulgusunun kanıtı.

```bash
# ikincil anlatinin verdigi kaynagi DOGRULA - icinde gecmiyorsa yanlis kaynaktir
curl -sL "<iddia-edilen-kaynak>" -o /tmp/k.html
grep -ciE "gauntlet|loop|subagent" /tmp/k.html    # 0 ise kaynak yanlis
```

## Bulamadığını uydurma

Bu oturumda bulunamayanlar açıkça \"bulamadım\" diye raporlandı: hakemli makale
yok, kontrollü karşılaştırmalı değerlendirme yok, X metriklerine doğrudan erişim
yok. **Bir şeyin yokluğu da bulgudur** — \"milyonlarca izlenme ama sıfır
mühendislik incelemesi\" cümlesi postun omurgası oldu.

## İsim ve rakam doğrulaması

Video transkriptinden gelen üç bilgi yanlıştı: yazarın soyadı (Schumer değil
**Shumer**), kaynak makale, ve izlenme sayısı (4,8M değil **3,8M** — yazarın
kendi LinkedIn'inde). Transkript, özet ve ikincil anlatı bu üç eksende
güvenilmez; her birini birincil kaynaktan teyit et.

## Denetim postuna dönüştürürken

Ton denetçi, komplo değil. \"Adam yalan söyledi\" değil, **\"adam dürüstçe yazmış,
kimse okumamış\"**. Kendi kullanım niyetini de söyle (\"ben yine de kullanacağım,
ama çıtayı kendim ölçeceğim\") — bu, denetimi reddiyeden ayırır.
