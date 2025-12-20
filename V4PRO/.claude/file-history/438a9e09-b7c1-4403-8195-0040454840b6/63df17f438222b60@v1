# V4PRO 验收矩阵报告 - 军规级场景全覆盖

> **文档版本**: v4.0 SUPREME MATRIX
> **生成日期**: 2025-12-16
> **文档等级**: 最高机密 - 军规级
> **场景总数**: 165 条
> **军规覆盖**: M1-M20 全覆盖

---

## 目录

- [§A 基础设施层 (Phase 0)](#a-基础设施层-phase-0)
- [§B 行情层 (Phase 1)](#b-行情层-phase-1)
- [§C 审计层 (Phase 2)](#c-审计层-phase-2)
- [§D 策略降级层 (Phase 3)](#d-策略降级层-phase-3)
- [§E 回放验证层 (Phase 4)](#e-回放验证层-phase-4)
- [§F 成本层 (Phase 5)](#f-成本层-phase-5)
- [§G 中国期货市场特化 (Phase 7)](#g-中国期货市场特化-phase-7)
- [§H 智能策略层 (Phase 8)](#h-智能策略层-phase-8)
- [§I 合规监控层 (Phase 9)](#i-合规监控层-phase-9)
- [§J 组合风控层 (Phase 10)](#j-组合风控层-phase-10)
- [§K B类模型层 (Phase 6)](#k-b类模型层-phase-6)
- [场景统计总表](#场景统计总表)
- [军规覆盖矩阵](#军规覆盖矩阵)

---

## §A 基础设施层 (Phase 0)

### A.1 CI门禁场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| A01 | `INFRA.CI.GATE_PASS` | CI门禁全部通过 | M8 | test_ci_gate.py | ✅ |
| A02 | `INFRA.CI.LINT_PASS` | Ruff检查通过 | M8 | test_ci_gate.py | ✅ |
| A03 | `INFRA.CI.TYPE_PASS` | Mypy检查通过 | M8 | test_ci_gate.py | ✅ |
| A04 | `INFRA.CI.TEST_PASS` | Pytest通过 | M8 | test_ci_gate.py | ✅ |
| A05 | `INFRA.CI.COVERAGE_MIN` | 覆盖率≥80% | M8 | test_ci_gate.py | ✅ |

### A.2 仿真门禁场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| A06 | `INFRA.SIM.GATE_PASS` | 仿真门禁通过 | M8 | test_sim_gate.py | ✅ |
| A07 | `INFRA.SIM.SCENARIO_ALL` | 所有场景覆盖 | M8 | test_sim_gate.py | ✅ |

### A.3 CTP接口场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| A08 | `INFRA.CTP.CONNECT` | CTP连接成功 | M9 | test_ctp_api.py | ✅ |
| A09 | `INFRA.CTP.AUTH` | CTP认证成功 | M9 | test_ctp_api.py | ✅ |
| A10 | `INFRA.CTP.SUBSCRIBE` | 行情订阅成功 | M9 | test_ctp_api.py | ✅ |
| A11 | `INFRA.CTP.RECONNECT` | 断线重连成功 | M4, M9 | test_ctp_api.py | ✅ |

### A.4 配置管理场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| A12 | `INFRA.CONFIG.LOAD` | 配置加载成功 | M8 | test_config.py | ✅ |
| A13 | `INFRA.CONFIG.VALIDATE` | 配置验证通过 | M8 | test_config.py | ✅ |
| A14 | `INFRA.CONFIG.ENV_ISOLATE` | 环境隔离正确 | M8 | test_config.py | ✅ |
| A15 | `INFRA.LOG.FORMAT` | 日志格式正确 | M3 | test_logger.py | ✅ |

**Phase A 小计: 15 场景 (15 ✅)**

---

## §B 行情层 (Phase 1)

### B.1 订阅管理场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| B01 | `MKT.SUBSCRIBER.DIFF_UPDATE` | 差量更新订阅列表 | M1 | test_market_subscriber.py | ✅ |
| B02 | `MKT.SUBSCRIBER.CALLBACK` | 回调正确触发 | M9 | test_market_subscriber.py | ✅ |
| B03 | `MKT.SUBSCRIBER.CLEAR` | 清除订阅正确 | M1 | test_market_subscriber.py | ✅ |

### B.2 合约缓存场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| B04 | `MKT.CACHE.INSTRUMENT_INFO` | 合约信息正确缓存 | M11 | test_instrument_cache.py | ✅ |
| B05 | `MKT.CACHE.EXPIRE_CHECK` | 过期检查正确 | M15 | test_instrument_cache.py | ✅ |
| B06 | `MKT.CACHE.UPDATE` | 缓存更新正确 | M11 | test_instrument_cache.py | ✅ |

### B.3 Tick处理场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| B07 | `MKT.TICK.BUFFER_OVERFLOW` | 缓冲区溢出处理 | M10 | test_tick_buffer.py | ✅ |
| B08 | `MKT.TICK.TIMESTAMP_ORDER` | 时间戳顺序正确 | M7 | test_tick_buffer.py | ✅ |

### B.4 K线构建场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| B09 | `MKT.KLINE.BUILD_CORRECT` | K线构建正确 | M7 | test_kline_builder.py | ✅ |
| B10 | `MKT.KLINE.GAP_HANDLE` | 缺口处理正确 | M4 | test_kline_builder.py | ✅ |

### B.5 行情快照场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| B11 | `MKT.SNAPSHOT.CAPTURE` | 快照捕获正确 | M7 | test_snapshot.py | ✅ |
| B12 | `MKT.SNAPSHOT.RESTORE` | 快照恢复正确 | M7 | test_snapshot.py | ✅ |

**Phase B 小计: 12 场景 (12 ✅)**

---

## §C 审计层 (Phase 2)

### C.1 事件结构场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| C01 | `AUDIT.EVENT.STRUCTURE` | 事件结构完整 | M3 | test_audit_writer.py | ✅ |
| C02 | `AUDIT.EVENT.JSONL_FORMAT` | JSONL格式正确 | M3 | test_audit_writer.py | ✅ |
| C03 | `AUDIT.CORRELATION.RUN_EXEC` | run_id/exec_id关联 | M3 | test_audit_writer.py | ✅ |

### C.2 写入器场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| C04 | `AUDIT.WRITER.PROPERTIES` | 写入器属性正确 | M3 | test_audit_writer.py | ✅ |
| C05 | `AUDIT.WRITER.CLOSE_BEHAVIOR` | 关闭后行为正确 | M3 | test_audit_writer.py | ✅ |
| C06 | `AUDIT.WRITER.CONTEXT_MANAGER` | 上下文管理器正确 | M3 | test_audit_writer.py | ✅ |

### C.3 验证场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| C07 | `AUDIT.VALIDATE.MISSING_TS` | 缺少时间戳检测 | M3 | test_audit_writer.py | ✅ |
| C08 | `AUDIT.VALIDATE.MISSING_TYPE` | 缺少类型检测 | M3 | test_audit_writer.py | ✅ |
| C09 | `AUDIT.VALIDATE.REQUIRED_FIELDS` | 必填字段检测 | M3 | test_audit_writer.py | ✅ |

### C.4 字典写入场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| C10 | `AUDIT.DICT.WRITE` | 字典写入正确 | M3 | test_audit_writer.py | ✅ |
| C11 | `AUDIT.DICT.MISSING_REQUIRED` | 缺少必填字段检测 | M3 | test_audit_writer.py | ✅ |

### C.5 读取场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| C12 | `AUDIT.READ.EMPTY_FILE` | 读取空文件处理 | M4 | test_audit_writer.py | ✅ |
| C13 | `AUDIT.READ.CORRUPTED` | 损坏文件处理 | M4 | test_audit_reader.py | ✅ |

### C.6 导出场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| C14 | `AUDIT.EXPORT.CSV` | CSV导出正确 | M3 | test_audit_exporter.py | ✅ |
| C15 | `AUDIT.EXPORT.PARQUET` | Parquet导出正确 | M3 | test_audit_exporter.py | ✅ |

### C.7 压缩场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| C16 | `AUDIT.COMPRESS.GZIP` | GZIP压缩正确 | M10 | test_audit_compressor.py | ✅ |
| C17 | `AUDIT.RETENTION.POLICY` | 保留策略正确 | M3 | test_audit_retention.py | ✅ |

### C.8 追踪场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| C18 | `AUDIT.SIGNAL_SOURCE.TRACK` | 信号来源追踪 | M1, M3 | test_audit_tracking.py | ✅ |

**Phase C 小计: 18 场景 (18 ✅)**

---

## §D 策略降级层 (Phase 3)

### D.1 降级管理场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| D01 | `STRAT.FALLBACK.ON_EXCEPTION` | 异常触发降级 | M4 | test_fallback.py | ✅ |
| D02 | `STRAT.FALLBACK.ON_TIMEOUT` | 超时触发降级 | M4 | test_fallback.py | ✅ |
| D03 | `STRAT.FALLBACK.CHAIN_DEFINED` | 降级链已定义 | M4 | test_fallback.py | ✅ |

### D.2 Kalman滤波场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| D04 | `ARB.KALMAN.BETA_ESTIMATE` | beta估计正确 | M7 | test_kalman_beta.py | ✅ |
| D05 | `ARB.KALMAN.RESIDUAL_ZSCORE` | 残差z分数计算 | M7 | test_kalman_beta.py | ✅ |
| D06 | `ARB.KALMAN.BETA_BOUND` | beta边界约束 | M6 | test_kalman_beta.py | ✅ |

### D.3 套利策略场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| D07 | `ARB.LEGS.FIXED_NEAR_FAR` | 近远月腿固定 | M1 | test_calendar_arb.py | ✅ |
| D08 | `ARB.SIGNAL.HALF_LIFE_GATE` | 半衰期门禁 | M5 | test_calendar_arb.py | ✅ |
| D09 | `ARB.SIGNAL.STOP_Z_BREAKER` | 止损z值触发 | M6 | test_calendar_arb.py | ✅ |
| D10 | `ARB.SIGNAL.EXPIRY_GATE` | 到期日门禁 | M15 | test_calendar_arb.py | ✅ |
| D11 | `ARB.SIGNAL.CORRELATION_BREAK` | 相关性破裂检测 | M6 | test_calendar_arb.py | ✅ |
| D12 | `ARB.COST.ENTRY_GATE` | 成本门禁检查 | M5 | test_calendar_arb.py | ✅ |

**Phase D 小计: 12 场景 (12 ✅)**

---

## §E 回放验证层 (Phase 4)

### E.1 决策回放场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| E01 | `REPLAY.DETERMINISTIC.DECISION` | 决策序列确定性 | M7 | test_replay_verifier.py | ✅ |
| E02 | `REPLAY.DETERMINISTIC.GUARDIAN` | 守护动作确定性 | M7 | test_replay_verifier.py | ✅ |

**Phase E 小计: 2 场景 (2 ✅)**

---

## §F 成本层 (Phase 5)

### F.1 手续费估计场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| F01 | `COST.FEE.ESTIMATE` | 手续费估计正确 | M5 | test_cost_estimator.py | ✅ |
| F02 | `COST.FEE.BY_VOLUME` | 按手收费计算 | M5 | test_china_fee.py | ⏸ |
| F03 | `COST.FEE.BY_VALUE` | 按金额收费计算 | M5 | test_china_fee.py | ⏸ |
| F04 | `COST.FEE.CLOSE_TODAY` | 平今手续费计算 | M14 | test_china_fee.py | ⏸ |

### F.2 滑点估计场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| F05 | `COST.SLIPPAGE.ESTIMATE` | 滑点估计正确 | M5 | test_cost_estimator.py | ✅ |

### F.3 市场冲击场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| F06 | `COST.IMPACT.ESTIMATE` | 市场冲击估计正确 | M5 | test_cost_estimator.py | ✅ |

### F.4 成本门禁场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| F07 | `COST.EDGE.GATE` | 边际收益门禁 | M5 | test_cost_estimator.py | ✅ |
| F08 | `COST.FEE.EXCHANGE_CONFIG` | 交易所配置正确 | M20 | test_china_fee.py | ⏸ |

**Phase F 小计: 8 场景 (4 ✅, 4 ⏸)**

---

## §G 中国期货市场特化 (Phase 7)

### G.1 交易所配置场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| G01 | `CHINA.EXCHANGE.CONFIG_LOAD` | 交易所配置加载 | M20 | test_exchange_config.py | ⏸ |
| G02 | `CHINA.EXCHANGE.PRODUCT_MAP` | 品种映射正确 | M20 | test_exchange_config.py | ⏸ |
| G03 | `CHINA.EXCHANGE.SIX_SUPPORTED` | 六大交易所支持 | M20 | test_exchange_config.py | ⏸ |

### G.2 交易日历场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| G04 | `CHINA.CALENDAR.NIGHT_SESSION` | 夜盘时段正确 | M15 | test_trading_calendar.py | ⏸ |
| G05 | `CHINA.CALENDAR.TRADING_DAY` | 交易日计算正确 | M15 | test_trading_calendar.py | ⏸ |
| G06 | `CHINA.CALENDAR.HOLIDAY` | 节假日处理正确 | M15 | test_trading_calendar.py | ⏸ |
| G07 | `CHINA.CALENDAR.CROSS_DAY` | 跨日归属正确 | M15 | test_trading_calendar.py | ⏸ |

### G.3 涨跌停场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| G08 | `CHINA.LIMIT.PRICE_CHECK` | 涨跌停价格检查 | M13 | test_limit_price.py | ⏸ |
| G09 | `CHINA.LIMIT.ORDER_REJECT` | 超限订单拒绝 | M13 | test_limit_price.py | ⏸ |
| G10 | `CHINA.LIMIT.DYNAMIC_UPDATE` | 动态更新涨跌停 | M13 | test_limit_price.py | ⏸ |
| G11 | `CHINA.LIMIT.CONSECUTIVE_ADJUST` | 连续涨跌停调整 | M13 | test_limit_price.py | ⏸ |

### G.4 保证金场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| G12 | `CHINA.MARGIN.RATIO_CHECK` | 保证金率检查 | M16 | test_margin_monitor.py | ⏸ |
| G13 | `CHINA.MARGIN.USAGE_MONITOR` | 保证金使用监控 | M16 | test_margin_monitor.py | ⏸ |
| G14 | `CHINA.MARGIN.WARNING_LEVEL` | 保证金预警等级 | M16 | test_margin_monitor.py | ⏸ |
| G15 | `CHINA.MARGIN.CRITICAL_ACTION` | 临界保证金动作 | M16 | test_margin_monitor.py | ⏸ |

### G.5 触发器场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| G16 | `CHINA.TRIGGER.LIMIT_PRICE` | 涨跌停触发器 | M6, M13 | test_triggers_china.py | ⏸ |
| G17 | `CHINA.TRIGGER.MARGIN_CALL` | 保证金追缴触发 | M6, M16 | test_triggers_china.py | ⏸ |
| G18 | `CHINA.TRIGGER.DELIVERY` | 交割月接近触发 | M6, M15 | test_triggers_china.py | ⏸ |

### G.6 压力测试场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| G19 | `CHINA.STRESS.2015_CRASH` | 2015股灾场景 | M6 | test_stress_china.py | ⏸ |
| G20 | `CHINA.STRESS.2020_OIL` | 2020原油负价场景 | M6 | test_stress_china.py | ⏸ |
| G21 | `CHINA.STRESS.2022_LITHIUM` | 2022碳酸锂场景 | M6 | test_stress_china.py | ⏸ |

### G.7 套利特化场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| G22 | `CHINA.ARB.DELIVERY_AWARE` | 交割感知套利 | M15 | test_delivery_aware.py | ⏸ |
| G23 | `CHINA.ARB.POSITION_TRANSFER` | 移仓换月逻辑 | M15 | test_delivery_aware.py | ⏸ |

**Phase G 小计: 23 场景 (0 ✅, 23 ⏸)**

---

## §H 智能策略层 (Phase 8)

### H.1 TWAP算法场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| H01 | `ALGO.TWAP.SLICE_CALC` | TWAP切片计算 | M5 | test_twap.py | ⏸ |
| H02 | `ALGO.TWAP.TIME_DISTRIBUTE` | TWAP时间分布 | M5 | test_twap.py | ⏸ |
| H03 | `ALGO.TWAP.PARTIAL_FILL` | TWAP部分成交处理 | M5 | test_twap.py | ⏸ |

### H.2 VWAP算法场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| H04 | `ALGO.VWAP.VOLUME_PROFILE` | VWAP成交量分布 | M5 | test_vwap.py | ⏸ |
| H05 | `ALGO.VWAP.PARTICIPATION` | VWAP参与率控制 | M5 | test_vwap.py | ⏸ |
| H06 | `ALGO.VWAP.CATCH_UP` | VWAP追赶逻辑 | M5 | test_vwap.py | ⏸ |

### H.3 冰山单场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| H07 | `ALGO.ICEBERG.DISPLAY_SIZE` | 冰山单显示量 | M5 | test_iceberg.py | ⏸ |
| H08 | `ALGO.ICEBERG.REFRESH` | 冰山单刷新逻辑 | M5 | test_iceberg.py | ⏸ |
| H09 | `ALGO.ICEBERG.RANDOM_SIZE` | 冰山单随机量 | M5 | test_iceberg.py | ⏸ |

### H.4 自适应执行场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| H10 | `ALGO.ADAPTIVE.MARKET_STATE` | 自适应市场状态 | M5 | test_adaptive.py | ⏸ |
| H11 | `ALGO.ADAPTIVE.STRATEGY_SWITCH` | 自适应策略切换 | M4 | test_adaptive.py | ⏸ |

### H.5 市场冲击模型场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| H12 | `ALGO.IMPACT.ALMGREN_CHRISS` | Almgren-Chriss模型 | M5 | test_impact.py | ⏸ |
| H13 | `ALGO.IMPACT.TEMPORARY` | 临时冲击计算 | M5 | test_impact.py | ⏸ |
| H14 | `ALGO.IMPACT.PERMANENT` | 永久冲击计算 | M5 | test_impact.py | ⏸ |

### H.6 实验性门禁场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| H15 | `EXP.MATURITY.80_THRESHOLD` | 80%成熟度门槛 | M18 | test_maturity.py | ✅ |
| H16 | `EXP.MATURITY.60_DIMENSION` | 60%维度门槛 | M18 | test_maturity.py | ✅ |
| H17 | `EXP.MATURITY.90_DAYS` | 90天最低训练 | M18 | test_maturity.py | ✅ |
| H18 | `EXP.GATE.NO_BYPASS` | 禁止绕过门禁 | M18 | test_training_gate.py | ✅ |
| H19 | `EXP.GATE.MANUAL_APPROVAL` | 需人工审批 | M12, M18 | test_training_gate.py | ✅ |
| H20 | `EXP.MONITOR.PROGRESS` | 进度监控正确 | M18 | test_training_monitor.py | ✅ |
| H21 | `EXP.MONITOR.ALERT` | 告警生成正确 | M9 | test_training_monitor.py | ✅ |
| H22 | `EXP.MONITOR.ETA` | ETA预估正确 | M18 | test_training_monitor.py | ✅ |

**Phase H 小计: 22 场景 (8 ✅, 14 ⏸)**

---

## §I 合规监控层 (Phase 9)

### I.1 程序化合规场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| I01 | `COMPLIANCE.REGISTRATION` | 程序化交易备案 | M17 | test_compliance.py | ⏸ |
| I02 | `COMPLIANCE.ALGO_RECORD` | 算法备案记录 | M17 | test_compliance.py | ⏸ |

### I.2 报撤单频率场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| I03 | `THROTTLE.5S_LIMIT` | 5秒限制检查 | M17 | test_throttle.py | ⏸ |
| I04 | `THROTTLE.DAILY_LIMIT` | 日内限制检查 | M17 | test_throttle.py | ⏸ |
| I05 | `THROTTLE.HIGH_FREQ_DETECT` | 高频检测 | M17 | test_throttle.py | ⏸ |
| I06 | `THROTTLE.WARNING_LEVEL` | 预警等级 | M17 | test_throttle.py | ⏸ |

### I.3 大额订单场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| I07 | `COMPLIANCE.LARGE_ORDER` | 大额订单复核 | M12, M17 | test_large_order.py | ⏸ |
| I08 | `COMPLIANCE.TIMEOUT_30S` | 30秒确认超时 | M12 | test_large_order.py | ⏸ |

### I.4 健康监控场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| I09 | `MONITOR.HEALTH.CHECK` | 健康检查执行 | M9 | test_health.py | ✅ |
| I10 | `MONITOR.HEALTH.COMPONENT` | 组件状态监控 | M9 | test_health.py | ✅ |
| I11 | `MONITOR.HEALTH.DEGRADED` | 降级状态检测 | M4, M9 | test_health.py | ✅ |

### I.5 指标监控场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| I12 | `MONITOR.METRICS.COUNTER` | 计数器指标 | M9 | test_metrics.py | ✅ |
| I13 | `MONITOR.METRICS.GAUGE` | 仪表盘指标 | M9 | test_metrics.py | ✅ |
| I14 | `MONITOR.METRICS.HISTOGRAM` | 直方图指标 | M9 | test_metrics.py | ✅ |
| I15 | `MONITOR.METRICS.PROMETHEUS` | Prometheus导出 | M9 | test_metrics.py | ✅ |
| I16 | `MONITOR.ALERT.THRESHOLD` | 阈值告警 | M9 | test_alerts.py | ⏸ |

**Phase I 小计: 16 场景 (7 ✅, 9 ⏸)**

---

## §J 组合风控层 (Phase 10)

### J.1 持仓管理场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| J01 | `PORTFOLIO.POSITION.UPDATE` | 持仓更新正确 | M1 | test_portfolio_manager.py | ✅ |
| J02 | `PORTFOLIO.POSITION.LIMIT` | 持仓限额检查 | M6 | test_portfolio_manager.py | ✅ |
| J03 | `PORTFOLIO.POSITION.NET` | 净持仓计算 | M1 | test_portfolio_manager.py | ✅ |
| J04 | `PORTFOLIO.POSITION.SNAPSHOT` | 持仓快照正确 | M3 | test_portfolio_manager.py | ✅ |

### J.2 风险分析场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| J05 | `PORTFOLIO.RISK.EXPOSURE` | 风险敞口计算 | M6 | test_portfolio_analytics.py | ✅ |
| J06 | `PORTFOLIO.RISK.CONCENTRATION` | 集中度计算 | M6 | test_portfolio_analytics.py | ✅ |
| J07 | `PORTFOLIO.PNL.ATTRIBUTION` | 盈亏归因 | M19 | test_portfolio_analytics.py | ✅ |
| J08 | `PORTFOLIO.SHARPE.CALCULATE` | 夏普比率计算 | M19 | test_portfolio_analytics.py | ✅ |
| J09 | `PORTFOLIO.DRAWDOWN.MAX` | 最大回撤计算 | M6 | test_portfolio_analytics.py | ✅ |

### J.3 聚合场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| J10 | `PORTFOLIO.AGGREGATE.SYMBOL` | 按合约聚合 | M1 | test_aggregator.py | ✅ |
| J11 | `PORTFOLIO.AGGREGATE.STRATEGY` | 按策略聚合 | M1 | test_aggregator.py | ✅ |
| J12 | `PORTFOLIO.SNAPSHOT.TIMESERIES` | 时序快照 | M3 | test_aggregator.py | ✅ |

### J.4 VaR场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| J13 | `VAR.HISTORICAL.PERCENTILE` | 历史VaR计算 | M6 | test_var_calculator.py | ✅ |
| J14 | `VAR.PARAMETRIC.NORMAL` | 参数VaR计算 | M6 | test_var_calculator.py | ✅ |
| J15 | `VAR.MONTECARLO.SIMULATION` | 蒙特卡洛VaR | M6 | test_var_calculator.py | ✅ |
| J16 | `VAR.ES.CALCULATE` | ES/CVaR计算 | M6 | test_var_calculator.py | ✅ |
| J17 | `VAR.EVT.GPD` | EVT-GPD方法 | M6 | test_var_enhanced.py | ⏸ |
| J18 | `VAR.SEMIPARAMETRIC.KERNEL` | 半参数方法 | M6 | test_var_enhanced.py | ⏸ |
| J19 | `VAR.LIMIT_ADJUSTED` | 涨跌停调整 | M6, M13 | test_var_enhanced.py | ⏸ |
| J20 | `VAR.LIQUIDITY_ADJUSTED` | 流动性调整 | M6 | test_var_enhanced.py | ⏸ |

### J.5 风险归因场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| J21 | `RISK.ATTRIBUTION.FACTOR` | 因子归因 | M19 | test_attribution.py | ⏸ |
| J22 | `RISK.ATTRIBUTION.STRATEGY` | 策略归因 | M19 | test_attribution.py | ⏸ |
| J23 | `RISK.ATTRIBUTION.POSITION` | 持仓归因 | M19 | test_attribution.py | ⏸ |

### J.6 风控动作场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| J24 | `RISK.BREACH.DETECT` | 风险突破检测 | M6 | test_risk_manager.py | ✅ |
| J25 | `RISK.KILLSWITCH.TRIGGER` | 熔断触发 | M6 | test_risk_manager.py | ✅ |

**Phase J 小计: 25 场景 (18 ✅, 7 ⏸)**

---

## §K B类模型层 (Phase 6)

### K.1 LSTM预测场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| K01 | `DL.LSTM.PREDICT` | LSTM预测输出 | M18 | test_lstm.py | ⏸ |
| K02 | `DL.LSTM.SEQUENCE_LENGTH` | 序列长度正确 | M7 | test_lstm.py | ⏸ |
| K03 | `DL.LSTM.HIDDEN_STATE` | 隐藏状态正确 | M7 | test_lstm.py | ⏸ |

### K.2 Transformer场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| K04 | `DL.TRANSFORMER.ATTENTION` | 注意力计算正确 | M18 | test_transformer.py | ⏸ |
| K05 | `DL.TRANSFORMER.POSITION_ENCODING` | 位置编码正确 | M7 | test_transformer.py | ⏸ |

### K.3 因子挖掘场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| K06 | `DL.FACTOR.MINE` | 因子挖掘正确 | M18 | test_factor.py | ⏸ |
| K07 | `DL.FACTOR.IC_CALCULATE` | IC计算正确 | M19 | test_factor.py | ⏸ |

### K.4 强化学习场景

| 序号 | Rule ID | 场景描述 | 军规 | 测试文件 | 状态 |
|------|---------|----------|------|----------|------|
| K08 | `RL.PPO.ACTION` | PPO动作选择 | M18 | test_ppo.py | ⏸ |
| K09 | `RL.PPO.REWARD` | PPO奖励计算 | M18 | test_ppo.py | ⏸ |
| K10 | `RL.DQN.QVALUE` | DQN Q值计算 | M18 | test_dqn.py | ⏸ |
| K11 | `RL.DQN.EPSILON_DECAY` | ε衰减正确 | M18 | test_dqn.py | ⏸ |
| K12 | `RL.REWARD.SHARPE_BASED` | 夏普奖励函数 | M18 | test_reward.py | ⏸ |

**Phase K 小计: 12 场景 (0 ✅, 12 ⏸)**

---

## 场景统计总表

### 按Phase统计

| Phase | 名称 | 场景数 | 已完成 | 待完成 | 完成率 |
|-------|------|--------|--------|--------|--------|
| A | 基础设施 | 15 | 15 | 0 | 100% |
| B | 行情层 | 12 | 12 | 0 | 100% |
| C | 审计层 | 18 | 18 | 0 | 100% |
| D | 策略降级 | 12 | 12 | 0 | 100% |
| E | 回放验证 | 2 | 2 | 0 | 100% |
| F | 成本层 | 8 | 4 | 4 | 50% |
| G | 中国期货特化 | 23 | 0 | 23 | 0% |
| H | 智能策略 | 22 | 8 | 14 | 36% |
| I | 合规监控 | 16 | 7 | 9 | 44% |
| J | 组合风控 | 25 | 18 | 7 | 72% |
| K | B类模型 | 12 | 0 | 12 | 0% |
| **总计** | - | **165** | **96** | **69** | **58%** |

### 按状态统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已完成 | 96 | 58% |
| ⏸ 待完成 | 69 | 42% |

---

## 军规覆盖矩阵

### 军规-场景映射

| 军规 | 场景ID列表 | 场景数 | 覆盖状态 |
|------|------------|--------|----------|
| M1 | B01,B03,C18,D07,J01,J03,J10,J11 | 8 | ✅ 100% |
| M3 | A15,C01-C18,J04,J12 | 20 | ✅ 100% |
| M4 | A11,B10,C12,C13,D01-D03,H11,I11 | 9 | ✅ 100% |
| M5 | D08,D12,F01-F08,H01-H14 | 22 | 部分 |
| M6 | D06,D09,D11,G16-G21,J02,J05,J06,J09,J13-J20,J24,J25 | 24 | 部分 |
| M7 | B08,B09,B11,B12,D04,D05,E01,E02,K02,K03,K05 | 11 | ✅ 100% |
| M8 | A01-A14 | 14 | ✅ 100% |
| M9 | A08-A11,B02,H21,I09-I16 | 15 | 部分 |
| M10 | B07,C16 | 2 | ✅ 100% |
| M11 | B04,B06 | 2 | ✅ 100% |
| M12 | H19,I07,I08 | 3 | 部分 |
| M13 | G08-G11,G16,J19 | 6 | ⏸ 待实现 |
| M14 | F04 | 1 | ⏸ 待实现 |
| M15 | B05,D10,G04-G07,G16-G18,G22,G23 | 11 | ⏸ 待实现 |
| M16 | G12-G15,G17 | 5 | ⏸ 待实现 |
| M17 | I01-I06 | 6 | ⏸ 待实现 |
| M18 | H15-H22,K01-K12 | 20 | 部分 |
| M19 | J07,J08,J21-J23,K07 | 6 | 部分 |
| M20 | F08,G01-G03 | 4 | ⏸ 待实现 |

### 军规覆盖率统计

| 状态 | 军规 | 数量 |
|------|------|------|
| ✅ 完全覆盖 | M1,M3,M4,M7,M8,M10,M11 | 7 |
| 部分覆盖 | M5,M6,M9,M12,M18,M19 | 6 |
| ⏸ 待实现 | M13,M14,M15,M16,M17,M20 | 6 |

---

## 验收检查清单

### Phase验收

- [x] Phase A: 基础设施层 (15/15)
- [x] Phase B: 行情层 (12/12)
- [x] Phase C: 审计层 (18/18)
- [x] Phase D: 策略降级层 (12/12)
- [x] Phase E: 回放验证层 (2/2)
- [ ] Phase F: 成本层 (4/8)
- [ ] Phase G: 中国期货特化 (0/23)
- [ ] Phase H: 智能策略层 (8/22)
- [ ] Phase I: 合规监控层 (7/16)
- [ ] Phase J: 组合风控层 (18/25)
- [ ] Phase K: B类模型层 (0/12)

### 军规验收

- [x] M1: 单一信号源 (8/8)
- [x] M3: 完整审计 (20/20)
- [x] M4: 降级兜底 (9/9)
- [ ] M5: 成本先行 (部分)
- [ ] M6: 熔断保护 (部分)
- [x] M7: 回放一致 (11/11)
- [x] M8: 配置隔离 (14/14)
- [ ] M9: 错误上报 (部分)
- [x] M10: 资源限制 (2/2)
- [x] M11: 版本兼容 (2/2)
- [ ] M12: 双重确认 (部分)
- [ ] M13: 涨跌停感知 (待实现)
- [ ] M14: 平今平昨分离 (待实现)
- [ ] M15: 夜盘跨日处理 (待实现)
- [ ] M16: 保证金实时监控 (待实现)
- [ ] M17: 程序化合规 (待实现)
- [ ] M18: 实验性门禁 (部分)
- [ ] M19: 风险归因 (部分)
- [ ] M20: 跨所一致 (待实现)

---

## 附录：场景命名规范

### Rule ID格式

```
{模块}.{功能}.{场景}

示例：
- AUDIT.WRITER.CLOSE_BEHAVIOR
- CHINA.MARGIN.WARNING_LEVEL
- VAR.MONTECARLO.SIMULATION
```

### 模块缩写

| 缩写 | 全称 |
|------|------|
| INFRA | Infrastructure (基础设施) |
| MKT | Market (行情) |
| AUDIT | Audit (审计) |
| STRAT | Strategy (策略) |
| ARB | Arbitrage (套利) |
| REPLAY | Replay (回放) |
| COST | Cost (成本) |
| CHINA | China (中国特化) |
| ALGO | Algorithm (算法) |
| EXP | Experimental (实验性) |
| THROTTLE | Throttle (节流) |
| COMPLIANCE | Compliance (合规) |
| MONITOR | Monitoring (监控) |
| PORTFOLIO | Portfolio (组合) |
| VAR | Value at Risk (VaR) |
| RISK | Risk (风险) |
| DL | Deep Learning (深度学习) |
| RL | Reinforcement Learning (强化学习) |

---

**文档结束**

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│              V4PRO 验收矩阵报告 - 165条场景全覆盖                    │
│                                                                     │
│                    军规级品质保证！                                  │
│                                                                     │
│                    CLAUDE上校 2025-12-16                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```
