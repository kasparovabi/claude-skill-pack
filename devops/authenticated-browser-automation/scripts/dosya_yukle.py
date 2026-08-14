#!/usr/bin/env python3
"""
Web formundaki input[type=file] alanina dosya yukler.

Neden gerekli: tarayicilar guvenlik geregi dosya alanini JS ile doldurtmaz.
Chrome ayrica dosya secici sheet'ini yalnizca GUVENILIR kullanici hareketiyle
acar; JS .click() sessizce hicbir sey yapmaz. Bu betik sheet acildiktan
SONRAKI kismi otomatiklestirir (yolu yazma + onaylama).

Kullanim iki adimdir:

  1. Sheet'i GERCEK fare tiklamasiyla ac (bu betik degil, computer_use ile):
       computer_use(action="click", coordinate=[x, y],
                    delivery_mode="foreground", pid=..., window_id=...)

  2. Sheet acikken bu betigi cagir:
       python3 dosya_yukle.py <pencere_id> <sekme_no> <dosya_yolu>

Dogrulandi: 2026-08-13, Personio basvuru formu, iki alan da yuklendi.
"""
import subprocess
import sys
import time


def sh(betik, sure=40):
    try:
        r = subprocess.run(["osascript", "-e", betik], capture_output=True,
                           text=True, timeout=sure)
        return (r.stdout or r.stderr).strip()
    except subprocess.TimeoutExpired:
        return "ZAMAN ASIMI"


def sheet_penceresi(deneme=10):
    """Sheet'i TASIYAN pencereyi bul.

    Kritik: sheet her zaman window 1'de acilmaz. Yalnizca window 1'e bakmak
    "DOSYA PENCERESI GELMEDI" yanlis negatifini uretir; sheet aslinda
    window 2'dedir. Butun pencereleri tara.
    """
    betik = '''tell application "System Events" to tell process "Google Chrome"
      repeat with k from 1 to count of windows
        if (count of sheets of window k) > 0 then return k
      end repeat
      return "0"
    end tell'''
    for _ in range(deneme):
        s = sh(betik)
        if s.isdigit() and int(s) > 0:
            return int(s)
        time.sleep(0.6)
    return 0


def yolu_yaz(dosya):
    """Cmd+Shift+G ile tam yolu yaz, iki kez Enter.

    Ilk Enter yolu onaylar, ikinci Enter dosyayi acar. Aradaki gecikmeler
    comert olmali, sheet agir aciliyor.
    """
    return sh('''tell application "System Events" to tell process "Google Chrome"
      set frontmost to true
      delay 0.5
      keystroke "g" using {command down, shift down}
      delay 1.2
      keystroke "%s"
      delay 0.9
      key code 36
      delay 1.6
      key code 36
    end tell
    return "yazildi"''' % dosya)


def durum(pencere_id, sekme):
    return sh('tell application "Google Chrome" to execute tab %s of '
              '(first window whose id is %s) javascript '
              '"[].slice.call(document.querySelectorAll(\'input[type=file]\'))'
              '.map(function(f,i){return i+\':\'+(f.files&&f.files.length?'
              'f.files[0].name:\'bos\')}).join(\' | \')"' % (sekme, pencere_id))


def yukle(pencere_id, sekme, dosya):
    k = sheet_penceresi()
    if not k:
        return ("SHEET YOK: dosya secici acilmamis. Sheet'i once GERCEK fare "
                "tiklamasiyla ac (computer_use click, delivery_mode=foreground). "
                "JS .click() Chrome'da sheet acmaz.")
    yolu_yaz(dosya)
    time.sleep(2.5)
    return durum(pencere_id, sekme)


if __name__ == "__main__":
    print(yukle(sys.argv[1], sys.argv[2], sys.argv[3]))
