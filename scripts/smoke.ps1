<#
.SYNOPSIS
  Smoke test the running stack: health endpoints, login as each seeded role, /auth/me,
  GET /internships, GET /analytics/dashboard. Exits non-zero on any failure.
#>
param(
    [string]$Api = 'http://localhost:8000',
    [string]$Web = 'http://localhost:3000'
)

$ErrorActionPreference = 'Stop'
$script:failures = 0
$script:token = $null

function Ok([string]$m)   { Write-Host "[ OK ] $m" -ForegroundColor Green }
function Fail([string]$m) { Write-Host "[FAIL] $m" -ForegroundColor Red; $script:failures++ }

function Check([string]$name, [scriptblock]$body) {
    try { & $body; Ok $name } catch { Fail "$name -> $($_.Exception.Message)" }
}

function Expect-200([string]$url) {
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -ne 200) { throw "HTTP $($r.StatusCode)" }
}

Check 'GET /healthz'    { Expect-200 "$Api/healthz" }
Check 'GET /readyz'     { Expect-200 "$Api/readyz" }
Check 'frontend /'      { Expect-200 "$Web/" }
Check 'frontend /login' { Expect-200 "$Web/login" }
Check 'minio live'      { Expect-200 'http://localhost:9000/minio/health/live' }
Check 'mailpit UI'      { Expect-200 'http://localhost:8025/' }

$users = @(
    @{ role = 'ADMIN';   email = 'admin@campushire.dev';   password = 'Admin@12345' },
    @{ role = 'FACULTY'; email = 'faculty@campushire.dev'; password = 'Faculty@12345' },
    @{ role = 'STUDENT'; email = 'student@campushire.dev'; password = 'Student@12345' },
    @{ role = 'COMPANY'; email = 'company@campushire.dev'; password = 'Company@12345' }
)

foreach ($u in $users) {
    $role = $u.role
    $script:token = $null

    Check "$role login" {
        $body = @{ email = $u.email; password = $u.password } | ConvertTo-Json
        $r = Invoke-RestMethod -Method Post -Uri "$Api/api/v1/auth/login" -ContentType 'application/json' -Body $body
        if (-not $r.access_token) { throw 'no access_token in response' }
        if ($r.user.role -ne $role) { throw "role mismatch: $($r.user.role)" }
        $script:token = $r.access_token
    }
    if (-not $script:token) { continue }
    $h = @{ Authorization = "Bearer $($script:token)" }

    Check "$role GET /auth/me" {
        $me = Invoke-RestMethod -Uri "$Api/api/v1/auth/me" -Headers $h
        if ($me.email -ne $u.email) { throw "unexpected email $($me.email)" }
    }
    Check "$role GET /internships (total > 0)" {
        $p = Invoke-RestMethod -Uri "$Api/api/v1/internships?page_size=5" -Headers $h
        if (-not ($p.total -gt 0)) { throw "total=$($p.total)" }
    }
    Check "$role GET /analytics/dashboard" {
        $d = Invoke-RestMethod -Uri "$Api/api/v1/analytics/dashboard" -Headers $h
        if ($null -eq $d) { throw 'empty response' }
    }
}

Write-Host ''
if ($script:failures -gt 0) {
    Write-Host "Smoke test FAILED ($($script:failures) failure(s))." -ForegroundColor Red
    exit 1
}
Write-Host 'Smoke test passed.' -ForegroundColor Green
exit 0
