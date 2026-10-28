[CmdletBinding()]
param(
    [string]$BinaryPath = (Join-Path $env:TEMP 'spec002-t001-opencode/node_modules/opencode-windows-x64/bin/opencode.exe'),
    [ValidateRange(5, 60)]
    [int]$ObserveSeconds = 20
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $BinaryPath -PathType Leaf)) {
    throw "No se encontró el binario OpenCode en: $BinaryPath"
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runRoot = Join-Path $env:TEMP "spec002-t001-diagnose-$stamp"
$profileRoot = Join-Path $runRoot 'profile'
$appDataRoot = Join-Path $runRoot 'appdata'
$localAppDataRoot = Join-Path $runRoot 'localappdata'
$outputPath = Join-Path $runRoot 'stdout.log'
$errorPath = Join-Path $runRoot 'stderr.log'
$summaryPath = Join-Path $runRoot 'diagnostic.json'

New-Item -ItemType Directory -Path $profileRoot, $appDataRoot, $localAppDataRoot | Out-Null

$listenerProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listenerProbe.Start()
$port = ([System.Net.IPEndPoint]$listenerProbe.LocalEndpoint).Port
$listenerProbe.Stop()

$arguments = @('serve', '--hostname', '127.0.0.1', '--port', [string]$port, '--print-logs')
$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = (Resolve-Path -LiteralPath $BinaryPath).Path
$startInfo.Arguments = ($arguments -join ' ')
$startInfo.WorkingDirectory = $runRoot
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true

# Use a minimal child environment so provider credentials cannot be inherited or recorded.
$startInfo.EnvironmentVariables.Clear()
$startInfo.EnvironmentVariables['PATH'] = "$env:SystemRoot\System32;$env:SystemRoot"
$startInfo.EnvironmentVariables['SYSTEMROOT'] = $env:SystemRoot
$startInfo.EnvironmentVariables['WINDIR'] = $env:SystemRoot
$startInfo.EnvironmentVariables['TEMP'] = $runRoot
$startInfo.EnvironmentVariables['TMP'] = $runRoot
$startInfo.EnvironmentVariables['USERPROFILE'] = $profileRoot
$startInfo.EnvironmentVariables['HOME'] = $profileRoot
$startInfo.EnvironmentVariables['APPDATA'] = $appDataRoot
$startInfo.EnvironmentVariables['LOCALAPPDATA'] = $localAppDataRoot
$startInfo.EnvironmentVariables['XDG_CONFIG_HOME'] = (Join-Path $runRoot 'xdg-config')
$startInfo.EnvironmentVariables['XDG_DATA_HOME'] = (Join-Path $runRoot 'xdg-data')

$binaryHash = (Get-FileHash -LiteralPath $startInfo.FileName -Algorithm SHA256).Hash
$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $startInfo
$startedAt = [DateTimeOffset]::UtcNow
$termination = 'process_exit'
$samples = [System.Collections.Generic.List[object]]::new()
$stdoutTask = $null
$stderrTask = $null

if (-not $process.Start()) {
    throw 'Windows no pudo iniciar el proceso OpenCode.'
}

$pidLaunched = $process.Id
$stdoutTask = $process.StandardOutput.ReadToEndAsync()
$stderrTask = $process.StandardError.ReadToEndAsync()
$deadline = [DateTimeOffset]::UtcNow.AddSeconds($ObserveSeconds)

while ([DateTimeOffset]::UtcNow -lt $deadline) {
    $process.Refresh()
    $hasExited = $process.HasExited
    $sample = [ordered]@{
        captured_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        pid = $pidLaunched
        state = if ($hasExited) { 'exited' } else { 'running' }
        exit_code = if ($hasExited) { $process.ExitCode } else { $null }
        working_set_bytes = if ($hasExited) { $null } else { $process.WorkingSet64 }
        cpu_seconds = if ($hasExited) { $null } else { $process.TotalProcessorTime.TotalSeconds }
        listener_accepting_loopback = $false
    }

    if (-not $hasExited) {
        try {
            $client = [System.Net.Sockets.TcpClient]::new()
            $connect = $client.ConnectAsync('127.0.0.1', $port)
            if ($connect.Wait(150)) { $sample.listener_accepting_loopback = $client.Connected }
            $client.Dispose()
        } catch {
            $sample.listener_accepting_loopback = $false
        }
    }
    $samples.Add([pscustomobject]$sample)

    if ($hasExited) { break }
    Start-Sleep -Milliseconds 500
}

$process.Refresh()
if (-not $process.HasExited) {
    $termination = 'diagnostic_timeout_process_stopped'
    $process.Kill()
    $process.WaitForExit()
}
$process.WaitForExit()
$endedAt = [DateTimeOffset]::UtcNow
$stdoutRaw = $stdoutTask.GetAwaiter().GetResult()
$stderrRaw = $stderrTask.GetAwaiter().GetResult()

function Protect-LogText([string]$Text) {
    $safe = $Text
    $userProfile = [regex]::Escape($env:USERPROFILE)
    if ($userProfile) { $safe = [regex]::Replace($safe, $userProfile, '<USERPROFILE>', 'IgnoreCase') }
    $safe = [regex]::Replace($safe, '(?i)(authorization\s*[:=]\s*(?:bearer|basic)\s+)\S+', '$1<redacted>')
    $safe = [regex]::Replace($safe, '(?i)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\b\s*[:=]\s*)("[^"]*"|''[^'']*''|[^\s,;]+)', '$1<redacted>')
    $safe = [regex]::Replace($safe, '(?i)\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,})\b', '<redacted-token>')
    return $safe
}

$stdoutSafe = Protect-LogText $stdoutRaw
$stderrSafe = Protect-LogText $stderrRaw
[System.IO.File]::WriteAllText($outputPath, $stdoutSafe, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText($errorPath, $stderrSafe, [System.Text.UTF8Encoding]::new($false))

$internalLogDirectory = Join-Path $runRoot 'xdg-data/opencode/log'
$internalLogs = @(Get-ChildItem -LiteralPath $internalLogDirectory -Filter '*.log' -File -ErrorAction SilentlyContinue)
foreach ($internalLog in $internalLogs) {
    $internalSafe = Protect-LogText (Get-Content -Raw -LiteralPath $internalLog.FullName)
    [System.IO.File]::WriteAllText($internalLog.FullName, $internalSafe, [System.Text.UTF8Encoding]::new($false))
}

$summary = [ordered]@{
    version_expected = '0.2.27'
    binary_path = $startInfo.FileName
    binary_sha256 = $binaryHash
    working_directory = $runRoot
    argv = @($startInfo.FileName) + $arguments
    hostname = '127.0.0.1'
    port = $port
    credentials_inherited = $false
    prompt_or_custom_config_used = $false
    pid = $pidLaunched
    process_name = [System.IO.Path]::GetFileNameWithoutExtension($startInfo.FileName)
    started_at_utc = $startedAt.ToString('o')
    ended_at_utc = $endedAt.ToString('o')
    elapsed_seconds = [math]::Round(($endedAt - $startedAt).TotalSeconds, 3)
    exit_code = $process.ExitCode
    termination = $termination
    listener_ever_accepted_loopback = [bool]($samples | Where-Object { $_.listener_accepting_loopback } | Select-Object -First 1)
    process_samples = @($samples)
    stdout_log = $outputPath
    stderr_log = $errorPath
    internal_logs = @($internalLogs | Select-Object -ExpandProperty FullName)
}

$json = $summary | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($summaryPath, $json, [System.Text.UTF8Encoding]::new($false))

[pscustomobject]@{
    Result = if ($summary.listener_ever_accepted_loopback) { 'LISTENER_DETECTED' } else { 'NO_LISTENER' }
    ExitCode = $summary.exit_code
    Termination = $termination
    PID = $pidLaunched
    Port = $port
    StdoutLog = $outputPath
    StderrLog = $errorPath
    Summary = $summaryPath
} | Format-List
