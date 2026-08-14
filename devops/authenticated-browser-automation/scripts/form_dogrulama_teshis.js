// Formdaki HANGI alanin gonderimi bloke ettigini bulur ve takili
// customError bayragini duserer.
//
// Ne zaman: form alanlari dolu gorunuyor ama Gonder calismiyor, ya da
// tarayici "Please fill out the details" / "Bu alani doldurun" diyor.
//
// Kullanim (Chrome JS koprusu ile):
//   osascript /tmp/lk_exec.scpt <WINDOW_ID> <TAB_INDEX> \
//     ~/.hermes/skills/devops/authenticated-browser-automation/scripts/form_dogrulama_teshis.js
//
// Cikti ornegi:
//   ENGEL: repository_advisory_description | deger:3317 | customError
//     -> "Please fill out the details"
//     -> BAYRAK DUSURULDU, artik gecerli
//
// NOT: setCustomValidity('') yalniz sitenin kendi kodunun BIRAKTIGI takili
// bayragi temizler. Alan gercekten bossa (valueMissing) bu betik onu
// duzeltmez, sadece raporlar -- once icerigi doldur.

(function () {
  var alanlar = [].slice.call(
    document.querySelectorAll('input, textarea, select')
  );
  var rapor = [];
  var duzeltilen = 0;

  alanlar.forEach(function (a) {
    var r = a.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;      // gizli alan, atla
    if (!a.willValidate) return;                       // dogrulamaya girmiyor
    if (a.checkValidity()) return;                     // sorunsuz

    var ad = a.id || a.name || a.tagName.toLowerCase();
    var v = a.validity;
    var sebep = v.valueMissing ? 'valueMissing'
              : v.customError ? 'customError'
              : v.tooShort ? 'tooShort'
              : v.tooLong ? 'tooLong'
              : v.patternMismatch ? 'patternMismatch'
              : v.typeMismatch ? 'typeMismatch'
              : v.rangeUnderflow || v.rangeOverflow ? 'range'
              : 'bilinmeyen';

    var satir = 'ENGEL: ' + ad +
                ' | deger:' + (a.value || '').length +
                ' | ' + sebep +
                '\n  -> "' + a.validationMessage + '"';

    // Takili customError: alan dolu ama site bayragi temizlememis.
    // Tek guvenli otomatik duzeltme bu.
    if (v.customError && (a.value || '').length > 0) {
      a.setCustomValidity('');
      duzeltilen++;
      satir += a.checkValidity()
        ? '\n  -> BAYRAK DUSURULDU, artik gecerli'
        : '\n  -> bayrak dusuruldu ama HALA gecersiz, baska kural var';
    } else if (v.valueMissing) {
      satir += '\n  -> alan GERCEKTEN bos, once doldur';
    }

    rapor.push(satir);
  });

  if (!rapor.length) {
    return 'TUM ALANLAR GECERLI (engel formda degil: gizli alan, ' +
           'sunucu hatasi ya da eksik zorunlu bolum olabilir)';
  }
  return rapor.join('\n') + '\n\nduzeltilen: ' + duzeltilen;
})()
