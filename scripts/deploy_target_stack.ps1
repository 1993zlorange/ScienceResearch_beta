<#
.SYNOPSIS
  Runs, stops, inspects, or cleans the ScienceResearch target stack.
.DESCRIPTION
  Docker Compose is the default runtime. The local-isolated runtime must be selected explicitly and only uses caller-supplied local tools. Dependency synchronization remains lock-file controlled; offline mode is explicit. The script never downloads tools and never reads or writes official data.
.PARAMETER Command
  up, down, status, or clean. up is the default.
.PARAMETER Mode
  docker or local-isolated. docker is the default; no silent fallback is performed.
.PARAMETER DependencySyncMode
  local-isolated only: locked (default) or offline. Both use uv.lock; offline adds uv --offline.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command down -Mode local-isolated
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/deploy_target_stack.ps1 -Command up -Mode local-isolated -DependencySyncMode offline
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('up', 'down', 'status', 'clean')]
    [string]$Command = 'up',

    [ValidateSet('docker', 'local-isolated')]
    [string]$Mode = 'docker',

    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')]
    [string]$RunId = '',

    [string]$RunRoot = 'output/runtime-deploy',

    [ValidateRange(1024, 65535)]
    [int]$WebPort = 8765,

    [ValidateRange(1024, 65535)]
    [int]$ApiPort = 8877,

    [ValidateRange(1024, 65535)]
    [int]$PostgresPort = 55432,

    [ValidateNotNullOrEmpty()]
    [string]$PostgresBinDir = '',

    [ValidateNotNullOrEmpty()]
    [string]$NginxPath = 'nginx.exe',

    [ValidateNotNullOrEmpty()]
    [string]$UvPath = 'uv.exe',

    [ValidateNotNullOrEmpty()]
    [string]$NpmPath = 'npm.cmd',

    [switch]$RemoveIsolatedData,

    [ValidateSet('locked', 'offline')]
    [string]$DependencySyncMode = 'locked'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeProject = 'scienceresearch-target'
$databaseName = 'scienceresearch'
$databaseUser = 'scienceresearch'
$runtimeBase = [System.IO.Path]::GetFullPath((Join-Path $projectRoot 'output/runtime-deploy'))

function Stop-WithContract {
    param(
        [Parameter(Mandatory = $true)][int]$ExitCode,
        [Parameter(Mandatory = $true)][string]$Message
    )
    Write-Error ("DEPLOY_TARGET_STACK_EXIT={0}; {1}" -f $ExitCode, $Message)
    exit $ExitCode
}

function Resolve-ExecutablePath {
    param(
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][string]$ToolName
    )
    try {
        $command = Get-Command $Value -ErrorAction Stop
        if ($null -eq $command -or [string]::IsNullOrWhiteSpace($command.Source)) {
            throw "not found"
        }
        return $command.Source
    }
    catch {
        Stop-WithContract -ExitCode 3 -Message ("Required tool '{0}' was not found. Pass its complete path with the {1} parameter or install it outside this script." -f $ToolName, $ToolName)
    }
}

function Resolve-PostgresTool {
    param([Parameter(Mandatory = $true)][string]$ToolName)
    if (-not [string]::IsNullOrWhiteSpace($PostgresBinDir)) {
        $candidate = Join-Path $PostgresBinDir ($ToolName + '.exe')
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            Stop-WithContract -ExitCode 3 -Message ("PostgreSQL tool '{0}' was not found under PostgresBinDir." -f $ToolName)
        }
        return (Resolve-Path -LiteralPath $candidate).ProviderPath
    }
    return Resolve-ExecutablePath -Value $ToolName -ToolName $ToolName
}

