# Inicia todo el entorno local del proyecto Historias de Usuario con un solo comando:
#   1) OpenCode Server  (puerto 4096)
#   2) Backend FastAPI  (puerto 8000)
#   3) Frontend Vite    (puerto 3000, abre el navegador)
# Cada servicio se abre en su propia ventana de PowerShell para ver sus mensajes.
#
# Uso (desde la raiz del repositorio):
#   .\scripts\entorno\iniciar-entorno.ps1              # inicia lo que no este corriendo
#   .\scripts\entorno\iniciar-entorno.ps1 -Reiniciar   # cierra lo que use esos puertos y vuelve a iniciar todo
#   npm run iniciar                 # equivalente a la primera forma
# Solo usa caracteres ASCII para que Windows PowerShell 5.1 lo lea bien. No imprime secretos.

param(
    [switch]$Reiniciar
)

$ErrorActionPreference = 'Stop'
# Este script vive en scripts\entorno; la raiz del repositorio esta dos niveles arriba.
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $root

$pythonExe = Join-Path $root 'agentes\analista\.venv\Scripts\python.exe'
$opencodeExe = Join-Path $env:TEMP 'opencode-2.1.2-isolated\node_modules\@opencode\cli\bin\opencode.exe'
$envFile = Join-Path $root '.env'
$healthUrl = 'http://127.0.0.1:8000/api/analista/health'

function Write-Step([string]$text) { Write-Host "==> $text" -ForegroundColor Cyan }
function Write-Ok([string]$text) { Write-Host "    OK  $text" -ForegroundColor Green }
function Write-Warn([string]$text) { Write-Host "    !!  $text" -ForegroundColor Yellow }

function Get-PortOwner([int]$port) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) { return $listener.OwningProcess }
    return $null
}

function Stop-PortOwner([int]$port) {
    $listeners = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    foreach ($item in $listeners) {
        Stop-Process -Id $item.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

function Wait-Port([int]$port, [int]$seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        if (Get-PortOwner $port) { return $true }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

function Start-ServiceWindow([string]$title, [string]$command) {
    # Ventana nueva que se queda abierta (-NoExit) y muestra el titulo del servicio.
    $inner = "`$Host.UI.RawUI.WindowTitle = '$title'; $command"
    # Se pasa una sola cadena con el comando entre comillas dobles: asi las rutas con espacios no se parten.
    $argumentLine = "-NoExit -ExecutionPolicy Bypass -Command `"$inner`""
    Start-Process -FilePath 'powershell.exe' -WorkingDirectory $root -ArgumentList $argumentLine | Out-Null
}

# ---------------------------------------------------------------- Verificaciones
Write-Step 'Verificando requisitos'
$missing = @()
if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) { $missing += 'Falta el archivo .env en la raiz. Copia agentes\analista\.env.example como .env y completalo.' }
if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) { $missing += 'Falta el entorno de Python. Ejecuta: py -3.12 -m venv agentes\analista\.venv ; luego pip install -r agentes\analista\requirements.txt' }
if (-not (Test-Path -LiteralPath $opencodeExe -PathType Leaf)) { $missing += "Falta OpenCode 2.1.2. Ejecuta: npm install --prefix `"$env:TEMP\opencode-2.1.2-isolated`" --no-audit --no-fund @opencode/cli@2.1.2" }
if ($missing.Count -gt 0) {
    $missing | ForEach-Object { Write-Warn $_ }
    throw 'Corrige lo anterior y vuelve a ejecutar .\scripts\entorno\iniciar-entorno.ps1'
}
if (-not (Test-Path -LiteralPath (Join-Path $root 'node_modules'))) {
    Write-Step 'Instalando dependencias del frontend (npm install)'
    & npm install
}
Write-Ok 'Requisitos listos'

# Aviso (no bloquea) si OpenCode Go no esta autenticado.
try {
    $auth = (& $opencodeExe auth list 2>&1 | Out-String)
    if ($auth -match 'No authenticated') {
        Write-Warn 'OpenCode no tiene proveedor autenticado. Ejecuta una vez: & "$env:TEMP\opencode-2.1.2-isolated\node_modules\@opencode\cli\bin\opencode.exe" auth login'
    }
}
catch {
    Write-Warn "No se pudo consultar la autenticacion de OpenCode: $($_.Exception.Message)"
}

# ---------------------------------------------------------------- Puertos
$services = @(
    @{ Name = 'OpenCode'; Port = 4096 },
    @{ Name = 'Backend';  Port = 8000 },
    @{ Name = 'Frontend'; Port = 3000 }
)
if ($Reiniciar) {
    Write-Step 'Cerrando servicios anteriores'
    foreach ($service in $services) { Stop-PortOwner $service.Port }
    Start-Sleep -Seconds 2
}

# ---------------------------------------------------------------- Inicio en orden
Write-Step 'Iniciando OpenCode (puerto 4096)'
if (Get-PortOwner 4096) {
    Write-Warn 'El puerto 4096 ya esta en uso: se reutiliza. Si el agente no carga, ejecuta .\scripts\entorno\iniciar-entorno.ps1 -Reiniciar'
}
else {
    Start-ServiceWindow 'OpenCode' "& '.\scripts\entorno\iniciar-servidor-opencode.ps1'"
    if (Wait-Port 4096 45) { Write-Ok 'OpenCode escuchando en 4096' } else { Write-Warn 'OpenCode no respondio en 45 s. Revisa su ventana.' }
}

Write-Step 'Iniciando backend (puerto 8000)'
if (Get-PortOwner 8000) {
    Write-Warn 'El puerto 8000 ya esta en uso: se reutiliza. Si cambiaste el .env, ejecuta .\scripts\entorno\iniciar-entorno.ps1 -Reiniciar'
}
else {
    $backendCommand = "& '$pythonExe' -m uvicorn agentes.analista.api.main:app --host 127.0.0.1 --port 8000 --workers 1"
    Start-ServiceWindow 'Backend FastAPI' $backendCommand
    if (Wait-Port 8000 60) { Write-Ok 'Backend escuchando en 8000' } else { Write-Warn 'El backend no respondio en 60 s. Revisa su ventana.' }
}

Write-Step 'Iniciando frontend (puerto 3000)'
if (Get-PortOwner 3000) {
    Write-Warn 'El puerto 3000 ya esta en uso: se reutiliza.'
}
else {
    Start-ServiceWindow 'Frontend Vite' 'npm run dev'
    if (Wait-Port 3000 45) { Write-Ok 'Frontend escuchando en 3000' } else { Write-Warn 'El frontend no respondio en 45 s. Revisa su ventana.' }
}

# ---------------------------------------------------------------- Estado final
Write-Step 'Comprobando el estado del agente'
$status = $null
for ($attempt = 1; $attempt -le 10; $attempt++) {
    try {
        $status = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 8
        break
    }
    catch {
        Start-Sleep -Seconds 2
    }
}
if ($null -eq $status) {
    Write-Warn 'El backend no devolvio el estado. Revisa la ventana del backend.'
}
else {
    $opencodeState = $status.checks.opencode.status
    $color = if ($status.status -eq 'ready') { 'Green' } else { 'Yellow' }
    Write-Host "    Estado general: $($status.status) | OpenCode: $opencodeState | MCP: $($status.checks.mcp.status)" -ForegroundColor $color
    if ($opencodeState -ne 'ok') {
        Write-Warn "Motivo: $($status.checks.opencode.rejection_reason)"
    }
}

Write-Host ''
Write-Host 'Listo. App: http://localhost:3000  |  Para cerrar todo: .\scripts\entorno\detener-entorno.ps1' -ForegroundColor Cyan
