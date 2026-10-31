# Cierra los servicios locales del proyecto (OpenCode 4096, backend 8000, frontend 3000).
# Uso: .\scripts\entorno\detener-entorno.ps1   |   npm run detener
# Solo usa caracteres ASCII para que Windows PowerShell 5.1 lo lea bien.

$ErrorActionPreference = 'Continue'
$services = @(
    @{ Name = 'OpenCode'; Port = 4096 },
    @{ Name = 'Backend';  Port = 8000 },
    @{ Name = 'Frontend'; Port = 3000 }
)

foreach ($service in $services) {
    $listeners = @(Get-NetTCPConnection -LocalPort $service.Port -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -eq 0) {
        Write-Host "$($service.Name) (puerto $($service.Port)): no estaba corriendo" -ForegroundColor DarkGray
        continue
    }
    foreach ($item in $listeners) {
        Stop-Process -Id $item.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Write-Host "$($service.Name) (puerto $($service.Port)): cerrado" -ForegroundColor Green
}
Write-Host 'Las ventanas de PowerShell de cada servicio pueden cerrarse a mano.' -ForegroundColor Cyan