function Test-TcpPortOpen {
    param([Parameter(Mandatory = $true)][int]$Port)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync('127.0.0.1', $Port)
        if ($task.Wait(250) -and $client.Connected) {
            return $true
        }
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Assert-PortsAvailable {
    foreach ($port in @($PostgresPort, $ApiPort, $WebPort)) {
        if (Test-TcpPortOpen -Port $port) {
            Stop-WithContract -ExitCode 4 -Message ("Port {0} is already in use. The script does not stop processes that it did not create." -f $port)
        }
    }
}

function Invoke-Tool {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$Activity
    )
    $displayArguments = ($ArgumentList | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
    if ($WhatIfPreference) {
        Write-Host ("What if: {0}: {1} {2}" -f $Activity, $FilePath, $displayArguments)
        return
    }
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw ("{0} failed with exit code {1}." -f $Activity, $LASTEXITCODE)
    }
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Value
    )
    if ($WhatIfPreference) {
        Write-Host ("What if: write JSON state to {0}" -f (ConvertTo-RelativeProjectPath -Path $Path))
        return
    }
    $Value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function ConvertTo-RelativeProjectPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $prefix = $projectRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    if ($fullPath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $fullPath.Substring($prefix.Length).Replace([System.IO.Path]::DirectorySeparatorChar, '/')
    }
    return $fullPath
}

function Resolve-RunRoot {
    $requested = if ([System.IO.Path]::IsPathRooted($RunRoot)) {
        $RunRoot
    }
    else {
        Join-Path $projectRoot $RunRoot
    }
    $full = [System.IO.Path]::GetFullPath($requested)
    $comparison = [System.StringComparison]::OrdinalIgnoreCase
    $inside = ($full -eq $runtimeBase) -or $full.StartsWith($runtimeBase.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar, $comparison)
    if (-not $inside) {
        Stop-WithContract -ExitCode 2 -Message 'RunRoot must stay inside project output/runtime-deploy.'
    }
    return $full
}

function New-RunDirectory {
    param([Parameter(Mandatory = $true)][string]$Id)
    $base = Resolve-RunRoot
    $path = Join-Path $base $Id
    if ($WhatIfPreference) {
        Write-Host ("What if: create isolated run directory {0}" -f (ConvertTo-RelativeProjectPath -Path $path))
        return $path
    }
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    return $path
}

function Get-StatePath {
    param([Parameter(Mandatory = $true)][string]$Directory)
    return (Join-Path $Directory 'state.json')
}

function Read-State {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    try {
        return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
    }
    catch {
        Stop-WithContract -ExitCode 5 -Message ("Runtime state is invalid: {0}" -f (ConvertTo-RelativeProjectPath -Path $Path))
    }
}

function Find-LatestRunDirectory {
    $base = Resolve-RunRoot
    if (-not (Test-Path -LiteralPath $base -PathType Container)) {
        return $null
    }
    $candidate = Get-ChildItem -LiteralPath $base -Directory |
        Where-Object {
            $candidateStatePath = Get-StatePath -Directory $_.FullName
            if (-not (Test-Path -LiteralPath $candidateStatePath -PathType Leaf)) {
                return $false
            }
            $candidateState = Get-Content -LiteralPath $candidateStatePath -Raw | ConvertFrom-Json
            return ($null -ne $candidateState -and $candidateState.mode -eq $Mode)
        } |
        Sort-Object -Property @{ Expression = { (Get-Item -LiteralPath (Get-StatePath -Directory $_.FullName)).LastWriteTimeUtc }; Descending = $true } |
        Select-Object -First 1
    if ($null -eq $candidate) {
        return $null
    }
    return $candidate.FullName
}

function Test-ProcessAlive {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        return ($null -ne $process -and -not $process.HasExited)
    }
    catch {
        return $false
    }
}

function Wait-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Label,
        [int]$TimeoutSeconds = 180
    )
    if ($WhatIfPreference) {
        Write-Host ("What if: wait for {0} at {1}" -f $Label, $Uri)
        return
    }
    $deadline = [DateTimeOffset]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                return $response
            }
        }
        catch {
        }
        Start-Sleep -Seconds 2
    } while ([DateTimeOffset]::UtcNow -lt $deadline)
    Stop-WithContract -ExitCode 6 -Message ("Timed out waiting for {0} at {1}." -f $Label, $Uri)
}

