<#
.SYNOPSIS
    Policy Validator (Military-Grade v3.0)
    检测：路径、JSON schema、命令白名单、debug 上传等

.DESCRIPTION
    军规级策略验证器，检测以下违规：
    1. 报告文件缺失
    2. JSON schema 校验失败
    3. 命令白名单违规
    4. 产物路径不符合约定
    5. check_mode 未启用
    6. context_manifest_sha 缺失
    
    任何违规 → exit 12 (POLICY_VIOLATION)

.PARAMETER Check
    检查类型：all, ci, sim, replay, commands, artifacts, context

.PARAMETER Strict
    严格模式：任何 ERROR 级别违规立即 exit 12

.EXAMPLE
    .\scripts\validate_policy.ps1 -Check all -Strict
    .\scripts\validate_policy.ps1 -Check ci
#>

param(
    [ValidateSet("all", "ci", "sim", "replay", "commands", "artifacts", "context")]
    [string]$Check = "all",
    
    [switch]$Strict,
    
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# =============================================================================
# 退出码
# =============================================================================
$EXIT_SUCCESS = 0
$EXIT_POLICY_VIOLATION = 12

# =============================================================================
# 固定路径约定 (D.1)
# =============================================================================
$SCRIPT_ROOT = $PSScriptRoot
$PROJECT_ROOT = Split-Path $SCRIPT_ROOT -Parent

$FIXED_PATHS = @{
    ci_report = Join-Path $PROJECT_ROOT "artifacts\check\report.json"
    sim_report = Join-Path $PROJECT_ROOT "artifacts\sim\report.json"
    events_jsonl = Join-Path $PROJECT_ROOT "artifacts\sim\events.jsonl"
    context = Join-Path $PROJECT_ROOT "artifacts\context\context.md"
    commands_log = Join-Path $PROJECT_ROOT "artifacts\claude\commands.log"
    round_summary = Join-Path $PROJECT_ROOT "artifacts\claude\round_summary.json"
    policy_violation = Join-Path $PROJECT_ROOT "artifacts\claude\policy_violation.json"
}

$SCHEMA_DIR = Join-Path $SCRIPT_ROOT "json_schema"
$REQUIRED_SCHEMA_VERSION = 3

# =============================================================================
# 命令白名单
# =============================================================================
$COMMAND_WHITELIST = @(
    '^\.\s*[\\\/]?scripts[\\\/]make\.ps1\s+',
    '^make\s+',
    '^git\s+(status|diff|log|branch|rev-parse)',
    '^(cat|Get-Content|type)\s+',
    '^python\s+-m\s+src\.trading\.(replay|sim)\s+'
)

$COMMAND_BLACKLIST = @(
    '^pytest\b',
    '^ruff\b',
    '^mypy\b',
    '^python\s+-m\s+pytest\b',
    '^python\s+-m\s+ruff\b',
    '^python\s+-m\s+mypy\b'
)

# =============================================================================
# 违规记录
# =============================================================================
$script:violations = @()

function Add-Violation {
    param(
        [string]$Code,
        [string]$Message,
        [hashtable]$Evidence = @{},
        [string]$Severity = "ERROR"
    )
    
    $script:violations += @{
        code = $Code
        message = $Message
        evidence = $Evidence
        severity = $Severity
    }
    
    $marker = if ($Severity -eq "ERROR") { "❌" } else { "⚠️" }
    Write-Host "$marker [$Code] $Message" -ForegroundColor $(if ($Severity -eq "ERROR") { "Red" } else { "Yellow" })
    
    if ($Verbose -and $Evidence.Count -gt 0) {
        Write-Host "   Evidence: $($Evidence | ConvertTo-Json -Compress)" -ForegroundColor Gray
    }
}

# =============================================================================
# JSON Schema 校验
# =============================================================================
function Test-JsonSchema {
    param(
        [string]$ReportPath,
        [string]$ReportType
    )
    
    if (-not (Test-Path $ReportPath)) {
        Add-Violation -Code "REPORT.FILE_MISSING" -Message "Report file not found: $ReportPath" -Evidence @{ path = $ReportPath }
        return $false
    }
    
    try {
        $data = Get-Content $ReportPath -Raw | ConvertFrom-Json
    }
    catch {
        Add-Violation -Code "REPORT.INVALID_JSON" -Message "Invalid JSON: $($_.Exception.Message)" -Evidence @{ path = $ReportPath }
        return $false
    }
    
    # 1. schema_version 检查
    if (-not $data.schema_version) {
        Add-Violation -Code "SCHEMA.VERSION_MISSING" -Message "Missing schema_version" -Evidence @{ path = $ReportPath }
        return $false
    }
    
    if ($data.schema_version -lt $REQUIRED_SCHEMA_VERSION) {
        Add-Violation -Code "SCHEMA.VERSION_OUTDATED" -Message "schema_version $($data.schema_version) < $REQUIRED_SCHEMA_VERSION" -Evidence @{
            current = $data.schema_version
            required = $REQUIRED_SCHEMA_VERSION
        }
        return $false
    }
    
    # 2. 必填字段检查
    $requiredFields = @("schema_version", "type", "overall", "exit_code", "check_mode", "timestamp", "run_id", "exec_id", "artifacts")
    $missingFields = @()
    foreach ($field in $requiredFields) {
        if ($null -eq $data.$field) {
            $missingFields += $field
        }
    }
    
    if ($missingFields.Count -gt 0) {
        Add-Violation -Code "SCHEMA.MISSING_FIELDS" -Message "Missing required fields: $($missingFields -join ', ')" -Evidence @{
            missing = $missingFields
            path = $ReportPath
        }
        return $false
    }
    
    # 3. check_mode 检查 (replay/sim 必须为 true)
    if ($ReportType -in @("replay", "sim")) {
        if ($data.check_mode -ne $true) {
            Add-Violation -Code "POLICY.CHECK_MODE_DISABLED" -Message "check_mode must be true for $ReportType" -Evidence @{
                check_mode = $data.check_mode
            }
            return $false
        }
    }
    
    # 4. run_id 格式检查 (UUID)
    if ($data.run_id -and $data.run_id -notmatch '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$') {
        Add-Violation -Code "SCHEMA.INVALID_RUN_ID" -Message "run_id must be UUID format" -Evidence @{
            run_id = $data.run_id
        } -Severity "WARNING"
    }
    
    # 5. Failure 结构检查 (sim/replay)
    if ($ReportType -in @("replay", "sim") -and $data.failures) {
        $requiredFailureFields = @("scenario", "rule_id", "component", "event_id", "expected", "actual", "error", "evidence")
        $index = 0
        foreach ($failure in $data.failures) {
            $missingFailureFields = @()
            foreach ($field in $requiredFailureFields) {
                # event_id 可以是 tick 的别名
                if ($field -eq "event_id" -and $null -ne $failure.tick) {
                    continue
                }
                if ($null -eq $failure.$field) {
                    $missingFailureFields += $field
                }
            }
            if ($missingFailureFields.Count -gt 0) {
                Add-Violation -Code "FAILURE.MISSING_FIELDS" -Message "Failure[$index] missing: $($missingFailureFields -join ', ')" -Evidence @{
                    index = $index
                    scenario = $failure.scenario
                    missing = $missingFailureFields
                }
            }
            $index++
        }
    }
    
    return $true
}

# =============================================================================
# 命令白名单校验
# =============================================================================
function Test-Command {
    param([string]$Command)
    
    # 检查黑名单
    foreach ($pattern in $COMMAND_BLACKLIST) {
        if ($Command -match $pattern) {
            Add-Violation -Code "COMMAND.BLACKLISTED" -Message "Command matches blacklist: $Command" -Evidence @{
                command = $Command
                pattern = $pattern
            }
            return $false
        }
    }
    
    # 检查白名单
    foreach ($pattern in $COMMAND_WHITELIST) {
        if ($Command -match $pattern) {
            return $true
        }
    }
    
    # 不在白名单 → 警告
    Add-Violation -Code "COMMAND.NOT_WHITELISTED" -Message "Command not in whitelist: $Command" -Evidence @{
        command = $Command
    } -Severity "WARNING"
    
    return $true
}

function Test-CommandsLog {
    $logPath = $FIXED_PATHS.commands_log
    if (-not (Test-Path $logPath)) {
        return $true  # 首次运行可能不存在
    }
    
    $lines = Get-Content $logPath
    foreach ($line in $lines) {
        if ($line -match 'CMD:\s*(.+?)\s*\|') {
            $cmd = $Matches[1]
            Test-Command $cmd | Out-Null
        }
    }
    
    return $true
}

# =============================================================================
# 产物路径校验
# =============================================================================
function Test-ArtifactPaths {
    # 检查 CI 报告路径
    if (Test-Path $FIXED_PATHS.ci_report) {
        $data = Get-Content $FIXED_PATHS.ci_report -Raw | ConvertFrom-Json
        if ($data.artifacts -and $data.artifacts.report_path) {
            $expected = "artifacts/check/report.json"
            if ($data.artifacts.report_path -ne $expected) {
                Add-Violation -Code "ARTIFACT.PATH_MISMATCH" -Message "CI report path mismatch" -Evidence @{
                    expected = $expected
                    actual = $data.artifacts.report_path
                }
                return $false
            }
        }
    }
    
    # 检查 Sim 报告路径
    if (Test-Path $FIXED_PATHS.sim_report) {
        $data = Get-Content $FIXED_PATHS.sim_report -Raw | ConvertFrom-Json
        if ($data.artifacts -and $data.artifacts.report_path) {
            $expected = "artifacts/sim/report.json"
            if ($data.artifacts.report_path -ne $expected) {
                Add-Violation -Code "ARTIFACT.PATH_MISMATCH" -Message "Sim report path mismatch" -Evidence @{
                    expected = $expected
                    actual = $data.artifacts.report_path
                }
                return $false
            }
        }
    }
    
    return $true
}

# =============================================================================
# Context manifest 校验
# =============================================================================
function Get-ContextSha {
    $contextPath = $FIXED_PATHS.context
    if (-not (Test-Path $contextPath)) {
        return $null
    }
    
    $bytes = [System.IO.File]::ReadAllBytes($contextPath)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $hash = $sha256.ComputeHash($bytes)
    return [BitConverter]::ToString($hash).Replace("-", "").ToLower()
}

function Test-ContextManifest {
    $contextPath = $FIXED_PATHS.context
    if (-not (Test-Path $contextPath)) {
        return $true  # context.md 不存在不强制报错
    }
    
    $expectedSha = Get-ContextSha
    
    # 检查 round_summary 中是否有 context_manifest_sha
    $summaryPath = $FIXED_PATHS.round_summary
    if (Test-Path $summaryPath) {
        $data = Get-Content $summaryPath -Raw | ConvertFrom-Json
        if (-not $data.context_manifest_sha) {
            Add-Violation -Code "CONTEXT.SHA_MISSING" -Message "context_manifest_sha missing in round_summary" -Evidence @{
                round_summary = $summaryPath
            }
            return $false
        }
        if ($data.context_manifest_sha -ne $expectedSha) {
            Add-Violation -Code "CONTEXT.SHA_MISMATCH" -Message "context_manifest_sha mismatch" -Evidence @{
                expected = $expectedSha
                actual = $data.context_manifest_sha
            }
            return $false
        }
    }
    
    return $true
}

# =============================================================================
# 主入口
# =============================================================================
Write-Host ""
Write-Host "=== Policy Validator (Military-Grade v3.0) ===" -ForegroundColor Cyan
Write-Host "Check type: $Check, Strict: $Strict" -ForegroundColor Gray
Write-Host ""

# 执行检查
if ($Check -in @("all", "ci")) {
    Write-Host "Checking CI report..." -ForegroundColor Cyan
    Test-JsonSchema -ReportPath $FIXED_PATHS.ci_report -ReportType "ci" | Out-Null
}

if ($Check -in @("all", "sim", "replay")) {
    if (Test-Path $FIXED_PATHS.sim_report) {
        Write-Host "Checking Sim/Replay report..." -ForegroundColor Cyan
        $data = Get-Content $FIXED_PATHS.sim_report -Raw | ConvertFrom-Json
        $reportType = if ($data.type) { $data.type } else { "sim" }
        Test-JsonSchema -ReportPath $FIXED_PATHS.sim_report -ReportType $reportType | Out-Null
    }
}

if ($Check -in @("all", "commands")) {
    Write-Host "Checking commands log..." -ForegroundColor Cyan
    Test-CommandsLog | Out-Null
}

if ($Check -in @("all", "artifacts")) {
    Write-Host "Checking artifact paths..." -ForegroundColor Cyan
    Test-ArtifactPaths | Out-Null
}

if ($Check -in @("all", "context")) {
    Write-Host "Checking context manifest..." -ForegroundColor Cyan
    Test-ContextManifest | Out-Null
}

# 输出结果
Write-Host ""
$errorCount = ($script:violations | Where-Object { $_.severity -eq "ERROR" }).Count
$warningCount = ($script:violations | Where-Object { $_.severity -eq "WARNING" }).Count

if ($errorCount -gt 0) {
    Write-Host "❌ POLICY_VIOLATION: $errorCount errors, $warningCount warnings" -ForegroundColor Red
    
    # 写入违规报告
    $report = @{
        timestamp = (Get-Date -Format 'o')
        has_errors = $true
        error_count = $errorCount
        warning_count = $warningCount
        violations = $script:violations
    }
    
    $violationDir = Split-Path $FIXED_PATHS.policy_violation -Parent
    if (-not (Test-Path $violationDir)) {
        New-Item -ItemType Directory -Path $violationDir -Force | Out-Null
    }
    $report | ConvertTo-Json -Depth 10 | Out-File $FIXED_PATHS.policy_violation -Encoding UTF8
    
    if ($Strict) {
        exit $EXIT_POLICY_VIOLATION
    }
    exit $EXIT_POLICY_VIOLATION
}
elseif ($warningCount -gt 0) {
    Write-Host "⚠️ Policy check passed with $warningCount warnings" -ForegroundColor Yellow
    exit $EXIT_SUCCESS
}
else {
    Write-Host "✅ Policy check passed" -ForegroundColor Green
    exit $EXIT_SUCCESS
}
