<#
.SYNOPSIS
    Claude 自动闭环驱动器（军规级 v3.0）
    运行 CI + Replay + Sim 直到全部通过或达到最大轮数

.DESCRIPTION
    军规级自动修复闭环：
    1. 生成上下文 (context-dev)
    2. 运行 CI 检查 (ci-json) - 必须通过 schema 校验
    3. 运行 Replay (replay-json) - 必须启用 CHECK_MODE
    4. 运行 Sim (sim-json) - 可选
    5. 记录所有命令和结果到审计日志
    6. 检测 Policy Violation 并阻止继续

    军规级增强：
    - 白名单命令：只允许 make.ps1 targets
    - Schema 校验：report.json 必须符合 v3 schema
    - 审计日志：artifacts/claude/commands.log
    - 违规报告：artifacts/claude/policy_violation.json
    - 轮次摘要：artifacts/claude/round_summary.json

.PARAMETER Mode
    运行模式：
    - full: CI + Replay + Sim 完整闭环（默认）
    - ci: 仅 CI 闭环
    - replay: 仅 Replay 闘环（假设 CI 已通过）
    - sim: 仅 Sim 闭环

.PARAMETER MaxRounds
    最大尝试轮数（默认 5）

.PARAMETER SkipContext
    跳过上下文刷新（用于快速迭代）

.PARAMETER Strict
    严格模式：违规立即退出 12

.EXAMPLE
    .\scripts\claude_loop.ps1 -Mode full -MaxRounds 5
    .\scripts\claude_loop.ps1 -Mode ci -Strict
    .\scripts\claude_loop.ps1 -Mode replay -SkipContext
#>

param(
    [ValidateSet("full", "ci", "replay", "sim")]
    [string]$Mode = "full",

    [int]$MaxRounds = 5,

    [switch]$SkipContext,

    [switch]$Strict
)

$ErrorActionPreference = "Stop"

# =============================================================================
# 配置（固定路径 - D.1 不可更改）
# =============================================================================
$SCRIPT_ROOT = $PSScriptRoot
$PROJECT_ROOT = Split-Path $SCRIPT_ROOT -Parent
$MAKE_PS1 = Join-Path $SCRIPT_ROOT "make.ps1"

# 固定产物路径（D.1 路径绝对不变）
$CI_REPORT = Join-Path $PROJECT_ROOT "artifacts\check\report.json"
$SIM_REPORT = Join-Path $PROJECT_ROOT "artifacts\sim\report.json"
$CONTEXT_FILE = Join-Path $PROJECT_ROOT "artifacts\context\context.md"

# 军规级审计路径
$CLAUDE_DIR = Join-Path $PROJECT_ROOT "artifacts\claude"
$COMMANDS_LOG = Join-Path $CLAUDE_DIR "commands.log"
$ROUND_SUMMARY = Join-Path $CLAUDE_DIR "round_summary.json"
$POLICY_VIOLATION_FILE = Join-Path $CLAUDE_DIR "policy_violation.json"

# Schema 版本要求
$REQUIRED_SCHEMA_VERSION = 3

# 退出码
$EXIT_SUCCESS = 0
$EXIT_GENERAL_ERROR = 1
$EXIT_CI_FAIL = 2
$EXIT_REPLAY_FAIL = 8
$EXIT_SIM_FAIL = 9
$EXIT_POLICY_VIOLATION = 12

# =============================================================================
# 初始化审计目录
# =============================================================================
if (-not (Test-Path $CLAUDE_DIR)) {
    New-Item -ItemType Directory -Path $CLAUDE_DIR -Force | Out-Null
}

# =============================================================================
# 辅助函数
# =============================================================================

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host "==============================================================" -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host "==============================================================" -ForegroundColor Cyan
}

function Write-Status {
    param([string]$Message, [string]$Color = "White")
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Write-Host "[$ts] $Message" -ForegroundColor $Color
}

function Write-CommandLog {
    param([string]$Command, [string]$Result = "", [int]$ExitCode = 0)
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $entry = "[$ts] CMD: $Command | EXIT: $ExitCode | RESULT: $Result"
    Add-Content -Path $COMMANDS_LOG -Value $entry -Encoding UTF8
}

