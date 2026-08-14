---
name: video-link-download
description: Download videos from YouTube/links at full quality and upload to a file host, returning a direct download link. Use this whenever Kasparov or anyone in MAARIF AI ASISTAN group asks to download a video from any link.
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [video, youtube, yt-dlp, gofile, telegram, download]
    category: media
---

# Video İndirme Protokolü (Telegram)

Kullanıcı YouTube veya başka bir platformdan video indirmek istediğinde MUTLAKA bu akışı kullan. Telegram 50 MB sınırı yüzünden videoyu sıkıştırıp göndermek YASAK — kalite bozulur, kullanıcı kızar.

## Tetikleyici cümleler
- "bu videoyu indir"
- "videoyu indirsene"
- "linkten video indir"
- "şu videoyu yolla"
- Herhangi bir YouTube/Vimeo/Twitter/TikTok linki + "indir"

## Akış (kesinlikle bu sırayla)

### 1. Tam kalite indir
```bash
cd /tmp && yt-dlp -f "bv*+ba/b" --merge-output-format mp4 -o "video_$(date +%s).%(ext)s" "URL"
```
- `-f "bv*+ba/b"` = en iyi video + en iyi ses, fallback en iyi tek dosya
- Background olarak çalıştır (`background=true`, `notify_on_complete=true`) — büyük dosyalar 2-5 dk sürer
- yt-dlp yolu: `/usr/local/Cellar/yt-dlp/<sürüm>/bin/yt-dlp` veya PATH'te varsa direkt `yt-dlp`

### 2. Telegram sınırını kontrol et
```bash
SIZE=$(stat -f%z /tmp/video.mp4)
```
- **< 50 MB** ise direkt sendVideo ile gönder (aşağıya bak)
- **>= 50 MB** ise file host'a yükle (gofile)

### 3a. Telegram'a doğrudan gönder (< 50 MB)
Mutlaka `width`, `height`, `duration` parametrelerini ver — yoksa Telegram kare olarak gösterir:
```bash
W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 /tmp/video.mp4)
H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 /tmp/video.mp4)
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 /tmp/video.mp4 | cut -d. -f1)
TOKEN=$(awk -F= '/X_TELEGRAM_BOT_TOKEN_DISABLED/{print $2}' ~/.hermes/.env)
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendVideo" \
  -F "chat_id=<CHAT_ID>" \
  -F "video=@/tmp/video.mp4" \
  -F "width=$W" -F "height=$H" -F "duration=$D" \
  -F "supports_streaming=true"
```
Topic ID varsa `-F "message_thread_id=<TOPIC>"` ekle.

### 3b. gofile.io'ya yükle (>= 50 MB)
```bash
# Server seç (eu zone genelde hızlı)
SERVER=$(curl -s https://api.gofile.io/servers | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['servers'][0]['name'])")
# Upload (büyük dosya için background)
curl -X POST -F "file=@/tmp/video.mp4" "https://${SERVER}.gofile.io/contents/uploadfile" -o /tmp/gofile_resp.json
# Link'i çıkar
LINK=$(python3 -c "import json; print(json.load(open('/tmp/gofile_resp.json'))['data']['downloadPage'])")
echo $LINK
```
Çıktı: `https://gofile.io/d/XXXXXX` formatında bir indirme sayfası linki.

### 4. Kullanıcıya cevap
Linki tek satırda ver, "şu sayfadan indir" demeden link tek başına yeterli.

## Pitfalls (gerçek hatalar, dikkat)
1. **Asla `-x` veya `--audio-format mp3` kullanma** — kullanıcı sadece ses dedi değilse video iste video ver
2. **Asla `--max-filesize` ile sıkıştırma yapma** — kalite düşer, kullanıcı tepki gösterir
3. **Telegram'a width/height vermeden gönderme** — kare görünür, kullanıcı "leş" der
4. **catbox.moe = 200 MB limit, transfer.sh = kapandı (2024'te)** — gofile.io kullan, sınırsız
5. **0x0.st bazen bağlantı reset atar** — fallback gofile
6. **Türkçe karakterli dosya adı + bash** = hata, dosya adını sadece ASCII tut (`video_TIMESTAMP.mp4`)
7. **Background ffmpeg/yt-dlp çalışırken Hermes timeout** — `notify_on_complete=true` kullan, sonra `process action=wait`

## Yetki
- Kasparov (DM, user_id=<user_id>): direkt yap, sorma
- MAARIF AI ASISTAN grubu üyeleri: direkt yap, sorma
- Diğer kullanıcılar: önce profil kontrol et, yetki yoksa nazikçe reddet

## Hızlı şablon (one-liner)

```bash
URL="https://www.youtube.com/watch?v=..."
cd /tmp && rm -f vid.mp4
yt-dlp -f "bv*+ba/b" --merge-output-format mp4 -o vid.mp4 "$URL"
SIZE=$(stat -f%z vid.mp4)
if [ $SIZE -lt 49000000 ]; then
  echo "telegram'a gönder"
else
  SERVER=$(curl -s https://api.gofile.io/servers | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['servers'][0]['name'])")
  curl -X POST -F "file=@vid.mp4" "https://${SERVER}.gofile.io/contents/uploadfile" -o resp.json
  python3 -c "import json; print(json.load(open('resp.json'))['data']['downloadPage'])"
fi
```
