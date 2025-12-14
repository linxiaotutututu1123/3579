<#
.SYNOPSIS
    Claude 自动闭环驱动器
    运行 CI + Replay 直到全部通过或达到最大轮数

.DESCRIPTION
    此脚本实现完整的自动修复闭环：
    1. 生成上下文 (context-dev)
    2. 运行 CI 检查 (ci-json)
    3. 如果失败，显示失败摘要供 Claude 修复
    4. CI 通过后运行 Replay (replay-json)
    5. 如果失败，显示失败摘要供 Claude 修复
    6. 重复直到全部通过

.PARAMETER Mode
    运行模式：
    - full: CI + Replay 完整闭环（默认）
    - ci: 仅 CI 闭环
    - replay: 仅 Replay 闭环（假设 CI 已通过）
    - sim: 仅 Sim 闭环

.PARAMETER MaxRounds
    最大尝试轮数（默认 5）

.PARAMETER SkipContext
    跳过上下文刷新（用于快速迭代）

.EXAMPLE
    .\scripts\claude_loop.ps1 -Mode full -MaxRounds 5
    .\scripts\claude_loop.ps1 -Mode ci
    .\scripts\claude_loop.ps1 -Mode replay -SkipContext
#>

param(
    [ValidateSet("full", "ci", "replay", "sim")]
    [string]$Mode = "full",

    [int]$MaxRounds = 5,

    [switch]$SkipContext
)

$ErrorActionPreference = "Stop"

# =============================================================================
# 配置
# =============================================================================
$SCRIPT_ROOT = $PSScriptRoot
$PROJECT_ROOT = Split-Path $SCRIPT_ROOT -Parent
$MAKE_PS1 = Join-Path $SCRIPT_ROOT "make.ps1"

$CI_REPORT = Join-Path $PROJECT_ROOT "artifacts\check\report.json"
$SIM_REPORT = Join-Path $PROJECT_ROOT "artifacts\sim\report.json"
$CONTEXT_FILE = Join-Path $PROJECT_ROOT "artifacts\context\context.md"

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
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor $Color
}

function Read-JsonReport {
    param([string]$Path)
    if (Test-Path $Path) {
        return Get-Content $Path -Raw | ConvertFrom-Json
    }
    return $null
}

