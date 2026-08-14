-- Chrome JS köprüsü ile toplu web formu düzenleme harness'ı
-- Doğrulandığı oturum: 2026-08-05, LinkedIn yetenek listesi (49 silme + 7 ekleme,
-- AX yoluyla ~200 araç çağrısı sürecek iş ~10 çağrıya indi).
--
-- ÖN KOŞUL: Chrome'da Görünüm > Geliştirici > "Apple Events'ten JavaScript'e izin ver"
-- işaretli olmalı. Kullanıcı ELLE işaretlemeli; menüyü programatik tıklamak tutmuyor
-- (AXPress dahil üç yol denendi, Chrome bilinçli koruyor).
--
-- KULLANIM: bu dosyayı /tmp/x.scpt olarak kopyala, şu üç yeri düzenle:
--   1. WINDOW_ID    (AppleScript `id of window` — computer_use window_id DEĞİL, farklı sayı)
--   2. URL_PARCASI  (hedef sekmeyi bulmak için)
--   3. en alttaki toDelete / toAdd listeleri + aria-label regex'i
-- Sonra: osascript /tmp/x.scpt

property WINDOW_ID : 444136678
property URL_PARCASI : "linkedin.com"

-- ============================================================
-- 1. Ortak JS çalıştırıcı — doğru sekmeyi bulur ve aktif yapar
-- ============================================================
on runJS(theJS)
  tell application "Google Chrome"
    set w to window id WINDOW_ID
    set idx to 0
    set i to 0
    repeat with t in tabs of w
      set i to i + 1
      if URL of t contains URL_PARCASI then
        set idx to i
        exit repeat
      end if
    end repeat
    if idx = 0 then return "SEKME_YOK"
    set active tab index of w to idx
    return (execute active tab of w javascript theJS)
  end tell
end runJS

-- KÖPRÜ CANLI MI? Her şeyden önce bunu çalıştır. Köprü kapalıysa Chrome
-- hata mesajında bunu açıkça söyler; o zaman kullanıcıdan kutuyu işaretlemesini
-- iste, sessizce AX yoluna düşme.
on bridgeCheck()
  return runJS("document.querySelectorAll('button').length")
end bridgeCheck

-- ============================================================
-- 2. Liste envanteri — aria-label deseninden madde adlarını çek
--
-- DİKKAT: sanal listelerde DOM yalnızca ilk ~20 maddeyi tutar.
-- "Daha fazla göster" tıklamak, window.scrollTo, scrollBy döngüsü:
-- HİÇBİRİ sayıyı artırmıyor (hepsi bu oturumda denendi, 20'de sabit kaldı).
-- Doğru döngü: BİR PARTİ SİL -> YENİDEN SORGULA -> yeni maddeler görünür.
-- ============================================================
on listItems()
  set js to "(function(){
    var out = [];
    document.querySelectorAll('a[aria-label], button[aria-label]').forEach(function(el){
      var al = el.getAttribute('aria-label') || '';
      var m = al.match(/^(.+?)\\s+(?:yeteneğini|becerisini)\\s+düzenle/);
      if (m && out.indexOf(m[1]) === -1) out.push(m[1]);
    });
    return out.length + ' |||| ' + out.join(' ~~ ');
  })()"
  return runJS(js)
end listItems

-- ============================================================
-- 3. Tek maddeyi sil — üç aşamalı (düzenle -> sil -> onayla)
--    Aradaki delay'ler modal animasyonu içindir, kısaltma.
-- ============================================================
on deleteItem(itemName)
  set js1 to "(function(){
    var target = null;
    document.querySelectorAll('a[aria-label], button[aria-label]').forEach(function(el){
      var al = el.getAttribute('aria-label') || '';
      var m = al.match(/^(.+?)\\s+(?:yeteneğini|becerisini)\\s+düzenle/);
      if (m && m[1].trim() === " & quoted form of itemName & ") { target = el; }
    });
    if (!target) return 'NOTFOUND';
    target.click();
    return 'CLICKED';
  })()"
  if runJS(js1) is "NOTFOUND" then return "NOTFOUND"
  delay 1.4

  set js2 to "(function(){
    var b = Array.from(document.querySelectorAll('button')).find(function(x){
      return /^(Yeteneği sil|Delete skill)/.test((x.innerText||'').trim());
    });
    if (!b) return 'NODELETE';
    b.click(); return 'DELETECLICKED';
  })()"
  if runJS(js2) is "NODELETE" then return "NODELETE"
  delay 1.2

  set js3 to "(function(){
    var b = Array.from(document.querySelectorAll('button')).find(function(x){
      var t = (x.innerText||'').trim();
      return t === 'Sil' || t === 'Delete';
    });
    if (!b) return 'NOCONFIRM';
    b.click(); return 'CONFIRMED';
  })()"
  set r to runJS(js3)
  delay 1.8
  return r