function Get-RequiredPostgresPassword {
    if (-not [string]::IsNullOrWhiteSpace($env:POSTGRES_PASSWORD)) {
        if ($env:POSTGRES_PASSWORD.Length -lt 8) {
            Stop-WithContract -ExitCode 3 -Message 'POSTGRES_PASSWORD must contain at least 8 characters.'
        }
        return $env:POSTGRES_PASSWORD
    }
    if ($WhatIfPreference) {
        Write-Host 'What if: require POSTGRES_PASSWORD through a masked prompt.'
        return '<prompt-preview>'
    }
    $secureValue = Read-Host -AsSecureString 'POSTGRES_PASSWORD (input is hidden)'
    $plainValue = [System.Net.NetworkCredential]::new([string]::Empty, $secureValue).Password
    if ($plainValue.Length -lt 8) {
        Stop-WithContract -ExitCode 3 -Message 'POSTGRES_PASSWORD must be provided and contain at least 8 characters.'
    }
    return $plainValue
}

function Write-RuntimeEnv {
    param([Parameter(Mandatory = $true)][string]$Directory)
    $metadata = [ordered]@{
        mode = $Mode
        command = $Command
        web_port = $WebPort
        api_port = $ApiPort
        postgres_port = $PostgresPort
        postgres_password = '<redacted>'
        scienceresearch_database_url = '<redacted>'
        generated_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
    }
    Write-JsonFile -Path (Join-Path $Directory 'runtime-env.json') -Value $metadata
}

function Invoke-DockerStack {
    param([Parameter(Mandatory = $true)][string]$Action)
    $docker = Resolve-ExecutablePath -Value 'docker' -ToolName 'docker'
    $arguments = @('compose', '-p', $composeProject)
    switch ($Action) {
        'config' { $arguments += @('config', '--quiet') }
        'up' { $arguments += @('up', '--detach', '--build') }
        'down' { $arguments += @('down', '--remove-orphans') }
        'status' { $arguments += @('ps') }
        default { Stop-WithContract -ExitCode 2 -Message ('Unsupported Docker action {0}.' -f $Action) }
    }
    Invoke-Tool -FilePath $docker -ArgumentList $arguments -Activity ("Docker Compose {0}" -f $Action)
}

function Invoke-DockerClean {
    $docker = Resolve-ExecutablePath -Value 'docker' -ToolName 'docker'
    Invoke-DockerStack -Action 'down'
    if ($RemoveIsolatedData) {
        Invoke-Tool -FilePath $docker -ArgumentList @('compose', '-p', $composeProject, 'down', '--volumes', '--remove-orphans') -Activity 'Remove this Compose project volumes'
    }
}

