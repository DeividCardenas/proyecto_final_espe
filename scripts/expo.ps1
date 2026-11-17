<#
.SYNOPSIS
  Enciende la demo para la exposición: levanta la plataforma con Docker, abre un túnel
  público gratuito de Cloudflare hacia http://localhost y publica su URL en la página fija
  del proyecto (site/demo.json → GitHub Pages), que es a donde apunta el QR del póster.

.USO
  En PowerShell, desde la raíz del repositorio:
      powershell -ExecutionPolicy Bypass -File scripts\expo.ps1
  Para apagar: Ctrl+C en esta ventana (la página vuelve a mostrar "demo apagada").

  -NoPublish   abre el túnel pero no hace commit/push de site/demo.json.

.REQUISITOS
  Docker Desktop, git con permiso de push a master, e internet. cloudflared se instala solo
  con winget si falta. El túnel rápido (trycloudflare.com) no necesita cuenta; su URL cambia
  cada vez que se enciende, por eso se publica en demo.json y el QR apunta a la página fija.
#>
param([switch]$NoPublish)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Publish-DemoUrl([string]$url) {
    if ($NoPublish) { return }
    if ((git rev-parse --abbrev-ref HEAD) -ne "master") {
        Write-Host "  No estás en la rama master: no se publica demo.json. URL: $url" -ForegroundColor Yellow
        return
    }
    git pull --ff-only origin master | Out-Null
    $now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $u = if ($url) { "`"$url`"" } else { "null" }
    $t = if ($url) { "`"$now`"" } else { "null" }
    $json = "{`n  `"url`": $u,`n  `"updated_at`": $t,`n  `"note`": `"Lo actualiza scripts/expo.ps1 al encender el túnel desde el PC de la exposición.`"`n}`n"
    [IO.File]::WriteAllText((Join-Path (Get-Location) "site\demo.json"), $json, (New-Object Text.UTF8Encoding $false))
    git add site/demo.json | Out-Null
    $msg = if ($url) { "chore(demo): demo en vivo encendida" } else { "chore(demo): demo en vivo apagada" }
    git commit -m $msg -- site/demo.json | Out-Null
    git push origin HEAD:master | Out-Null
    Write-Host "  demo.json publicado; GitHub Pages se actualiza en 1-2 minutos." -ForegroundColor DarkGray
}

Write-Host "1/4 Levantando la plataforma con Docker..." -ForegroundColor Cyan
docker compose up -d | Out-Null
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    try { if ((Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://localhost/health).StatusCode -eq 200) { $ok = $true; break } } catch {}
    Start-Sleep -Seconds 3
}
if (-not $ok) { throw "La plataforma no respondió en http://localhost/health. Revisa 'docker compose ps'." }
Write-Host "  http://localhost responde." -ForegroundColor Green

Write-Host "2/4 Verificando cloudflared..." -ForegroundColor Cyan
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements | Out-Null
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) { throw "No se pudo instalar cloudflared. Instálalo con: winget install Cloudflare.cloudflared" }
}

Write-Host "3/4 Abriendo el túnel público..." -ForegroundColor Cyan
$log = Join-Path $env:TEMP "cloudflared-expo.log"
Remove-Item $log -ErrorAction SilentlyContinue
$proc = Start-Process cloudflared -ArgumentList "tunnel --no-autoupdate --url http://localhost:80" -RedirectStandardError $log -PassThru -WindowStyle Hidden
$url = $null
for ($i = 0; $i -lt 40 -and -not $url; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $log) { $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1
        if ($m) { $url = $m.Matches[0].Value } }
}
if (-not $url) { Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue; throw "No se obtuvo la URL del túnel. Revisa $log" }

Write-Host "4/4 Publicando la URL en la página del proyecto..." -ForegroundColor Cyan
Publish-DemoUrl $url

Write-Host ""
Write-Host "  DEMO EN VIVO: $url" -ForegroundColor Green
Write-Host "  Página del QR: https://deividcardenas.github.io/proyecto_final_espe/" -ForegroundColor Green
Write-Host "  Deja esta ventana abierta. Ctrl+C para apagar." -ForegroundColor Yellow
try {
    while (-not $proc.HasExited) { Start-Sleep -Seconds 5 }
    Write-Host "El túnel se cerró solo. Vuelve a ejecutar el script." -ForegroundColor Red
} finally {
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue }
    Write-Host "Apagando: la página vuelve a mostrar 'demo apagada'." -ForegroundColor Cyan
    try { Publish-DemoUrl $null } catch { Write-Host "  No se pudo publicar demo.json: $_" -ForegroundColor Red }
}