function Show-CIFailures {
    param($Report)
    
    if (-not $Report) {
        Write-Status "无法读取 CI 报告" -Color Red
        return
    }
    
    Write-Host ""
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
    Write-Host " CI 失败摘要" -ForegroundColor Red
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
    
    foreach ($step in $Report.steps) {
        if ($step.status -eq "FAIL") {
            Write-Host ""
            Write-Host "  [$($step.name)] 失败 (exit_code=$($step.exit_code))" -ForegroundColor Red
            
            if ($step.failures) {
                foreach ($failure in $step.failures) {
                    Write-Host "    • $($failure.file):$($failure.line) - $($failure.message)" -ForegroundColor Yellow
                }
            }
            elseif ($step.output_summary) {
                # 只显示前 5 行
                $lines = $step.output_summary -split "`n" | Select-Object -First 5
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
    Write-Host " Replay/Sim 失败摘要" -ForegroundColor Red
    Write-Host "─────────────────────────────────────────────────────────────" -ForegroundColor Red
    Write-Host ""
    Write-Host "  通过: $($Report.scenarios_passed) / $($Report.scenarios_total)" -ForegroundColor Yellow
    
    if ($Report.failures) {
        foreach ($failure in $Report.failures) {
            Write-Host ""
            Write-Host "  [$($failure.scenario)] tick=$($failure.tick)" -ForegroundColor Red
            Write-Host "    期望: $($failure.expected | ConvertTo-Json -Compress)" -ForegroundColor Yellow
            Write-Host "    实际: $($failure.actual | ConvertTo-Json -Compress)" -ForegroundColor Yellow
            Write-Host "    错误: $($failure.error)" -ForegroundColor Yellow
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
    
    # 运行 ci-json
    & $MAKE_PS1 ci-json
    $exitCode = $LASTEXITCODE
    
    # 读取报告
    $report = Read-JsonReport $CI_REPORT
    
    if ($report -and $report.overall -eq "PASS") {
        Write-Status "CI 通过!" -Color Green
        return $true
    }
    
    Write-Status "CI 失败 (exit_code=$exitCode)" -Color Red
    Show-CIFailures $report
    
    return $false
}

function Invoke-ReplayLoop {
    param([int]$Round)
    
    Write-Status "运行 Replay 检查..." -Color Cyan
    
    # 运行 replay-json
    & $MAKE_PS1 replay-json
    $exitCode = $LASTEXITCODE
    
    # 读取报告
    $report = Read-JsonReport $SIM_REPORT
    
    if ($report -and $report.overall -eq "PASS") {
        Write-Status "Replay 通过!" -Color Green
        return $true
    }
    
    Write-Status "Replay 失败 (exit_code=$exitCode)" -Color Red
    Show-SimFailures $report
    
    return $false
}

function Invoke-SimLoop {
    param([int]$Round)
    
    Write-Status "运行 Sim 检查..." -Color Cyan
    
    # 运行 sim-json
    & $MAKE_PS1 sim-json
    $exitCode = $LASTEXITCODE
    
    # 读取报告
    $report = Read-JsonReport $SIM_REPORT
    
    if ($report -and $report.overall -eq "PASS") {
        Write-Status "Sim 通过!" -Color Green
        return $true
    }
    
    Write-Status "Sim 失败 (exit_code=$exitCode)" -Color Red
    Show-SimFailures $report
    
    return $false
}

# =============================================================================
# 主入口
# =============================================================================

Push-Location $PROJECT_ROOT

try {
    Write-Header "Claude 自动闭环驱动器"
    Write-Status "模式: $Mode, 最大轮数: $MaxRounds"
    
    $round = 0
    $ciPassed = $false
    $replayPassed = $false
    
    while ($round -lt $MaxRounds) {
        $round++
        Write-Header "Round $round / $MaxRounds"
        
        # Step 1: 刷新上下文
        if (-not $SkipContext) {
            Write-Status "刷新开发上下文..." -Color Cyan
            & $MAKE_PS1 context-dev
            Write-Status "上下文已生成: $CONTEXT_FILE" -Color Gray
        }
        
        # Step 2: 根据模式执行
        switch ($Mode) {
            "ci" {
                if (Invoke-CILoop -Round $round) {
                    Write-Host ""
                    Write-Host "✓ CI 闭环完成!" -ForegroundColor Green
                    exit 0
                }
            }
            
            "replay" {
                if (Invoke-ReplayLoop -Round $round) {
                    Write-Host ""
                    Write-Host "✓ Replay 闭环完成!" -ForegroundColor Green
                    exit 0
                }
            }
            
            "sim" {
                if (Invoke-SimLoop -Round $round) {
                    Write-Host ""
                    Write-Host "✓ Sim 闭环完成!" -ForegroundColor Green
                    exit 0
                }
            }
            
            "full" {
                # 先 CI
                if (-not $ciPassed) {
                    if (Invoke-CILoop -Round $round) {
                        $ciPassed = $true
                        Write-Status "CI 已通过，进入 Replay 阶段" -Color Green
                    }
                    else {
                        Write-Status "等待 Claude 修复 CI 问题..." -Color Yellow
                        Write-Host ""
                        Write-Host "请修复上述问题后重新运行此脚本" -ForegroundColor Magenta
                        exit 2
                    }
                }
                
                # 再 Replay
                if ($ciPassed -and -not $replayPassed) {
                    if (Invoke-ReplayLoop -Round $round) {
                        $replayPassed = $true
                    }
                    else {
                        Write-Status "等待 Claude 修复 Replay 问题..." -Color Yellow
                        Write-Host ""
                        Write-Host "请修复上述问题后重新运行此脚本" -ForegroundColor Magenta
                        exit 10
                    }
                }
                
                # 全部通过
                if ($ciPassed -and $replayPassed) {
                    Write-Host ""
                    Write-Host "✓✓ CI + Replay 完整闭环完成!" -ForegroundColor Green
                    exit 0
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
        # 如果是交互式，等待用户确认
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
    exit 1
    
} finally {
    Pop-Location
}