function New-LocalNginxConfig {
    param(
        [Parameter(Mandatory = $true)][string]$Directory,
        [Parameter(Mandatory = $true)][string]$NginxExecutable
    )
    $nginxDirectory = Split-Path -Parent $NginxExecutable
    $mimeTypes = (Resolve-Path -LiteralPath (Join-Path $nginxDirectory 'conf/mime.types')).ProviderPath
    $webRoot = (Join-Path $projectRoot 'apps/web/dist').Replace('\', '/')
    $includeMime = if (Test-Path -LiteralPath $mimeTypes -PathType Leaf) {
        "include `"$($mimeTypes.Replace('\', '/'))`";"
    }
    else {
        'types { text/html html htm; text/css css; application/javascript js mjs; application/json json; image/svg+xml svg; }'
    }
    $config = @"
worker_processes 1;
pid "$($Directory.Replace('\','/'))/nginx.pid";
daemon off;
error_log "$($Directory.Replace('\','/'))/nginx-error.log" notice;
events { worker_connections 128; }
http {
    $includeMime
    access_log "$($Directory.Replace('\','/'))/nginx-access.log";
    server {
        listen 127.0.0.1:$WebPort;
        server_name 127.0.0.1;
        root "$webRoot";
        index index.html;
        client_max_body_size 100m;
        proxy_connect_timeout 5s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        location = /healthz { proxy_pass http://127.0.0.1:$ApiPort; }
        location = /readyz { proxy_pass http://127.0.0.1:$ApiPort; }
        location = /docs { proxy_pass http://127.0.0.1:$ApiPort; }
        location = /redoc { proxy_pass http://127.0.0.1:$ApiPort; }
        location = /_legacy { proxy_pass http://127.0.0.1:$ApiPort; }
        location ^~ /api/ {
            proxy_http_version 1.1;
            proxy_set_header Host `$host;
            proxy_set_header X-Request-Id `$request_id;
            proxy_pass http://127.0.0.1:$ApiPort;
        }
        location ^~ /_legacy/ {
            proxy_http_version 1.1;
            proxy_set_header Host `$host;
            proxy_set_header X-Request-Id `$request_id;
            proxy_pass http://127.0.0.1:$ApiPort;
        }
        location / { try_files `$uri `$uri/ /index.html; }
    }
}
"@
    foreach ($relativeDirectory in @('logs', 'temp/client_body_temp', 'temp/proxy_temp', 'temp/fastcgi_temp', 'temp/uwsgi_temp', 'temp/scgi_temp')) {
        New-Item -ItemType Directory -Path (Join-Path $Directory $relativeDirectory) -Force | Out-Null
    }
    $path = Join-Path $Directory 'nginx.conf'
    if ($WhatIfPreference) {
        Write-Host ("What if: generate local Nginx config {0}" -f (ConvertTo-RelativeProjectPath -Path $path))
    }
    else {
        [System.IO.File]::WriteAllText($path, $config, [System.Text.UTF8Encoding]::new($false))
    }
    return $path
}

function Stop-LocalStack {
    param([Parameter(Mandatory = $true)][string]$Directory)
    $statePath = Get-StatePath -Directory $Directory
    $state = Read-State -Path $statePath
    if ($null -eq $state) {
        Stop-WithContract -ExitCode 4 -Message ('No local-isolated state exists at {0}.' -f (ConvertTo-RelativeProjectPath -Path $statePath))
    }
    if ($WhatIfPreference) {
        Write-Host ("What if: stop Nginx, FastAPI, and PostgreSQL recorded in {0}" -f (ConvertTo-RelativeProjectPath -Path $statePath))
        return
    }
    $nginxExecutable = Resolve-ExecutablePath -Value $NginxPath -ToolName 'nginx'
    $nginxAlive = $state.pids.nginx -and (Test-ProcessAlive -ProcessId ([int]$state.pids.nginx))
    if ($nginxAlive -and (Test-Path -LiteralPath (Join-Path $Directory 'nginx.conf') -PathType Leaf)) {
        & $nginxExecutable -p $Directory -c nginx.conf -s quit 2>$null
        if ($LASTEXITCODE -ne 0 -and (Test-ProcessAlive -ProcessId ([int]$state.pids.nginx))) {
            Stop-Process -Id ([int]$state.pids.nginx) -Force -ErrorAction SilentlyContinue
        }
    }
    if ($state.pids.api -and (Test-ProcessAlive -ProcessId ([int]$state.pids.api))) {
        Stop-Process -Id ([int]$state.pids.api) -Force -ErrorAction SilentlyContinue
    }
    $pgCtl = Resolve-PostgresTool -ToolName 'pg_ctl'
    $dataDirectory = Join-Path $Directory 'postgres-data'
    if (Test-Path -LiteralPath $dataDirectory -PathType Container) {
        & $pgCtl -D $dataDirectory -m fast stop
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) {
            throw ("PostgreSQL stop failed with exit code {0}." -f $LASTEXITCODE)
        }
    }
    $state.status = 'stopped'
    $state | Add-Member -NotePropertyName stopped_at_utc -NotePropertyValue ([DateTimeOffset]::UtcNow.ToString('o')) -Force
    Write-JsonFile -Path $statePath -Value $state
}

function Remove-LocalTransientFiles {
    param([Parameter(Mandatory = $true)][string]$Directory)
    if ($WhatIfPreference) {
        Write-Host ("What if: remove transient PID, log, state, and generated Nginx files in {0}" -f (ConvertTo-RelativeProjectPath -Path $Directory))
        return
    }
    foreach ($name in @('nginx.pid', 'nginx-access.log', 'nginx-error.log', 'api.stdout.log', 'api.stderr.log', 'postgres.log', 'nginx.conf', 'state.json', 'health.json', 'runtime-env.json')) {
        $path = Join-Path $Directory $name
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Remove-Item -LiteralPath $path -Force
        }
    }
}

function Remove-LocalIsolatedData {
    param([Parameter(Mandatory = $true)][string]$Directory)
    if (-not $RemoveIsolatedData) {
        return
    }
    if ($WhatIfPreference) {
        Write-Host ("What if: remove only this run's PostgreSQL and artifact directories under {0}" -f (ConvertTo-RelativeProjectPath -Path $Directory))
        return
    }
    $resolvedRoot = [System.IO.Path]::GetFullPath($Directory)
    if (-not (($resolvedRoot -eq $runtimeBase) -or $resolvedRoot.StartsWith($runtimeBase.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase))) {
        Stop-WithContract -ExitCode 2 -Message 'Refusing to remove data outside output/runtime-deploy.'
    }
    foreach ($name in @('postgres-data', 'artifacts')) {
        $target = [System.IO.Path]::GetFullPath((Join-Path $Directory $name))
        if (-not $target.StartsWith($resolvedRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
            Stop-WithContract -ExitCode 2 -Message 'Refusing to remove a path outside the selected run directory.'
        }
        if (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target -Recurse -Force
        }
    }
}

function Get-DockerRunDirectory {
    if (-not [string]::IsNullOrWhiteSpace($RunId)) {
        return (New-RunDirectory -Id $RunId)
    }
    $generated = 'docker-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    return (New-RunDirectory -Id $generated)
}

function Invoke-DockerCommand {
    if ($WhatIfPreference) {
        Write-Host ("What if: validate docker compose, require POSTGRES_PASSWORD, run compose project {0} up --detach --build, then probe http://127.0.0.1:{1}/healthz and /readyz." -f $composeProject, $WebPort)
        return
    }
    $docker = Resolve-ExecutablePath -Value 'docker' -ToolName 'docker'
    Invoke-Tool -FilePath $docker -ArgumentList @('compose', 'version') -Activity 'Check Docker Compose CLI'
    switch ($Command) {
        'up' {
            $directory = Get-DockerRunDirectory
            $postgresPassword = Get-RequiredPostgresPassword
            $previousWebPort = $env:SCIENCERESEARCH_WEB_PORT
            $previousPassword = $env:POSTGRES_PASSWORD
            $env:SCIENCERESEARCH_WEB_PORT = [string]$WebPort
            $env:POSTGRES_PASSWORD = $postgresPassword
            try {
                Invoke-DockerStack -Action 'up'
                $healthUri = "http://127.0.0.1:{0}/healthz" -f $WebPort
                $readyUri = "http://127.0.0.1:{0}/readyz" -f $WebPort
                [void](Wait-HttpEndpoint -Uri $healthUri -Label 'Docker web health')
                [void](Wait-HttpEndpoint -Uri $readyUri -Label 'Docker application readiness')
                $state = [ordered]@{
                    schema_version = 1
                    mode = 'docker'
                    command = 'up'
                    status = 'running'
                    compose_project = $composeProject
                    web_url = "http://127.0.0.1:{0}/" -f $WebPort
                    health_url = $healthUri
                    ready_url = $readyUri
                    created_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
                }
                Write-RuntimeEnv -Directory $directory
                Write-JsonFile -Path (Get-StatePath -Directory $directory) -Value $state
                Write-Host ("ScienceResearch target stack is ready: {0}" -f $state.web_url)
            }
            finally {
                if ($null -ne $previousWebPort) { $env:SCIENCERESEARCH_WEB_PORT = $previousWebPort } else { Remove-Item Env:SCIENCERESEARCH_WEB_PORT -ErrorAction SilentlyContinue }
                if ($null -ne $previousPassword) { $env:POSTGRES_PASSWORD = $previousPassword } else { Remove-Item Env:POSTGRES_PASSWORD -ErrorAction SilentlyContinue }
            }
        }
        'down' {
            Invoke-DockerStack -Action 'down'
            $latest = Find-LatestRunDirectory
            if ($null -ne $latest) {
                $statePath = Get-StatePath -Directory $latest
                $state = Read-State -Path $statePath
                if ($null -ne $state -and $state.mode -eq 'docker') {
                    $state.status = 'stopped'
                    $state.stopped_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
                    Write-JsonFile -Path $statePath -Value $state
                }
            }
        }
        'status' {
            Invoke-DockerStack -Action 'status'
        }
        'clean' {
            Invoke-DockerClean
        }
    }
}

function Invoke-LocalCommand {
    if ($WhatIfPreference) {
        Write-Host ("What if: validate PostgreSQL psql/pg_ctl/initdb/createdb, Nginx, uv, and npm; initialize an isolated cluster; apply Alembic; build Vue; then start FastAPI and Nginx on 127.0.0.1 ports {0}/{1}/{2}." -f $PostgresPort, $ApiPort, $WebPort)
        return
    }
    $pgCtl = Resolve-PostgresTool -ToolName 'pg_ctl'
    $psql = Resolve-PostgresTool -ToolName 'psql'
    $createdb = Resolve-PostgresTool -ToolName 'createdb'
    [void](Resolve-PostgresTool -ToolName 'initdb')
    $initDb = Resolve-PostgresTool -ToolName 'initdb'
    $nginx = Resolve-ExecutablePath -Value $NginxPath -ToolName 'nginx'
    $uv = Resolve-ExecutablePath -Value $UvPath -ToolName 'uv'
    $npm = Resolve-ExecutablePath -Value $NpmPath -ToolName 'npm'
    $selectedDirectory = if (-not [string]::IsNullOrWhiteSpace($RunId)) {
        New-RunDirectory -Id $RunId
    }
    elseif ($Command -eq 'up') {
        New-RunDirectory -Id ('local-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    }
    else {
        Find-LatestRunDirectory
    }

    switch ($Command) {
        'down' {
            if ($null -eq $selectedDirectory) {
                Stop-WithContract -ExitCode 4 -Message 'No local-isolated run was found to stop.'
            }
            Stop-LocalStack -Directory $selectedDirectory
            Write-Host 'Local-isolated target stack stopped. Isolated database data was retained.'
        }
        'status' {
            if ($null -eq $selectedDirectory) {
                Stop-WithContract -ExitCode 4 -Message 'No local-isolated run state was found.'
            }
            $state = Read-State -Path (Get-StatePath -Directory $selectedDirectory)
            if ($null -eq $state) {
                Stop-WithContract -ExitCode 4 -Message 'No local-isolated run state was found.'
            }
            $dataDirectory = Join-Path $selectedDirectory 'postgres-data'
            if (-not $WhatIfPreference) {
                & $pgCtl -D $dataDirectory status
                if ($state.pids.api) { "API process {0}: {1}" -f $state.pids.api, (Test-ProcessAlive -ProcessId ([int]$state.pids.api)) }
                if ($state.pids.nginx) { "Nginx process {0}: {1}" -f $state.pids.nginx, (Test-ProcessAlive -ProcessId ([int]$state.pids.nginx)) }
            }
            else {
                Write-Host ("What if: inspect PostgreSQL, FastAPI, and Nginx state in {0}" -f (ConvertTo-RelativeProjectPath -Path $selectedDirectory))
            }
        }
        'clean' {
            if ($null -eq $selectedDirectory) {
                Stop-WithContract -ExitCode 4 -Message 'No local-isolated run was found to clean.'
            }
            if ((Test-Path -LiteralPath (Get-StatePath -Directory $selectedDirectory) -PathType Leaf) -and ((Read-State -Path (Get-StatePath -Directory $selectedDirectory)).status -ne 'stopped')) {
                Stop-LocalStack -Directory $selectedDirectory
            }
            Remove-LocalIsolatedData -Directory $selectedDirectory
            Remove-LocalTransientFiles -Directory $selectedDirectory
            Write-Host 'Local-isolated transient files removed. Isolated data is retained unless RemoveIsolatedData is explicitly set.'
        }
        'up' {
            if ($null -eq $selectedDirectory) {
                Stop-WithContract -ExitCode 5 -Message 'Could not create local-isolated run directory.'
            }
            $statePath = Get-StatePath -Directory $selectedDirectory
            $existingState = Read-State -Path $statePath
            if ($null -ne $existingState -and $existingState.status -eq 'running') {
                $apiAlive = $existingState.pids.api -and (Test-ProcessAlive -ProcessId ([int]$existingState.pids.api))
                $nginxAlive = $existingState.pids.nginx -and (Test-ProcessAlive -ProcessId ([int]$existingState.pids.nginx))
                if ($apiAlive -and $nginxAlive) {
                    [void](Wait-HttpEndpoint -Uri ("http://127.0.0.1:{0}/readyz" -f $WebPort) -Label 'existing FastAPI readiness')
                    Write-Host ("Local-isolated target stack is already ready: http://127.0.0.1:{0}/" -f $WebPort)
                    exit 0
                }
                Stop-LocalStack -Directory $selectedDirectory
            }
            Assert-PortsAvailable
            $dataDirectory = Join-Path $selectedDirectory 'postgres-data'
            $artifactDirectory = Join-Path $selectedDirectory 'artifacts'
            $postgresLog = Join-Path $selectedDirectory 'postgres.log'
            $apiStdout = Join-Path $selectedDirectory 'api.stdout.log'
            $apiStderr = Join-Path $selectedDirectory 'api.stderr.log'
            if ($WhatIfPreference) {
                Write-Host ("What if: initialize PostgreSQL under {0}" -f (ConvertTo-RelativeProjectPath -Path $dataDirectory))
            }
            elseif (-not (Test-Path -LiteralPath $dataDirectory -PathType Container)) {
                New-Item -ItemType Directory -Path $selectedDirectory -Force | Out-Null
                Invoke-Tool -FilePath $initDb -ArgumentList @('-D', $dataDirectory, '-U', $databaseUser, '--auth=trust', '--encoding=UTF8', '--no-instructions') -Activity 'Initialize isolated PostgreSQL cluster'
            }
            $bootstrapState = [ordered]@{
                schema_version = 1
                mode = 'local-isolated'
                command = 'up'
                status = 'starting'
                pg_ctl_tool = 'resolved-at-start'
                psql_tool = 'resolved-at-start'
                nginx_tool = 'resolved-at-start'
                pids = [ordered]@{ api = $null; nginx = $null }
                web_url = "http://127.0.0.1:{0}/" -f $WebPort
                created_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
            }
            Write-JsonFile -Path $statePath -Value $bootstrapState
            Write-RuntimeEnv -Directory $selectedDirectory
            Invoke-Tool -FilePath $pgCtl -ArgumentList @('-D', $dataDirectory, '-o', ('-p {0} -h 127.0.0.1' -f $PostgresPort), '-l', $postgresLog, '-w', 'start') -Activity 'Start isolated PostgreSQL'
            $databaseUrl = "postgresql://{0}@127.0.0.1:{1}/{2}" -f $databaseUser, $PostgresPort, $databaseName
            $existingDatabase = & $psql --host=127.0.0.1 --port=$PostgresPort --username=$databaseUser --dbname=postgres --tuples-only --no-align --command "SELECT 1 FROM pg_database WHERE datname = '$databaseName'"
            if ($LASTEXITCODE -ne 0) {
                throw 'PostgreSQL database inspection failed.'
            }
            if ([string]::IsNullOrWhiteSpace(($existingDatabase | Out-String).Trim())) {
                Invoke-Tool -FilePath $createdb -ArgumentList @('--host=127.0.0.1', '--port', [string]$PostgresPort, '--username', $databaseUser, $databaseName) -Activity 'Create isolated PostgreSQL database'
            }
            $previousDatabaseUrl = $env:SCIENCERESEARCH_DATABASE_URL
            $previousEnvironment = $env:SCIENCERESEARCH_ENVIRONMENT
            $previousArtifactRoot = $env:SCIENCERESEARCH_ARTIFACT_ROOT
            $env:SCIENCERESEARCH_DATABASE_URL = $databaseUrl
            $env:SCIENCERESEARCH_ENVIRONMENT = 'production'
            $env:SCIENCERESEARCH_ARTIFACT_ROOT = $artifactDirectory
            try {
                if (-not $WhatIfPreference) {
                    New-Item -ItemType Directory -Path $artifactDirectory -Force | Out-Null
                }
                $uvSyncArguments = @('sync', '--locked', '--python', '3.12')
                if ($DependencySyncMode -eq 'offline') {
                    $uvSyncArguments += '--offline'
                }
                Invoke-Tool -FilePath $uv -ArgumentList $uvSyncArguments -Activity "Synchronize Python dependencies ($DependencySyncMode)" 
                Invoke-Tool -FilePath $uv -ArgumentList @('run', 'alembic', '-c', 'database/migrations/alembic.ini', 'upgrade', 'head') -Activity 'Apply Alembic migrations'
                Invoke-Tool -FilePath $npm -ArgumentList @('--workspace', 'apps/web', 'run', 'build') -Activity 'Build Vue web application'
                $nginxConfig = New-LocalNginxConfig -Directory $selectedDirectory -NginxExecutable $nginx
                if ($WhatIfPreference) {
                    Write-Host ("What if: start FastAPI on 127.0.0.1:{0}" -f $ApiPort)
                    Write-Host ("What if: start Nginx on 127.0.0.1:{0}" -f $WebPort)
                }
                else {
                    $apiPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
                    if (-not (Test-Path -LiteralPath $apiPython -PathType Leaf)) { throw 'Locked Python virtual environment was not found after dependency synchronization.' }
                    $apiProcess = Start-Process -FilePath $apiPython -ArgumentList @('-m', 'uvicorn', 'scienceresearch.main:create_app', '--factory', '--host', '127.0.0.1', '--port', [string]$ApiPort) -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $apiStdout -RedirectStandardError $apiStderr -PassThru
                    $bootstrapState.pids.api = $apiProcess.Id
                    Write-JsonFile -Path $statePath -Value $bootstrapState
                    $nginxProcess = Start-Process -FilePath $nginx -ArgumentList @('-p', $selectedDirectory, '-c', 'nginx.conf') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
                    $bootstrapState.pids.nginx = $nginxProcess.Id
                    $bootstrapState.status = 'running'
                    Write-JsonFile -Path $statePath -Value $bootstrapState
                }
                $healthUri = "http://127.0.0.1:{0}/healthz" -f $WebPort
                $readyUri = "http://127.0.0.1:{0}/readyz" -f $WebPort
                [void](Wait-HttpEndpoint -Uri $healthUri -Label 'local Nginx health proxy')
                [void](Wait-HttpEndpoint -Uri $readyUri -Label 'local FastAPI and PostgreSQL readiness')
                $healthEvidence = [ordered]@{
                    healthz = 200
                    readyz = 200
                    checked_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
                }
                Write-JsonFile -Path (Join-Path $selectedDirectory 'health.json') -Value $healthEvidence
                Write-Host ("ScienceResearch local-isolated target stack is ready: {0}" -f $bootstrapState.web_url)
            }
            finally {
                if ($null -ne $previousDatabaseUrl) { $env:SCIENCERESEARCH_DATABASE_URL = $previousDatabaseUrl } else { Remove-Item Env:SCIENCERESEARCH_DATABASE_URL -ErrorAction SilentlyContinue }
                if ($null -ne $previousEnvironment) { $env:SCIENCERESEARCH_ENVIRONMENT = $previousEnvironment } else { Remove-Item Env:SCIENCERESEARCH_ENVIRONMENT -ErrorAction SilentlyContinue }
                if ($null -ne $previousArtifactRoot) { $env:SCIENCERESEARCH_ARTIFACT_ROOT = $previousArtifactRoot } else { Remove-Item Env:SCIENCERESEARCH_ARTIFACT_ROOT -ErrorAction SilentlyContinue }
            }
        }
    }
}

try {
    if ($Mode -eq 'docker') {
        Invoke-DockerCommand
    }
    else {
        Invoke-LocalCommand
    }
    exit 0
}
catch {
    $message = $_.Exception.Message
    if ($message -match '^DEPLOY_TARGET_STACK_EXIT=(\d+); (.*)$') {
        Stop-WithContract -ExitCode ([int]$Matches[1]) -Message $Matches[2]
    }
    Stop-WithContract -ExitCode 5 -Message ("Unhandled command failure: {0}" -f $message)
}
