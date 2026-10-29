# Iniciar OpenCode Server 2.1.2 usando la clave del .env local.
# Guardar este archivo en la raiz del repositorio, junto a .env.
# No imprime la clave ni modifica la configuracion global de OpenCode.

$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$envFile = Join-Path $projectRoot '.env'
$opencodeProbe = Join-Path $env:TEMP 'opencode-2.1.2-isolated'
$opencodeExe = Join-Path $opencodeProbe 'node_modules/@opencode/cli/bin/opencode.exe'

if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
    throw 'No se encontro .env en la misma carpeta que iniciar-opencode.ps1.'
}

if (-not (Test-Path -LiteralPath $opencodeExe -PathType Leaf)) {
    throw "No se encontro OpenCode 2.1.2 en la instalacion temporal. Instala una vez con: npm install --prefix `"$opencodeProbe`" --no-audit --no-fund @opencode/cli@2.1.2"
}

# Buscar solo esta variable; NO ejecutar ni importar el contenido del .env.
$passwordLines = @(Get-Content -LiteralPath $envFile -Encoding UTF8 |
    Where-Object { $_ -match '^\s*OPENCODE_SERVER_PASSWORD\s*=' })

if ($passwordLines.Count -eq 0) {
    throw 'Falta OPENCODE_SERVER_PASSWORD en .env.'
}

# Si aparece varias veces, tomar la ultima definicion.
$passwordLine = $passwordLines[-1]
$parsed = [regex]::Match($passwordLine, '^\s*OPENCODE_SERVER_PASSWORD\s*=\s*(.*)$')
$password = $parsed.Groups[1].Value.Trim()

# Admitir valores encerrados entre comillas simples o dobles.
if ($password.Length -ge 2) {
    if (($password.StartsWith('"') -and $password.EndsWith('"')) -or
        ($password.StartsWith("'") -and $password.EndsWith("'"))) {
        $password = $password.Substring(1, $password.Length - 2)
    }
}

if ([string]::IsNullOrWhiteSpace($password) -or $password -match '^<.*>$') {
    throw 'OPENCODE_SERVER_PASSWORD esta vacia o contiene un valor de ejemplo. Corrige el .env.'
}

# No iniciar un segundo servidor sobre el mismo puerto.
$existingListener = Get-NetTCPConnection -LocalPort 4096 -State Listen -ErrorAction SilentlyContinue
if ($existingListener) {
    throw 'El puerto 4096 ya tiene un servidor escuchando. Detenlo antes de iniciar otra instancia de OpenCode.'
}

# El password es visible solo como variable de entorno del proceso local y sus hijos.
# Al finalizar, restaurar el valor previo para no dejarlo expuesto en la terminal.
$previousPassword = [Environment]::GetEnvironmentVariable('OPENCODE_SERVER_PASSWORD', 'Process')
try {
    [Environment]::SetEnvironmentVariable('OPENCODE_SERVER_PASSWORD', $password, 'Process')
    Write-Host 'Iniciando OpenCode Server 2.1.2 en http://127.0.0.1:4096 ...'
    Write-Host 'Detener con Ctrl+C. Conservar esta terminal abierta mientras usas el agente.'
    & $opencodeExe serve --hostname 127.0.0.1 --port 4096
    if ($LASTEXITCODE -ne 0) {
        throw "OpenCode termino con codigo $LASTEXITCODE."
    }
}
finally {
    [Environment]::SetEnvironmentVariable('OPENCODE_SERVER_PASSWORD', $previousPassword, 'Process')
    $password = $null
    $passwordLine = $null
    $passwordLines = $null
}