end deleteItem

-- ============================================================
-- 4. React kontrollü input'a yazma — KRİTİK TUZAK
--
--    inp.value = "x" React'te ÇALIŞMAZ. React kendi iç state'ini korur,
--    yazdığın değeri yok sayar ve autocomplete listesi hiç açılmaz.
--    Çözüm: native setter'ı PROTOTİPTEN al, çağır, sonra bubbling event at.
-- ============================================================
on typeInto(theTerm)
  set js to "(function(){
    var inp = document.querySelector('input[role=\"combobox\"], input[aria-autocomplete=\"list\"]');
    if(!inp) return 'NOINPUT';
    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
    setter.call(inp, " & quoted form of theTerm & ");
    inp.dispatchEvent(new Event('input',  {bubbles:true}));
    inp.dispatchEvent(new Event('change', {bubbles:true}));
    return 'TYPED';
  })()"
  return runJS(js)
end typeInto

-- ============================================================
-- 5. ÖNCE YOKLA, SONRA EKLE
--
--    Kapalı katalog alanlarında (yetenek, etiket, konum, sektör) istediğin
--    terim katalogda olmayabilir. Tek tek deneyip "yok" demek yerine tek
--    turda ONLARCA varyasyon yokla, dönen [role=option] listelerini oku,
--    sonra sadece BİREBİR eşleşenleri ekle.
--
--    NOT: [role="option"] seçicisine sadık kal. Geniş 'li' seçicisi sayfanın
--    navigasyon menüsünü de toplar (Ana Sayfa / Ağım / İş İlanları ...) ve
--    çıktıyı çöple doldurur.
-- ============================================================
on probeTerm(theTerm)
  if typeInto(theTerm) is "NOINPUT" then return "NOINPUT"
  delay 2.2
  set js to "(function(){
    var out = [];
    document.querySelectorAll('[role=\"option\"]').forEach(function(el){
      var t = (el.innerText||'').trim().replace(/\\s+/g,' ');
      if (t && out.indexOf(t) === -1) out.push(t);
    });
    return out.slice(0,8).join(' / ');
  })()"
  return runJS(js)
end probeTerm

on addItem(theTerm, exactLabel)
  if typeInto(theTerm) is "NOINPUT" then return "NOINPUT"
  delay 2.5
  set js to "(function(){
    var want = " & quoted form of exactLabel & ";
    var opts = Array.from(document.querySelectorAll('[role=\"option\"]'));
    var hit = opts.find(function(el){
      return (el.innerText||'').trim().replace(/\\s+/g,' ') === want;
    });
    if(!hit) return 'NOOPT:' + opts.slice(0,4).map(function(e){
      return (e.innerText||'').trim(); }).join('|');
    hit.click(); return 'ADDED';
  })()"
  set r to runJS(js)
  delay 1.5
  return r
end addItem

on saveForm()
  set js to "(function(){
    var b = Array.from(document.querySelectorAll('button')).find(function(x){
      var t = (x.innerText||'').trim();
      return t === 'Kaydet' || t === 'Save';
    });
    if(!b) return 'NOSAVE';
    b.click(); return 'SAVED';
  })()"
  return runJS(js)
end saveForm

-- ============================================================
-- 6. ÇALIŞTIRMA — her maddeyi try ile sar, rapor biriktir.
--    Tek madde patlarsa parti durmaz; sonunda hangisi neden olmadı görürsün.
--    Bu rapor aynı zamanda kullanıcıya gösterilecek kanıttır.
-- ============================================================
set report to "KOPRU: " & bridgeCheck() & linefeed

set toDelete to {"Madde A", "Madde B"}
repeat with s in toDelete
  set sName to s as string
  try
    set report to report & sName & " => " & deleteItem(sName) & linefeed
  on error e
    set report to report & sName & " => HATA: " & e & linefeed
  end try
end repeat

-- {yazılacak terim, katalogda beklenen BİREBİR etiket}
set toAdd to {{"n8n", "n8n"}, {"Supabase", "Supabase"}}
repeat with pair in toAdd
  try
    set report to report & (item 2 of pair) & " => " & ¬
      addItem(item 1 of pair, item 2 of pair) & linefeed
  on error e
    set report to report & (item 2 of pair) & " => HATA: " & e & linefeed
  end try
end repeat

return report
