# Nötrleme JS tarifi (çalıştırılmış, 2026-08-10)

Bir SVG önizlemesi olan HTML aracında marka izlerini kaldıran tam akış.
Chrome JS köprüsüyle çalıştırılır (`authenticated-browser-automation` skill'indeki
`lk_exec.scpt` harness'ı — JS'i dosyadan okutur, kaçış katmanı oluşmaz):

```bash
osascript /tmp/lk_exec.scpt <window_id> <tab_index> /tmp/notrle.js
```

## Tek fonksiyon, beş katman

```js
function notrle(){
  // 1) Görünür metinler
  var yur = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  var n;
  while ((n = yur.nextNode())) {
    var t = n.nodeValue;
    if (t && /MAAR[İI]F|the client|ECOLE|KAMERUN|YAOUND|NKOLFOULOU/i.test(t)) {
      n.nodeValue = t
        .replace(/ECOLE MAARIF DE TÜRKİYE/gi, 'ECOLE ORION')
        .replace(/TÜRKİYE MAARİF OKULLARI/gi, 'ORION OKULLARI')
        .replace(/MAAR[İI]F/g, 'ORION').replace(/the client/g, 'Orion')
        .replace(/KAMERUN|CAMEROON/gi, 'ATLANTIS')
        .replace(/YAOUND[EÉ]/gi, 'PORTLAND')
        .replace(/NKOLFOULOU|BADALABOUGOU/gi, 'RIVERSIDE');
    }
  }

  // 2) Form alanları — ayrı geçiş şart, text node taraması bunları görmez
  [].slice.call(document.querySelectorAll('input[type=text], input:not([type])'))
    .forEach(function(i){
      if (/MAAR[İI]F|ECOLE|KAMERUN|YAOUND/i.test(i.value)) {
        i.value = i.value
          .replace(/MAAR[İI]F/g, 'ORION')
          .replace(/KAMERUN|CAMEROON/gi, 'ATLANTIS')
          .replace(/YAOUND[EÉ]/gi, 'PORTLAND');
        i.dispatchEvent(new Event('input', {bubbles:true}));
      }
    });

  // 3) Amblem ŞEKLİ — renk değil geometri
  var svg = document.querySelector('svg[viewBox]');
  if (svg) {
    [].slice.call(svg.querySelectorAll('g[transform]')).forEach(function(g){
      if (g.getAttribute('data-notr') === '1') return;      // tekrar işleme
      var pathlar = [].slice.call(g.querySelectorAll('path'));
      if (!pathlar.length) return;

      // marka amblemi imzası: uzun, çok kırıklı path
      var amblemMi = pathlar.some(function(p){
        var d = p.getAttribute('d') || '';
        return d.length > 400 && (d.match(/L/g) || []).length > 30;
      });
      if (!amblemMi) return;

      var b = g.getBBox();
      var renk = pathlar[0].getAttribute('fill') || '#4A6FA5';
      pathlar.forEach(function(p){ p.style.display = 'none'; });

      var ns = 'http://www.w3.org/2000/svg';
      var cx = b.x + b.width/2, cy = b.y + b.height/2;
      var R  = Math.min(b.width, b.height)/2;

      function sekizgen(olcek, dolgu){
        var p = document.createElementNS(ns, 'path'), pts = [];
        for (var i = 0; i < 8; i++) {
          var a = (Math.PI/4)*i - Math.PI/2;
          pts.push((cx + R*olcek*Math.cos(a)).toFixed(2) + ' ' +
                   (cy + R*olcek*Math.sin(a)).toFixed(2));
        }
        p.setAttribute('d', 'M' + pts.join(' L') + ' Z');
        p.setAttribute('fill', dolgu);
        return p;
      }
      g.appendChild(sekizgen(1, renk));       // gövde
      g.appendChild(sekizgen(0.52, '#FFF'));  // iç boşluk
      g.setAttribute('data-notr', '1');
    });
  }

  // 4) Arayüz rengi — hesaplanmış stili tara, attribute yetmez
  [].slice.call(document.querySelectorAll('*')).forEach(function(e){
    var h = getComputedStyle(e);
    function tq(s){
      if (!s) return false;
      s = s.toLowerCase().replace(/\s/g,'');
      if (s.indexOf('139eb4') > -1) return true;            // marka hex'i
      var m = s.match(/rgba?\((\d+),(\d+),(\d+)/);
      if (!m) return false;
      return Math.abs(+m[1]-19)<40 && Math.abs(+m[2]-158)<40 && Math.abs(+m[3]-180)<40;
    }
    if (tq(h.backgroundColor)) e.style.backgroundColor = '#4A6FA5';
    if (tq(h.color))           e.style.color = '#4A6FA5';
    if (tq(h.borderColor))     e.style.borderColor = '#4A6FA5';
    ['fill','stroke'].forEach(function(a){
      var v = e.getAttribute && e.getAttribute(a);
      if (tq(v)) e.setAttribute(a, '#4A6FA5');
    });
  });
}
```

Renk eşleştirmede tolerans (`<40`) şart: aynı marka rengi arayüzde `rgb()`,
hex ve SVG attribute biçiminde, kimi yerde hafif ton farkıyla geçiyor. Sadece
hex arayan ilk sürüm "BEYAZ" düğmesindeki turkuazı kaçırdı.

## Logotype değişimi — grubun İÇİNE koy

```js
var gizli = [].slice.call(svg.querySelectorAll('g[transform]'))
  .find(function(g){ return g.style.display === 'none'; });

gizli.style.display = '';
var ic = gizli.getBBox();      // grubun KENDİ koordinat uzayı
gizli.style.display = 'none';

var yeni = gizli.cloneNode(false);   // aynı transform, boş
yeni.style.display = '';

var m = document.createElementNS('http://www.w3.org/2000/svg', 'text');
m.setAttribute('x', ic.x + ic.width / 2);
m.setAttribute('y', ic.y + ic.height * 0.84);
m.setAttribute('text-anchor', 'middle');
m.setAttribute('font-size', ic.height * 0.95);
m.setAttribute('font-weight', '800');
m.textContent = 'ORION';
yeni.appendChild(m);
gizli.parentNode.insertBefore(yeni, gizli);
```

`cloneNode(false)` ile grubun `transform`'unu miras al — metni SVG kökünün
`viewBox` uzayında kurarsan ölçek tutmaz (126x65'lik viewBox'ta 308 birimlik
dev yazı çıktı).

## Video turu: mod gezme

```js
var s = document.querySelector('select');
var i = 0;
function sonraki(){
  if (i >= s.options.length) return;
  s.selectedIndex = i;
  s.dispatchEvent(new Event('change', {bubbles:true}));
  notrle();
  setTimeout(notrle, 150);
  setTimeout(notrle, 400);
  setTimeout(notrle, 800);
  i++;
  setTimeout(sonraki, 3400);
}
notrle();      // ilk mod kayıttan ÖNCE temizlensin
sonraki();
```

`MutationObserver` kurma — sayfayı kilitliyor (SKILL.md'deki tuzak 5).
Mod başına ~3,4 saniye izleyiciye rahat geliyor; 5 mod ≈ 17 sn video.
