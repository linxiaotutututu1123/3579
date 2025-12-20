# Fix extra spaces in V3PRO_UPGRADE_PLAN_Version2.md
$filePath = "c:\Users\1\2468\3579\docs\V3PRO_UPGRADE_PLAN_Version2.md"
$content = [System.IO.File]::ReadAllText($filePath)

$originalLength = $content.Length

# Fix extra spaces in file paths and module names
$replacements = @(
    @("__init__. py", "__init__.py"),
    @("context. md", "context.md"),
    @("dingtalk. py", "dingtalk.py"),
    @("state. py", "state.py"),
    @("fallback. py", "fallback.py"),
    @("quality. py", "quality.py"),
    @("kalman_beta. py", "kalman_beta.py"),
    @("replay. verifier", "replay.verifier"),
    @("audit. writer", "audit.writer"),
    @("cost. estimator", "cost.estimator"),
    @("strategy. fallback", "strategy.fallback"),
    @("strategy. calendar_arb", "strategy.calendar_arb"),
    @("execution. auto", "execution.auto"),
    @("execution. protection", "execution.protection"),
    @("execution. position", "execution.position"),
    @("validate_policy. py", "validate_policy.py"),
    @("coverage_gate. py", "coverage_gate.py"),
    @("src. audit", "src.audit"),
    @("src. cost", "src.cost"),
    @("src. guardian", "src.guardian"),
    @("src. execution", "src.execution"),
    @("src. strategy", "src.strategy"),
    @("src. market", "src.market"),
    @("src. replay", "src.replay"),
    @("pair. pair_executor", "pair.pair_executor"),
    @("protection. liquidity", "protection.liquidity"),
    @("liquidity. py", "liquidity.py"),
    @("timeout. py", "timeout.py"),
    @("v3pro_strategies. yml", "v3pro_strategies.yml"),
    @("make. ps1", "make.ps1"),
    @("4. 1", "4.1"),
    @("5. 7", "5.7"),
    @("INST. CACHE", "INST.CACHE"),
    @("UNIV. ", "UNIV."),
    @("MKT. ", "MKT."),
    @("GUARD. ", "GUARD."),
    @("AUDIT. ", "AUDIT."),
    @("COST. ", "COST."),
    @("STRAT. ", "STRAT."),
    @("EXEC. ", "EXEC."),
    @("FSM. ", "FSM."),
    @("POS. ", "POS."),
    @("PAIR. ", "PAIR."),
    @("ARB. ", "ARB."),
    @("MOE. ", "MOE."),
    @("DL. ", "DL."),
    @("TOPTIER. ", "TOPTIER."),
    @("LINEAR. ", "LINEAR."),
    @("SIMPLE. ", "SIMPLE."),
    @("REPLAY. ", "REPLAY."),
    @("calendar_arb. ", "calendar_arb."),
    @("2. 5h", "2.5h"),
    @("9. 5h", "9.5h")
)

$fixCount = 0
foreach ($r in $replacements) {
    if ($content.Contains($r[0])) {
        $content = $content.Replace($r[0], $r[1])
        $fixCount++
        Write-Host "Fixed: '$($r[0])' -> '$($r[1])'"
    }
}

[System.IO.File]::WriteAllText($filePath, $content)
Write-Host "`nTotal fixes applied: $fixCount"
Write-Host "Original length: $originalLength"
Write-Host "New length: $($content.Length)"
