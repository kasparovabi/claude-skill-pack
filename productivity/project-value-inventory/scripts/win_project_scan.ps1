# Windows uzak proje taramasi.
#
# .git ARAMAZ - isaret dosyasi arar. Cogu gercek proje versiyon kontrolu altinda
# degil; sadece .git aramak sistematik olarak eksik envanter uretir.
#
# Kullanim:
#   scp -o BatchMode=yes win_project_scan.ps1 KULLANICI@IP:win_scan.ps1
#   ssh -o BatchMode=yes KULLANICI@IP "powershell -NoProfile -ExecutionPolicy Bypass -File win_scan.ps1" \
#     2>&1 | grep -v "WARNING\|vulnerable\|upgraded\|openssh.com" > /tmp/win.json
#
# ONCE surucu koklerini ve profil birinci seviyesini listele, ILGINC olanlari
# asagidaki $roots listesine ekle. Kor derin tarama yavas ve yaniltici.
#   foreach($d in @('C:\','D:\')){ Get-ChildItem $d -Directory -Force }
#   Get-ChildItem $env:USERPROFILE -Directory -Force

$ErrorActionPreference = 'SilentlyContinue'

$roots = @(
  'C:\AI','C:\mockup','C:\upscale','C:\sentinel','C:\tools',
  "$env:USERPROFILE\projects", "$env:USERPROFILE\source",
  "$env:USERPROFILE\Documents", "$env:USERPROFILE\Desktop"
)

$markers = @('package.json','requirements.txt','pyproject.toml','main.py','app.py',
             'index.js','server.js','Cargo.toml','go.mod','pom.xml',
             'docker-compose.yml','Dockerfile','README.md','.git')

$codeExt = '^\.(py|js|ts|tsx|jsx|go|rs|java|cs|swift|rb|php|sh|ps1)$'

function Get-ProjInfo($dir) {
  $found = @()
  foreach ($f in $markers) {
    if (Test-Path (Join-Path $dir $f)) { $found += $f }
  }
  if ($found.Count -eq 0) { return $null }

  $o = [ordered]@{}
  $o.path  = $dir
  $o.marks = ($found -join ',')

  $files = Get-ChildItem $dir -Recurse -File -Force -EA SilentlyContinue |
           Select-Object -First 4000
  $o.files = $files.Count
  if ($files.Count -gt 0) {
    $o.last = ($files | Sort-Object LastWriteTime -Descending |
               Select-Object -First 1).LastWriteTime.ToString('yyyy-MM-dd')
    $o.code = ($files | Where-Object { $_.Extension -match $codeExt }).Count
  }

  if (Test-Path (Join-Path $dir '.git')) {
    $o.commit = (& git -C $dir rev-list --count HEAD 2>$null)
    $o.remote = (& git -C $dir remote get-url origin 2>$null)
    $first = (& git -C $dir log --reverse --format=%ci --max-parents=0 2>$null |
              Select-Object -First 1)
    if ($first) { $o.ilk = $first.Substring(0,10) }
  }

  $pj = Join-Path $dir 'package.json'
  if (Test-Path $pj) {
    try {
      $j = Get-Content $pj -Raw | ConvertFrom-Json
      $o.pkg = $j.name
      if ($j.description) {
        $o.desc = ($j.description -replace '[^\w\s\.\,\-\(\)/]', ' ') -replace '\s+', ' '
      }
      if ($j.dependencies) {
        $o.deps = (($j.dependencies.PSObject.Properties.Name) | Select-Object -First 6) -join ','
      }
    } catch {}
  }

  # README metnini JSON'a koymadan ONCE temizle. Tirnak/backtick/kontrol
  # karakterleri ConvertTo-Json ciktisini gecersiz kilar.
  $rd = Join-Path $dir 'README.md'
  if (Test-Path $rd) {
    $line = (Get-Content $rd -TotalCount 25 |
             Where-Object { $_.Trim() -ne '' -and $_ -notmatch '^\[!\[' } |
             Select-Object -First 1)
    if ($line) {
      $clean = $line.Trim().TrimStart('#').Trim() -replace '[^\w\s\.\,\-\(\)/]', ' '
      $o.readme = ($clean -replace '\s+', ' ')
    }
  }
  return $o
}

$results = @()
foreach ($r in $roots) {
  if (-not (Test-Path $r)) { continue }
  $self = Get-ProjInfo $r
  if ($self) { $results += $self }
  Get-ChildItem $r -Directory -Force -EA SilentlyContinue | ForEach-Object {
    $i = Get-ProjInfo $_.FullName
    if ($i) { $results += $i }
    Get-ChildItem $_.FullName -Directory -Force -EA SilentlyContinue | ForEach-Object {
      $i2 = Get-ProjInfo $_.FullName
      if ($i2) { $results += $i2 }
    }
  }
}

$results | ConvertTo-Json -Depth 4 -Compress