function Write-PolicyViolation {
    param([string]$Code, [string]$Message, [hashtable]$Evidence = @{})
    
    $violation = @{
        timestamp = (Get-Date -Format 'o')
        code = $Code
        message = $Message
        evidence = $Evidence
    }
    
    $existingViolations = @()
    if (Test-Path $POLICY_VIOLATION_FILE) {
        try {
            $existing = Get-Content $POLICY_VIOLATION_FILE -Raw | ConvertFrom-Json
            if ($existing.violations) {
                $existingViolations = @($existing.violations)
            }
        } catch {
            # Ignore parse errors
        }
    }
    
    $allViolations = $existingViolations + @($violation)
    $report = @{
        timestamp = (Get-Date -Format 'o')
        has_violations = $true
        violation_count = $allViolations.Count
        violations = $allViolations
    }
    
    $report | ConvertTo-Json -Depth 10 | Out-File $POLICY_VIOLATION_FILE -Encoding UTF8
    Write-Status "POLICY_VIOLATION: [$Code] $Message" -Color Red
}

function Write-RoundSummary {
    param([int]$Round, [hashtable]$Results)
    
    # 计算 context_manifest_sha（军规级 G.4）
    $contextSha = ""
    if (Test-Path $CONTEXT_FILE) {
        try {
            $contextSha = (Get-FileHash -Path $CONTEXT_FILE -Algorithm SHA256).Hash.ToLower()
        } catch {
            $contextSha = "ERROR_COMPUTING_SHA"
        }
    } else {
        $contextSha = "CONTEXT_FILE_MISSING"
    }
    
    # 生成 run_id 和 exec_id（军规级 C.1）
    $runId = [System.Guid]::NewGuid().ToString()
    $commitSha = ""
    try {
        $commitSha = (git rev-parse HEAD 2>$null)
        if (-not $commitSha) { $commitSha = "NO_GIT" }
    } catch {
        $commitSha = "NO_GIT"
    }
    $execId = "$commitSha-$(Get-Date -Format 'yyyyMMddHHmmss')"
    
    $summary = @{
        schema_version = 3
        timestamp = (Get-Date -Format 'o')
        run_id = $runId
        exec_id = $execId
        context_manifest_sha = $contextSha
        round = $Round
        mode = $Mode
        results = $Results
    }
    
    $summary | ConvertTo-Json -Depth 10 | Out-File $ROUND_SUMMARY -Encoding UTF8
}

function Read-JsonReport {
    param([string]$Path)
    if (Test-Path $Path) {
        try {
            return Get-Content $Path -Raw | ConvertFrom-Json
        } catch {
            Write-Status "无法解析 JSON: $Path" -Color Red
            return $null
        }
    }
    return $null
}

function Test-SchemaVersion {
    param($Report, [string]$ReportType)
    
    if (-not $Report) {
        Write-PolicyViolation -Code "SCHEMA.FILE_MISSING" -Message "Report is null" -Evidence @{type=$ReportType}
        return $false
    }
    
    # Check schema_version
    $version = $Report.schema_version
    if (-not $version) {
        Write-PolicyViolation -Code "SCHEMA.MISSING_FIELD" -Message "Missing schema_version" -Evidence @{type=$ReportType}
        return $false
    }
    
    if ($version -lt $REQUIRED_SCHEMA_VERSION) {
        Write-PolicyViolation -Code "SCHEMA.VERSION_OUTDATED" -Message "Schema version $version < $REQUIRED_SCHEMA_VERSION" -Evidence @{
            current = $version
            required = $REQUIRED_SCHEMA_VERSION
        }
        return $false
    }
    
    # Check check_mode for replay/sim
    if ($ReportType -in @("replay", "sim")) {
        if (-not $Report.check_mode) {
            Write-PolicyViolation -Code "POLICY.CHECK_MODE_DISABLED" -Message "CHECK_MODE must be enabled for $ReportType" -Evidence @{
                check_mode = $Report.check_mode
            }
            return $false
        }
    }
    
    return $true
}

