<#
Check-FlacRatings.ps1
Reads the rating tags stored INSIDE your FLAC files (not Plex's database) and
shows what the jukebox script on the Pi sees.

  - every tag whose name contains "RATING" (RATING, FMPS_RATING, RATING WMP, ...)
  - the star value the Pi script turns it into (same rules as jukebox_library.py)
  - a summary: raw values, and how many files land on each star count

Nothing is changed. Needs no extra software (plain PowerShell 5 or 7).

Usage (in PowerShell on the PC with the music):
  powershell -ExecutionPolicy Bypass -File .\Check-FlacRatings.ps1 -Path "D:\Music"
  ... -Path "D:\Music" -Csv "$HOME\Desktop\flac-ratings.csv"   # also save per-file results
#>
param(
    [Parameter(Mandatory = $true)][string]$Path,
    [string]$Csv
)

function Read-UInt32BE([byte[]]$b, [int]$o) { ([int]$b[$o] -shl 24) -bor ([int]$b[$o+1] -shl 16) -bor ([int]$b[$o+2] -shl 8) -bor [int]$b[$o+3] }

# Returns a hashtable of UPPERCASE tag name -> list of values, from the FLAC Vorbis comment block.
function Get-FlacTags([string]$file) {
    $tags = @{}
    $fs = [System.IO.File]::Open($file, 'Open', 'Read', 'ReadWrite')
    try {
        $br = New-Object System.IO.BinaryReader($fs)
        $magic = $br.ReadBytes(4)
        # Some taggers put an ID3v2 tag in front of the FLAC data. Read its
        # ratings (POPM, TXXX:RATING) and skip past it.
        if ([System.Text.Encoding]::ASCII.GetString($magic, 0, 3) -eq 'ID3') {
            $rest = $br.ReadBytes(6)
            $ver = $magic[3]
            $size = (([int]$rest[2] -band 0x7F) -shl 21) -bor (([int]$rest[3] -band 0x7F) -shl 14) -bor (([int]$rest[4] -band 0x7F) -shl 7) -bor ($rest[5] -band 0x7F)
            $id3 = $br.ReadBytes($size)
            $o = 0
            while ($o + 10 -le $id3.Length -and $id3[$o] -ne 0) {
                $fid = [System.Text.Encoding]::ASCII.GetString($id3, $o, 4)
                if ($ver -ge 4) {
                    $fsz = (([int]$id3[$o+4] -band 0x7F) -shl 21) -bor (([int]$id3[$o+5] -band 0x7F) -shl 14) -bor (([int]$id3[$o+6] -band 0x7F) -shl 7) -bor ($id3[$o+7] -band 0x7F)
                } else { $fsz = Read-UInt32BE $id3 ($o + 4) }
                $d = $o + 10
                if ($fsz -le 0 -or $d + $fsz -gt $id3.Length) { break }
                if ($fid -eq 'POPM') {
                    $z = [Array]::IndexOf($id3, [byte]0, $d)
                    if ($z -ge $d -and $z + 1 -lt $d + $fsz) {
                        $email = [System.Text.Encoding]::ASCII.GetString($id3, $d, $z - $d)
                        $k = "ID3 POPM ($email)"
                        if (-not $tags.ContainsKey($k)) { $tags[$k] = @() }
                        $tags[$k] += [string]$id3[$z + 1]
                    }
                } elseif ($fid -eq 'TXXX') {
                    $txt = [System.Text.Encoding]::UTF8.GetString($id3, $d + 1, $fsz - 1) -split "`0"
                    if ($txt.Count -ge 2 -and $txt[0] -match 'RATING') {
                        $k = "ID3 TXXX:" + $txt[0].ToUpperInvariant()
                        if (-not $tags.ContainsKey($k)) { $tags[$k] = @() }
                        $tags[$k] += $txt[1]
                    }
                }
                $o = $d + $fsz
            }
            $magic = $br.ReadBytes(4)
        }
        if ([System.Text.Encoding]::ASCII.GetString($magic) -ne 'fLaC') { return $null }
        $last = $false
        while (-not $last) {
            $h = $br.ReadBytes(4)
            if ($h.Length -lt 4) { break }
            $last = ($h[0] -band 0x80) -ne 0
            $type = $h[0] -band 0x7F
            $len  = ([int]$h[1] -shl 16) -bor ([int]$h[2] -shl 8) -bor [int]$h[3]
            if ($type -ne 4) { [void]$fs.Seek($len, 'Current'); continue }   # skip pictures etc.
            $block = $br.ReadBytes($len)
            $o = 0
            $vlen = [BitConverter]::ToUInt32($block, $o); $o += 4 + $vlen   # vendor string
            $n = [BitConverter]::ToUInt32($block, $o); $o += 4
            for ($i = 0; $i -lt $n -and $o -lt $block.Length; $i++) {
                $clen = [BitConverter]::ToUInt32($block, $o); $o += 4
                $kv = [System.Text.Encoding]::UTF8.GetString($block, $o, $clen); $o += $clen
                $eq = $kv.IndexOf('=')
                if ($eq -gt 0) {
                    $k = $kv.Substring(0, $eq).ToUpperInvariant()
                    if (-not $tags.ContainsKey($k)) { $tags[$k] = @() }
                    $tags[$k] += $kv.Substring($eq + 1)
                }
            }
            break
        }
    } finally { $fs.Close() }
    return $tags
}

# Same conversion as jukebox_library.py
function Convert-PopmStars([double]$n) {
    if ($n -le 0) { return 0 }
    foreach ($p in @(@(31,1), @(95,2), @(159,3), @(223,4))) { if ($n -le $p[0]) { return $p[1] } }
    return 5
}
function Convert-Stars([string]$text, [bool]$fraction) {
    $t = ($text -split "`0")[0].Trim()
    $v = 0.0
    if (-not [double]::TryParse($t, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$v)) { return $null }
    if ($v -le 0) { return 0 }
    if ($fraction -or ($v -le 1 -and $t.Contains('.'))) { return [math]::Round($v * 5, 2) }
    if ($v -le 5)   { return $v }
    if ($v -le 10)  { return $v / 2 }
    if ($v -le 100) { return $v / 20 }
    if ($v -le 255) { return Convert-PopmStars $v }
    return $null
}

$files = Get-ChildItem -LiteralPath $Path -Recurse -File -Filter *.flac -ErrorAction SilentlyContinue
$total = $files.Count
Write-Host "Reading $total FLAC files under $Path ..."
$rows = New-Object System.Collections.Generic.List[object]
$i = 0
foreach ($f in $files) {
    $i++
    if ($i % 250 -eq 0) { Write-Progress -Activity "Reading tags" -Status "$i of $total" -PercentComplete ($i * 100 / $total) }
    try { $tags = Get-FlacTags $f.FullName } catch { $tags = $null }
    if ($null -eq $tags) { $rows.Add([pscustomobject]@{ File = $f.FullName; RatingTags = 'UNREADABLE'; Stars = $null }); continue }
    $ratingKeys = $tags.Keys | Where-Object { $_ -like '*RATING*' -or $_ -like 'ID3 POPM*' } | Sort-Object
    $raw = ($ratingKeys | ForEach-Object { "$_=" + ($tags[$_] -join '|') }) -join '; '
    $stars = @()
    foreach ($k in @('RATING', 'RATING WMP', 'RATING MM')) {
        if ($tags.ContainsKey($k)) { foreach ($v in $tags[$k]) { $s = Convert-Stars $v $false; if ($null -ne $s) { $stars += $s } } }
    }
    foreach ($k in $tags.Keys | Where-Object { $_ -like 'ID3 POPM*' }) { foreach ($v in $tags[$k]) { $stars += Convert-PopmStars ([double]$v) } }
    foreach ($k in @('ID3 TXXX:RATING')) { if ($tags.ContainsKey($k)) { foreach ($v in $tags[$k]) { $s = Convert-Stars $v $false; if ($null -ne $s) { $stars += $s } } } }
    # FMPS_RATING wins when present (same as jukebox_library.py)
    if ($tags.ContainsKey('FMPS_RATING')) {
        $fm = @(); foreach ($v in $tags['FMPS_RATING']) { $s = Convert-Stars $v $true; if ($null -ne $s) { $fm += $s } }
        if ($fm.Count) { $stars = $fm }
    }
    $best = if ($stars.Count) { ($stars | Measure-Object -Maximum).Maximum } else { $null }
    $rows.Add([pscustomobject]@{ File = $f.FullName; RatingTags = $raw; Stars = $best })
}
Write-Progress -Activity "Reading tags" -Completed

Write-Host "`n=== Raw rating tags found in the files (top 20) ==="
$rows | Group-Object { if ($_.RatingTags) { $_.RatingTags } else { '(no rating tag)' } } |
    Sort-Object Count -Descending | Select-Object -First 20 | ForEach-Object { Write-Host ('{0,7}  {1}' -f $_.Count, $_.Name) }

Write-Host "=== Stars the jukebox script sees ==="
$rows | Group-Object { if ($null -eq $_.Stars) { 'unrated' } else { "$($_.Stars) stars" } } |
    Sort-Object Name | ForEach-Object { Write-Host ('{0,7}  {1}' -f $_.Count, $_.Name) }

$picked = ($rows | Where-Object { $_.Stars -ge 4 }).Count
Write-Host "Would be picked at 4+ stars: $picked of $total"

Write-Host "`n=== 5 example files per star value ==="
$rows | Where-Object { $null -ne $_.Stars } | Group-Object Stars | Sort-Object Name | ForEach-Object {
    Write-Host "-- $($_.Name) stars"
    $_.Group | Select-Object -First 5 | ForEach-Object { Write-Host "   $($_.File)   [$($_.RatingTags)]" }
}

if ($Csv) {
    $rows | Export-Csv -LiteralPath $Csv -NoTypeInformation -Encoding UTF8
    Write-Host "`nPer-file results saved to $Csv"
}
