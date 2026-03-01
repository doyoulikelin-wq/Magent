# MetaboDash 开发日志（V0.1）

## 更新日志

### 2026-03-01 Phase 2 — devlog §11 三项改动实现（干预等级 / Payload 契约 / 设置页）

> 完成时间：2026-03-01 03:40 CST

#### 概述

根据 devlog §11 新增改动，完成干预等级机制、AgentAction payload 契约校验、用户设置页（前后端）的全栈实现。所有组件通过集成烟雾测试，前端 TypeScript 编译零错误。

#### 新增 / 修改文件清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/app/core/intervention.py` | 新增 | InterventionLevel 枚举、RiskLevel 枚举、TriggerStrategy 数据类、STRATEGIES 参数表、`classify_risk()` / `get_strategy()` |
| `backend/app/models/user_settings.py` | 新增 | UserSettings 模型（intervention_level、daily_reminder_limit、allow_auto_escalation） |
| `backend/app/models/agent.py` | 修改 | AgentAction 新增 5 字段：payload_version、status（ActionStatus 枚举）、priority、error_code、trace_id |
| `backend/app/models/__init__.py` | 修改 | 导出 UserSettings |
| `backend/app/services/payload_schemas.py` | 新增 | 4 种 action_type 的 JSON Schema 定义（pre_meal_sim / rescue / daily_plan / weekly_goal），SCHEMA_REGISTRY 注册表 |
| `backend/app/services/payload_validator.py` | 新增 | `validate_payload()` — 校验 + 降级 + 安全回退；ValidationResult 数据类；trace_id 生成 |
| `backend/app/schemas/settings.py` | 新增 | UserSettingsOut（含 InterventionStrategyOut）、UserSettingsUpdate |
| `backend/app/schemas/user.py` | 修改 | UserMeOut 增加 `settings` 字段 |
| `backend/app/routers/users.py` | 修改 | 新增 GET/PATCH `/api/users/settings`；`/api/users/me` 返回 settings |
| `backend/app/db/migrations/versions/0003_intervention_levels.py` | 新增 | user_settings 表 + agent_actions 5 列 + actionstatus 枚举 |
| `backend/app/db/migrations/env.py` | 修改 | 导入 user_settings 模块 |
| `backend/pyproject.toml` | 修改 | 新增 `jsonschema>=4.21` 依赖 |
| `frontend/src/api/types.ts` | 修改 | 新增 UserSettings、InterventionStrategy 类型 |
| `frontend/src/api/hooks.ts` | 修改 | 新增 `useSettings()` / `useUpdateSettings()` hooks |
| `frontend/src/pages/SettingsPage.tsx` | 重写 | 干预等级三列选择卡片 + 提醒偏好 + 自动升级开关 + 原有隐私设置 |

#### 关键设计决策

1. **校验失败策略**：拦截 + 日志 + 安全回退（不下发无效 payload，生成中文安全文案替代）
2. **三态模型**：payload 校验结果分 `valid` / `degraded` / `invalid`，均记录 trace_id 可追溯
3. **懒创建 UserSettings**：首次访问设置 API 时自动创建默认 L2 记录，无需注册流程改动
4. **等级切换即时生效**：PATCH 后前端 invalidate settings + me 两个 query

#### 验证结果

- 干预等级 L1/L2/L3 策略参数解析 ✅
- 风险分类 low/medium/high ✅
- 4 种 action_type Schema 注册 ✅
- 有效 payload 校验通过（status=valid）✅
- 无效 payload 降级回退（status=degraded，中文安全文案）✅
- 未知 schema 拒绝（status=invalid，SCHEMA_NOT_FOUND）✅
- Settings API 路由注册（2 条）✅
- 前端 TypeScript 编译零错误 ✅（prebuild glob 依赖已移除，`npm run build` 通过）

---

### 2026-03-01 Phase 1 — 数据管线 ETL 全栈实现

> 完成时间：2026-03-01 02:00 CST

#### 概述

构建完整的数据导入管线（ETL），覆盖血糖 CGM 数据（65 个 Clarity CSV → 151,097 条读数）、膳食数据（activity_food.csv + index_corrected_oncurve.csv → 2,160 条校正事件）、特征工程（TIR/CV/AUC/餐后响应斜率等，按 24h/7d/28d 窗口计算）。

#### 新增 / 修改文件清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/app/models/user_profile.py` | 新增 | UserProfile 模型（subject_id、人口统计学、cohort） |
| `backend/app/models/feature.py` | 新增 | FeatureSnapshot 模型（user_id、window、features JSONB） |
| `backend/app/models/agent.py` | 新增 | AgentState、AgentAction、OutcomeFeedback 模型 |
| `backend/app/models/__init__.py` | 修改 | 导出所有新模型 |
| `backend/app/services/etl/__init__.py` | 新增 | ETL 包初始化 |
| `backend/app/services/etl/glucose_etl.py` | 新增 | Clarity CSV 解析、mmol/L→mg/dL 转换、按 subject 去重入库 |
| `backend/app/services/etl/meal_etl.py` | 新增 | activity_food.csv + index_corrected_oncurve.csv 导入、时间格式兼容 |
| `backend/app/services/etl/feature_compute.py` | 新增 | 多窗口特征计算（TIR/CV/夜间变异/AUC/餐后响应斜率） |
| `backend/app/schemas/etl.py` | 新增 | ETLRunResponse、FeatureSnapshotOut |
| `backend/app/routers/etl.py` | 新增 | POST /api/etl/run-batch、GET /api/etl/features/{subject_id}、POST /api/etl/features/recompute、GET /api/etl/subjects |
| `backend/app/db/migrations/versions/0002_agentic.py` | 新增 | user_profiles、agent_states、agent_actions、outcome_feedbacks、feature_snapshots 表 |
| `backend/app/db/migrations/env.py` | 修改 | 导入新模型模块 |
| `backend/app/core/config.py` | 修改 | 新增 DATA_DIR 配置项 |
| `backend/app/main.py` | 修改 | 注册 ETL 路由 |
| `backend/pyproject.toml` | 修改 | 新增 `numpy>=1.26` 依赖 |

#### 数据概况

| 数据源 | 文件数 | 记录数 | 受试者 |
|---|---|---|---|
| Clarity CGM CSV | 65 | 151,097 EGV | 63 unique SC subjects |
| activity_food.csv | 1 | ~12,000 raw | — |
| index_corrected_oncurve.csv | 1 | 2,160 filtered | — |
| 脂肪肝数据 | 105 (Excel/PDF) | 25 Liver-xxx | 独立队列，暂不接入 |

#### 验证结果

- 65 CSV 全部解析成功，151,097 条 EGV 读数 ✅
- 63 unique subject 识别 ✅
- 2,160 条校正餐事件导入 ✅
- 特征计算 TIR/CV/AUC 正确 ✅
- 4 个 ETL API 路由注册 ✅
- FastAPI 共 33 条路由正常 ✅

---
