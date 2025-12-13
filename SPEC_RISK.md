# RiskPolicy v1.1 (Final)

## Instruments
- AO (SHFE), SA (CZCE), LC (GFEX) + 2 auto-selected later

## Daily baseline
- E0 snapshot at **09:00:00** (day session)

## Kill switch (daily DD)
- Trigger: DD(t) <= -3% and kill_switch_fired_today == false
- Action: CancelAll -> ForceFlattenAll -> COOLDOWN(90min)
- After cooldown: RECOVERY
  - 
ecovery_risk_multiplier = 0.30
  - max_margin_recovery = 0.40
- Second time DD(t) <= -3% in same trading day: LOCKED (no opening until next day)

## Force flatten (execution policy)
- Order type: **LIMIT only** (no FAK/FOK)
- Prefer closing today positions first (**CloseToday**); if rejected, fallback to **Close**
- Stage1: 	1=5s near best (min impact)
- Stage2: dt=2s, 
=12 requotes, step=1 tick
- Stage3: aggressive but limited: cross <= 12 levels from best
- Alerts: DingTalk webhook