function Show-CIFailures {
    param($Report)
    
    if (-not $Report) {
        Write-Status "无法读取 CI 报告" -Color Red
        return
    }
    
    Write-Host ""
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
    Write-Host " CI 失败摘要 (schema_version=$($Report.schema_version))" -ForegroundColor Red
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
    
    foreach ($step in $Report.steps) {
        if ($step.status -eq "FAIL") {
            Write-Host ""
            Write-Host "  [$($step.name)] 失败 (exit_code=$($step.exit_code))" -ForegroundColor Red
            
            if ($step.hints) {
                Write-Host "  修复提示:" -ForegroundColor Yellow
                foreach ($hint in $step.hints) {
                    Write-Host "    → $hint" -ForegroundColor Yellow
                }
            }
            
            if ($step.failures) {
                Write-Host "  详细错误:" -ForegroundColor Yellow
                foreach ($failure in $step.failures | Select-Object -First 5) {
                    Write-Host "    • $($failure.file):$($failure.line) - $($failure.message)" -ForegroundColor Yellow
                }
            }
            elseif ($step.summary) {
                $lines = $step.summary -split "`n" | Select-Object -First 5
                foreach ($line in $lines) {
                    Write-Host "    $line" -ForegroundColor Yellow
                }
            }
        }
    }
    Write-Host ""
}

function Show-SimFailures {
    param($Report)
    
    if (-not $Report) {
        Write-Status "无法读取 Sim 报告" -Color Red
        return
    }
    
    Write-Host ""
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
    Write-Host " Replay/Sim 失败摘要 (schema_version=$($Report.schema_version))" -ForegroundColor Red
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
    Write-Host ""
    Write-Host "  CHECK_MODE: $($Report.check_mode)" -ForegroundColor $(if ($Report.check_mode) { "Green" } else { "Red" })
    Write-Host "  通过: $($Report.scenarios_passed) / $($Report.scenarios_total)" -ForegroundColor Yellow
    
    if ($Report.failures) {
        foreach ($failure in $Report.failures | Select-Object -First 5) {
            Write-Host ""
            Write-Host "  [$($failure.rule_id)] $($failure.scenario)" -ForegroundColor Red
            Write-Host "    Component: $($failure.component)" -ForegroundColor Yellow
            Write-Host "    Tick: $($failure.tick)" -ForegroundColor Yellow
            Write-Host "    期望: $($failure.expected | ConvertTo-Json -Compress)" -ForegroundColor Yellow
            Write-Host "    实际: $($failure.actual | ConvertTo-Json -Compress)" -ForegroundColor Yellow
            Write-Host "    错误: $($failure.error)" -ForegroundColor Yellow
            if ($failure.evidence -and ($failure.evidence | Get-Member -MemberType NoteProperty)) {
                Write-Host "    证据: $($failure.evidence | ConvertTo-Json -Compress)" -ForegroundColor Gray
            }
        }
    }
    Write-Host ""
}

# =============================================================================
# 主循环逻辑
# =============================================================================

function Invoke-CILoop {
    param([int]$Round)
    
    Write-Status "运行 CI 检查..." -Color Cyan
    
    # 记录命令
    Write-CommandLog -Command "make.ps1 ci-json"
    
    # 运行 ci-json
    & $MAKE_PS1 ci-json
    $exitCode = $LASTEXITCODE
    
    Write-CommandLog -Command "make.ps1 ci-json" -ExitCode $exitCode
    
    # 读取报告
    $report = Read-JsonReport $CI_REPORT
    
    # Schema 校验
    if ($Strict -and -not (Test-SchemaVersion -Report $report -ReportType "ci")) {
        Write-Status "CI 报告 schema 校验失败" -Color Red
        return @{ passed = $false; exit_code = $EXIT_POLICY_VIOLATION; report = $report }
    }
    
    if ($report -and $report.overall -eq "PASS") {
        Write-Status "CI 通过!" -Color Green
        return @{ passed = $true; exit_code = $EXIT_SUCCESS; report = $report }
    }
    
    Write-Status "CI 失败 (exit_code=$exitCode)" -Color Red
    Show-CIFailures $report
    
    return @{ passed = $false; exit_code = $exitCode; report = $report }
}

function Invoke-ReplayLoop {
    param([int]$Round)
    
    Write-Status "运行 Replay 检查..." -Color Cyan
    
    Write-CommandLog -Command "make.ps1 replay-json"
    
    # 运行 replay-json
    & $MAKE_PS1 replay-json
    $exitCode = $LASTEXITCODE
    
    Write-CommandLog -Command "make.ps1 replay-json" -ExitCode $exitCode
    
    # 读取报告
    $report = Read-JsonReport $SIM_REPORT
    
    # Schema 校验（军规级）
    if ($Strict -and -not (Test-SchemaVersion -Report $report -ReportType "replay")) {
        Write-Status "Replay 报告 schema 校验失败" -Color Red
        return @{ passed = $false; exit_code = $EXIT_POLICY_VIOLATION; report = $report }
    }
    
    if ($report -and $report.overall -eq "PASS") {
        Write-Status "Replay 通过!" -Color Green
        return @{ passed = $true; exit_code = $EXIT_SUCCESS; report = $report }
    }
    
    Write-Status "Replay 失败 (exit_code=$exitCode)" -Color Red
    Show-SimFailures $report
    
    return @{ passed = $false; exit_code = $EXIT_REPLAY_FAIL; report = $report }
}

