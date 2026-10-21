<#
.SYNOPSIS
  Instala (la primera vez) y abre la app de estadística en Chrome.
.DESCRIPTION
  1. Verifica/instala Python 3.12 y MiKTeX (pdflatex) con winget.
  2. Crea un entorno virtual en .\.venv e instala requirements.txt.
  3. Levanta Streamlit y abre Chrome en la página.
  Cerrar esta ventana (o Ctrl+C) detiene la app.
.PARAMETER Red
  Expone la app en la red local para abrirla desde otro equipo (ej. proyector).
.PARAMETER Puerto
  Puerto preferido (por defecto 8501; si está ocupado usa el siguiente libre).
.PARAMETER SinLatex
  No instala MiKTeX (el PDF directo no funcionará; queda la opción .zip para Overleaf).
#>
param(
    [switch]$Red,
    [int]$Puerto = 8501,
    [switch]$SinLatex
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Info($m) { Write-Host "[app] $m" -ForegroundColor Cyan }
function Aviso($m) { Write-Host "[app] $m" -ForegroundColor Yellow }

function Actualizar-Path {
    $maquina = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $usuario = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$maquina;$usuario"
    foreach ($p in @(
        "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64",
        "$env:ProgramFiles\MiKTeX\miktex\bin\x64"
    )) { if ((Test-Path $p) -and ($env:Path -notlike "*$p*")) { $env:Path += ";$p" } }
}

function Tiene-Winget { [bool](Get-Command winget -ErrorAction SilentlyContinue) }

function Instalar-Winget($id, $nombre) {
    if (-not (Tiene-Winget)) {
        throw "No encontré winget para instalar $nombre. Instálalo a mano (id: $id) y vuelve a ejecutar."
    }
    Info "Instalando $nombre con winget (puede tardar unos minutos)..."
    winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements | Out-Host
    Actualizar-Path
}

# ---------------------------------------------------------------- Python
function Probar-Python([string]$exe, [string[]]$pre) {
    # Devuelve la ruta real de un Python >= 3.10, o $null. Ignora stubs y launchers sin Python.
    $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    try {
        $out = & $exe @pre -c "import sys; print(sys.version_info[0]*100+sys.version_info[1]); print(sys.executable)" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
        $l = @($out | ForEach-Object { "$_".Trim() } | Where-Object { $_ })
        if ($l.Count -ge 2 -and ($l[0] -match '^\d+$') -and [int]$l[0] -ge 310 -and (Test-Path $l[1])) { return $l[1] }
    } catch { } finally { $ErrorActionPreference = $old }
    return $null
}
function Buscar-Python {
    foreach ($c in @(@{ e = "py"; a = @("-3") }, @{ e = "python"; a = @() }, @{ e = "python3"; a = @() })) {
        if (Get-Command $c.e -ErrorAction SilentlyContinue) {
            $r = Probar-Python $c.e $c.a
            if ($r) { return $r }
        }
    }
    foreach ($d in Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending) {
        $r = Probar-Python (Join-Path $d.FullName "python.exe") @()
        if ($r) { return $r }
    }
    return $null
}

Actualizar-Path
$script:PyExe = Buscar-Python
if (-not $script:PyExe) {
    Instalar-Winget "Python.Python.3.12" "Python 3.12"
    $script:PyExe = Buscar-Python
    if (-not $script:PyExe) { throw "Python se instaló pero no se detecta. Cierra y vuelve a abrir PowerShell y ejecuta de nuevo." }
}
function Run-Py { & $script:PyExe @args }
Info ("Python: " + (& $script:PyExe --version) + "  [" + $script:PyExe + "]")

# ---------------------------------------------------------------- LaTeX
if (-not $SinLatex) {
    if (-not (Get-Command pdflatex -ErrorAction SilentlyContinue)) {
        try {
            Instalar-Winget "MiKTeX.MiKTeX" "MiKTeX (para generar el PDF)"
        } catch {
            Aviso $_.Exception.Message
        }
    }
    if (Get-Command pdflatex -ErrorAction SilentlyContinue) {
        # Que MiKTeX descargue paquetes faltantes sin preguntar (si no, se queda esperando).
        try { & initexmf --set-config-value "[MPM]AutoInstall=1" 2>$null } catch { }
        Info "pdflatex listo."
    } else {
        Aviso "No hay pdflatex: la app funcionará, pero el PDF directo no. Usa el .zip en Overleaf."
    }
}

# ---------------------------------------------------------------- Entorno virtual
$venv = Join-Path $PSScriptRoot ".venv"
$pyVenv = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $pyVenv)) {
    Info "Creando entorno virtual..."
    Run-Py -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual." }
}

$req = Join-Path $PSScriptRoot "requirements.txt"
$marca = Join-Path $venv ".req_hash"
$hash = (Get-FileHash $req -Algorithm SHA256).Hash
if ((-not (Test-Path $marca)) -or ((Get-Content $marca -Raw).Trim() -ne $hash)) {
    Info "Instalando dependencias (solo la primera vez)..."
    & $pyVenv -m pip install --upgrade pip --quiet
    & $pyVenv -m pip install -r $req
    if ($LASTEXITCODE -ne 0) { throw "Falló pip install. Revisa tu conexión a internet." }
    Set-Content -Path $marca -Value $hash
} else {
    Info "Dependencias ya instaladas."
}

# ---------------------------------------------------------------- Puerto libre
function Puerto-Libre($p) {
    $l = $null
    try {
        $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $p)
        $l.Start(); return $true
    } catch { return $false } finally { if ($l) { $l.Stop() } }
}
$p = $Puerto
while (-not (Puerto-Libre $p)) { $p++; if ($p -gt $Puerto + 50) { throw "No hay puertos libres cerca de $Puerto." } }
if ($p -ne $Puerto) { Aviso "El puerto $Puerto está ocupado; uso $p." }
$url = "http://localhost:$p"

# ---------------------------------------------------------------- Streamlit
$dir = if ($Red) { "0.0.0.0" } else { "localhost" }
$argsSt = @("-m", "streamlit", "run", "app.py",
            "--server.headless", "true",
            "--server.port", "$p",
            "--server.address", $dir,
            "--browser.gatherUsageStats", "false")

Info "Iniciando la app..."
$proc = Start-Process -FilePath $pyVenv -ArgumentList $argsSt -WorkingDirectory $PSScriptRoot -NoNewWindow -PassThru

try {
    # Esperar a que el puerto responda (máx. 90 s).
    $listo = $false
    for ($i = 0; $i -lt 90; $i++) {
        if ($proc.HasExited) { throw "Streamlit se cerró al arrancar (revisa los mensajes de arriba)." }
        try {
            $c = New-Object System.Net.Sockets.TcpClient
            $c.Connect("127.0.0.1", $p); $c.Close(); $listo = $true; break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $listo) { throw "La app no respondió en 90 segundos." }

    # Abrir Chrome (o el navegador predeterminado si no está).
    $chrome = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($chrome) { Start-Process $chrome $url } else { Aviso "No encontré Chrome; abro el navegador predeterminado."; Start-Process $url }

    Info "App funcionando en $url"
    if ($Red) {
        $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
               Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
               Select-Object -ExpandProperty IPAddress
        foreach ($ip in $ips) { Info "En la red local: http://${ip}:$p" }
        Aviso "Si otro equipo no entra, permite el puerto $p en el Firewall de Windows."
    }
    Info "Cierra esta ventana o presiona Ctrl+C para detenerla."
    $proc.WaitForExit()
}
finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Info "App detenida."
    }
}