function Invoke-SimLoop {
    param([int]$Round)
    
    Write-Status "运行 Sim 检查..." -Color Cyan
    
    Write-CommandLog -Command "make.ps1 sim-json"
    
    & $MAKE_PS1 sim-json
    $exitCode = $LASTEXITCODE
    
    Write-CommandLog -Command "make.ps1 sim-json" -ExitCode $exitCode
    
    $report = Read-JsonReport $SIM_REPORT
    
    # Schema 校验
    if ($Strict -and -not (Test-SchemaVersion -Report $report -ReportType "sim")) {
        Write-Status "Sim 报告 schema 校验失败" -Color Red
        return @{ passed = $false; exit_code = $EXIT_POLICY_VIOLATION; report = $report }
    }
    
    if ($report -and $report.overall -eq "PASS") {
        Write-Status "Sim 通过!" -Color Green
        return @{ passed = $true; exit_code = $EXIT_SUCCESS; report = $report }
    }
    
    Write-Status "Sim 失败 (exit_code=$exitCode)" -Color Red
    Show-SimFailures $report
    
    return @{ passed = $false; exit_code = $EXIT_SIM_FAIL; report = $report }
}

# =============================================================================
# 主入口
# =============================================================================

Push-Location $PROJECT_ROOT

try {
    Write-Header "Claude 自动闭环驱动器（军规级 v3.0）"
    Write-Status "模式: $Mode, 最大轮数: $MaxRounds, 严格模式: $Strict"
    
    # 清理上一轮的违规报告
    if (Test-Path $POLICY_VIOLATION_FILE) {
        Remove-Item $POLICY_VIOLATION_FILE -Force
    }
    
    # 初始化命令日志
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Path $COMMANDS_LOG -Value "`n========== Session Start: $ts ==========" -Encoding UTF8
    Add-Content -Path $COMMANDS_LOG -Value "Mode: $Mode, MaxRounds: $MaxRounds, Strict: $Strict" -Encoding UTF8
    
    $round = 0
    $ciPassed = $false
    $replayPassed = $false
    $simPassed = $false
    
    while ($round -lt $MaxRounds) {
        $round++
        Write-Header "Round $round / $MaxRounds"
        
        $roundResults = @{
            round = $round
            ci = @{ status = "SKIP" }
            replay = @{ status = "SKIP" }
            sim = @{ status = "SKIP" }
        }
        
        # Step 1: 刷新上下文
        if (-not $SkipContext) {
            Write-Status "刷新开发上下文..." -Color Cyan
            Write-CommandLog -Command "make.ps1 context-dev"
            & $MAKE_PS1 context-dev
            Write-CommandLog -Command "make.ps1 context-dev" -ExitCode $LASTEXITCODE
            Write-Status "上下文已生成: $CONTEXT_FILE" -Color Gray
        }
        
        # Step 2: 根据模式执行
        switch ($Mode) {
            "ci" {
                $result = Invoke-CILoop -Round $round
                $roundResults.ci = @{ status = $(if ($result.passed) { "PASS" } else { "FAIL" }); exit_code = $result.exit_code }
                Write-RoundSummary -Round $round -Results $roundResults
                
                if ($result.passed) {
                    Write-Host ""
                    Write-Host "✓ CI 闭环完成!" -ForegroundColor Green
                    exit $EXIT_SUCCESS
                }
                if ($result.exit_code -eq $EXIT_POLICY_VIOLATION) {
                    Write-Host ""
                    Write-Host "✗ Policy Violation - 强制停止" -ForegroundColor Red
                    exit $EXIT_POLICY_VIOLATION
                }
            }
            
            "replay" {
                $result = Invoke-ReplayLoop -Round $round
                $roundResults.replay = @{ status = $(if ($result.passed) { "PASS" } else { "FAIL" }); exit_code = $result.exit_code }
                Write-RoundSummary -Round $round -Results $roundResults
                
                if ($result.passed) {
                    Write-Host ""
                    Write-Host "✓ Replay 闭环完成!" -ForegroundColor Green
                    exit $EXIT_SUCCESS
                }
                if ($result.exit_code -eq $EXIT_POLICY_VIOLATION) {
                    exit $EXIT_POLICY_VIOLATION
                }
            }
            
            "sim" {
                $result = Invoke-SimLoop -Round $round
                $roundResults.sim = @{ status = $(if ($result.passed) { "PASS" } else { "FAIL" }); exit_code = $result.exit_code }
                Write-RoundSummary -Round $round -Results $roundResults
                
                if ($result.passed) {
                    Write-Host ""
                    Write-Host "✓ Sim 闭环完成!" -ForegroundColor Green
                    exit $EXIT_SUCCESS
                }
                if ($result.exit_code -eq $EXIT_POLICY_VIOLATION) {
                    exit $EXIT_POLICY_VIOLATION
                }
            }
            
            "full" {
                # 先 CI
                if (-not $ciPassed) {
                    $result = Invoke-CILoop -Round $round
                    $roundResults.ci = @{ status = $(if ($result.passed) { "PASS" } else { "FAIL" }); exit_code = $result.exit_code }
                    
                    if ($result.exit_code -eq $EXIT_POLICY_VIOLATION) {
                        Write-RoundSummary -Round $round -Results $roundResults
                        exit $EXIT_POLICY_VIOLATION
                    }
                    
                    if ($result.passed) {
                        $ciPassed = $true
                        Write-Status "CI 已通过，进入 Replay 阶段" -Color Green
                    }
                    else {
                        Write-RoundSummary -Round $round -Results $roundResults
                        Write-Status "等待 Claude 修复 CI 问题..." -Color Yellow
                        Write-Host ""
                        Write-Host "请修复上述问题后重新运行此脚本" -ForegroundColor Magenta
                        exit $EXIT_CI_FAIL
                    }
                }
                
                # 再 Replay
                if ($ciPassed -and -not $replayPassed) {
                    $result = Invoke-ReplayLoop -Round $round
                    $roundResults.replay = @{ status = $(if ($result.passed) { "PASS" } else { "FAIL" }); exit_code = $result.exit_code }
                    
                    if ($result.exit_code -eq $EXIT_POLICY_VIOLATION) {
                        Write-RoundSummary -Round $round -Results $roundResults
                        exit $EXIT_POLICY_VIOLATION
                    }
                    
                    if ($result.passed) {
                        $replayPassed = $true
                    }
                    else {
                        Write-RoundSummary -Round $round -Results $roundResults
                        Write-Status "等待 Claude 修复 Replay 问题..." -Color Yellow
                        Write-Host ""
                        Write-Host "请修复上述问题后重新运行此脚本" -ForegroundColor Magenta
                        exit $EXIT_REPLAY_FAIL
                    }
                }
                
                # 全部通过
                if ($ciPassed -and $replayPassed) {
                    Write-RoundSummary -Round $round -Results $roundResults
                    Write-Host ""
                    Write-Host "✓✓ CI + Replay 完整闭环完成!" -ForegroundColor Green
                    exit $EXIT_SUCCESS
                }
            }
        }
        
        # 等待 Claude 修复
        Write-Host ""
        Write-Host "────────────────────────────────────────────────────" -ForegroundColor Magenta
        Write-Host " 请根据上述失败信息修改代码，然后重新运行" -ForegroundColor Magenta
        Write-Host " 或继续下一轮自动检查" -ForegroundColor Magenta
        Write-Host "────────────────────────────────────────────────────" -ForegroundColor Magenta
        
        # 如果是自动化环境，继续下一轮
        if ($env:CI -or $env:CLAUDE_AUTOMATED) {
            Write-Status "自动化模式，继续下一轮..." -Color Gray
        }
        else {
            Write-Host ""
            Write-Host "按 Enter 继续下一轮，或 Ctrl+C 退出" -ForegroundColor Gray
            Read-Host | Out-Null
        }
    }
    
    # 达到最大轮数
    Write-Host ""
    Write-Host "✗ 达到最大轮数 ($MaxRounds)，闭环未完成" -ForegroundColor Red
    exit $EXIT_GENERAL_ERROR
    
} finally {
    Pop-Location
}
