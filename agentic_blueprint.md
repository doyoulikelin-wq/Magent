# MetaboDash Agentic Service 蓝图（V0.1）

## 11. V0.1 新增改动（2026-03-01）

> 本节为新增内容，前文保持不变。
> 改动日期：2026-03-01（Asia/Shanghai）

### 11.1 干预等级机制（Intervention Levels）

为解决触发策略不够具体的问题，新增用户可选干预等级。干预等级不是文案差异，而是规则参数差异。

#### Level 定义

1. `L1 温和`：低打扰，适合新用户或不希望被频繁提醒的用户。
2. `L2 标准`：默认等级，平衡提醒频率与效果。
3. `L3 积极`：高敏感触发，适合短期强化管理。

#### 触发策略参数表

| 维度 | L1 温和 | L2 标准 | L3 积极 |
|---|---|---|---|
| 风险触发门槛 | 高风险才触发 | 中高风险触发 | 中风险以上触发 |
| 每日主动提醒上限 | 1 次 | 2 次 | 4 次 |
| 单餐最多提醒 | 1 次 | 2 次 | 3 次 |
| 建议动作数 | 1 条 | 1-2 条 | 2-3 条 |
| 是否要求复盘 | 可选 | 建议复盘 | 默认复盘 |
| 连续异常升级 | 不自动升级 | 连续 2 天可升级 | 连续 1 天可升级 |

#### 风险分层建议（可配置）

1. `low`：风险分 < 0.40
2. `medium`：0.40 <= 风险分 < 0.70
3. `high`：风险分 >= 0.70

#### 默认策略

1. 新用户默认 `L2`
2. 用户可在设置页随时手动切换
3. 系统只建议升级，不自动改用户等级（除非用户授权自动策略）

### 11.2 AgentAction 接口契约（Payload Schema + Versioning）

为解决“行动接口没落到契约级别”的问题，新增 `AgentAction.payload` 标准结构与版本机制，避免自由文本导致前后端不稳定。

#### 11.2.1 AgentAction 通用结构

```json
{
  "action_id": "act_20260301_0001",
  "user_id": "SC003",
  "action_type": "post_meal_rescue",
  "payload_version": "1.0.0",
  "created_ts": "2026-03-01T10:05:00+08:00",
  "priority": "medium",
  "payload": {},
  "reason_evidence": {
    "window": "last_14d",
    "signals": ["predicted_peak_high", "rapid_rise_30min"],
    "summary": "近14天晚餐后峰值偏高，本次上升速率超过个人阈值"
  }
}
```

#### 11.2.2 各动作类型 payload 要求

##### A. `pre_meal_sim`

```json
{
  "title": "吃前预演",
  "meal_input": {"kcal": 650, "meal_time": "2026-03-01T12:30:00+08:00"},
  "prediction": {
    "peak_glucose": 9.6,
    "time_to_peak_min": 65,
    "auc_0_120": 180.2,
    "liver_load_score": 0.72
  },
  "alternatives": [
    {"id": "alt_reduce_carb", "label": "主食减少20%", "expected_delta_peak": -0.6},
    {"id": "alt_delay_30m", "label": "延后30分钟进食", "expected_delta_peak": -0.3}
  ]
}
```

##### B. `post_meal_rescue`

```json
{
  "title": "吃后补救",
  "risk_level": "high",
  "trigger_evidence": ["slope_30min_high", "predicted_peak_over_threshold"],
  "steps": [
    {"id": "walk_12m", "label": "现在步行12分钟", "duration_min": 12},
    {"id": "hydrate", "label": "饮水300ml"}
  ],
  "expected_effect": {"delta_peak_low": 0.3, "delta_peak_high": 0.8},
  "followup": {"checkpoints_min": [30, 60, 120]},
  "expires_at": "2026-03-01T14:30:00+08:00"
}
```

##### C. `daily_plan`

```json
{
  "title": "今日代谢天气",
  "risk_windows": [
    {"start": "12:00", "end": "14:00", "risk": "medium"},
    {"start": "19:00", "end": "21:30", "risk": "high"}
  ],
  "today_goals": [
    "晚餐后10分钟内开始步行",
    "今日最后一餐热量控制在600kcal以内"
  ]
}
```

##### D. `weekly_goal`

```json
{
  "title": "周目标",
  "focus": "降低晚餐后峰值",
  "target": {
    "metric": "post_dinner_delta_peak",
    "baseline": 3.2,
    "goal": 2.6,
    "unit": "mmol/L",
    "window_days": 7
  },
  "tasks": [
    "晚餐主食减20%",
    "晚餐后步行15分钟（>=4天）"
  ]
}
```

#### 11.2.3 版本控制规则

1. `payload_version` 使用语义化版本（SemVer）：`MAJOR.MINOR.PATCH`
2. `PATCH`：仅修正文案/可选字段，不影响兼容
3. `MINOR`：新增向后兼容字段
4. `MAJOR`：字段含义或必填项变化，不向后兼容
5. 前端按 `action_type + payload_version` 路由解析器
6. 后端保留旧版本解析至少 2 个小版本周期

#### 11.2.4 校验与审计要求

1. 所有 `AgentAction.payload` 在入库前做 JSON Schema 校验
2. 校验失败不得下发给用户，需记录 `error_code + trace_id`
3. 每条动作必须可回放：`action_id` 可定位原始 payload 与 reason_evidence

### 11.3 设置页新增项（用户可见）

1. 干预等级选择：`L1/L2/L3`
2. 每日提醒上限可调（在等级上限内）
3. 是否允许“连续异常自动建议升级”

### 11.4 验收标准新增

1. 100% 动作卡符合 `payload schema`
2. 100% 动作记录包含 `payload_version`
3. 干预等级切换后 5 分钟内生效
4. 触发日志可追溯到具体阈值与证据信号



## 1. 项目目标（为什么做）

### 1.1 产品目标
将现有“工具型健康面板”升级为“代理型健康服务（Agentic Service）”，让用户感知到：

1. 系统能主动观察并发现问题（不是等用户来问）
2. 系统能在关键时刻给可执行建议（不是泛泛而谈）
3. 系统能追踪建议是否有效并自动调整（形成闭环）

### 1.2 用户体验目标
用户在功能上应明显感受到 4 种“智能体验”：

1. 吃前预判：还没吃就能知道对血糖/肝脏负担的影响
2. 吃后补救：出现高风险趋势时给实时可执行动作
3. 日内编排：每天自动给出高风险时段与行动窗口
4. 周度教练：自动复盘并形成下周个体化目标

### 1.3 业务目标（可量化）

1. 餐后 2h 峰值（Delta Peak）下降
2. AUC（餐后负担）下降
3. TIR（70-180）提升
4. 建议采纳率、完成率提升

---

## 2. 核心功能设计（让用户“体会到”agentic）

## 2.1 功能 A：吃前预演（Pre-Meal Simulator）

**用户动作**：输入/选择即将吃的食物（或热量）+ 时间

**系统输出**：

1. 预计 2h 血糖响应曲线（峰值、到峰时间）
2. 预计肝脏负担分（Liver Load）
3. 最小改动替代方案（例如：延后 30 分钟、减少 20% 主食、先走 10 分钟）

**体验价值**：用户感知“系统能提前思考并给选择空间”。

## 2.2 功能 B：吃后补救（Post-Meal Rescue）

**触发条件**：检测到餐后快速上升/超阈趋势

**系统输出**：

1. 实时补救动作卡（步行时长、补水、下一餐控制建议）
2. 预计可降低的峰值区间（透明说明不确定性）
3. 30/60/120 分钟追踪提醒与复盘

**体验价值**：用户感知“系统在关键时刻接管问题处理”。

## 2.3 功能 C：今日代谢天气（Daily Metabolic Weather）

**系统每日自动生成**：

1. 今日高风险时段（按用户历史模式）
2. 今日建议餐窗与运动窗口
3. 今日优先目标（仅 1-2 条，避免干扰）

**体验价值**：用户感知“系统在替我安排，而非只展示历史图”。

## 2.4 功能 D：周目标代理（Weekly Goal Agent）

**系统每周自动生成**：

1. 上周问题模式（如：晚餐后高峰、夜间波动）
2. 下周个体化目标（可执行、可验证）
3. 目标完成进度 + 效果证据

**体验价值**：用户感知“系统懂我，并会持续学习我的反馈”。

## 2.5 功能 E：证据解释层（Explainability Layer）

每条建议必须附带“证据句”：

- 基于哪些数据窗口（例如最近 14 天）
- 触发该建议的核心指标是什么
- 该建议预期改变哪项指标

**体验价值**：提高信任，减少“AI 瞎猜”的感觉。

---

## 3. 分阶段计划（Plan）

## 3.1 Phase 1（1-2 周）：Agentic MVP

1. 接入吃前预演 + 吃后补救双核心功能
2. 提供每日代谢天气卡片
3. 形成建议日志与结果日志

**交付物**：可运行 Web Demo、最小闭环数据流、基础评估指标

## 3.2 Phase 2（3-4 周）：个体化强化

1. 按用户历史学习“时段风险”与“热量-响应斜率”
2. 引入周目标代理与周报
3. 加入建议效果自动复盘

**交付物**：用户级策略参数、周度目标闭环

## 3.3 Phase 3（5-8 周）：服务化与扩展

1. 多代理协作（数据质检代理、策略代理、教练代理、复盘代理）
2. 实时触发与优先级调度
3. A/B 验证建议策略

**交付物**：Agent Runtime、运营控制台、策略实验框架

---

## 4. 需要用到的数据（Data Requirements）

## 4.1 现有数据源（V0）

1. `data/glucose/*.csv`
2. `data/activity_food.csv`
3. `data/index.csv`
4. `data/index_corrected.csv`
5. `data/index_corrected_oncurve.csv`
6. `fatty_liver_data_raw/`（初始/监测/结束阶段体检文件）

## 4.2 数据职责分工

1. `glucose`：实时状态与餐后响应核心依据
2. `food/index`：行为输入与餐次锚点
3. `fatty_liver`：长期代谢背景与分层管理先验

---

## 5. 数据结构设计（Data Structures）

## 5.1 核心实体

### A. `UserProfile`

- `user_id` (SCxxx)
- `sex`
- `age`
- `height_cm`
- `weight_kg`
- `liver_risk_level`（由体检抽取得到）
- `consent_flags`

### B. `GlucosePoint`

- `user_id`
- `ts`
- `glucose_mmol_l`
- `source`
- `quality_flag`

### C. `MealEvent`

- `meal_id`
- `user_id`
- `meal_ts_raw`
- `meal_ts_corrected`
- `kcal`
- `confidence`
- `data_source`

### D. `LiverExamRecord`

- `exam_id`
- `user_id`（若无法直接映射，先存匿名 cohort_id）
- `stage`（initial / monitor / final）
- `exam_date`
- `indicators`（ALT、AST、TG、影像结论等）
- `risk_score`

### E. `AgentState`

- `user_id`
- `current_goal`
- `risk_windows_today`
- `active_plan`
- `last_replan_ts`
- `state_version`

### F. `AgentAction`

- `action_id`
- `user_id`
- `action_type`（pre_meal_sim / rescue / daily_plan / weekly_goal）
- `payload_version`（SemVer）
- `payload`
- `status`（valid / degraded / invalid）
- `priority`（low / medium / high）
- `reason_evidence`
- `error_code`（nullable）
- `trace_id`（nullable）
- `created_ts`

### G. `OutcomeFeedback`

- `action_id`
- `user_feedback`（执行/未执行/部分执行）
- `objective_outcome`（峰值变化、AUC变化）
- `closed_loop_score`

## 5.2 特征层（Feature Store）

### 短期特征（24h-7d）

- `tir_24h`, `tir_7d`
- `cv_24h`
- `last_meal_delta_peak`
- `rolling_auc_7d`
- `night_variability`

### 长期特征（28d+）

- `meal_time_sensitivity`（不同时段响应差异）
- `kcal_response_slope`（热量对峰值/AUC斜率）
- `adherence_rate`
- `liver_risk_trend`

---

## 6. 数据意义与作用（Why each data matters）

## 6.1 血糖时序数据的意义

1. 用于检测“现在是否正在恶化”
2. 用于评估“建议是否真正有效”
3. 是所有代理决策的实时主信号

## 6.2 饮食事件数据的意义

1. 定义干预起点（餐前/餐后）
2. 连接行为与结果（吃了什么 -> 曲线怎么变）
3. 形成个体化模式（哪个时段更敏感）

## 6.3 体检（脂肪肝）数据的意义

1. 提供长期风险背景（不是只看当下血糖）
2. 决定建议强度和优先级
3. 支持长期目标（肝脏负担趋势改善）

## 6.4 用户反馈数据的意义

1. 判断建议可执行性（技术正确不等于能执行）
2. 训练个体化策略（同一建议对不同人效果差异）
3. 形成真正闭环优化

---

## 7. Agent 工作流（服务视角）

1. Observe：读取最新 glucose/meal/exam/context
2. Understand：识别当前状态（稳定/上升/高风险窗口）
3. Plan：生成今天/本次事件最佳行动
4. Act：输出动作卡并触发提醒
5. Review：比较建议前后指标，写回学习参数

---

## 8. 成功判定标准（Success Criteria）

## 8.1 用户体验指标

1. 用户每日主动打开率
2. 建议点击率、执行率
3. 建议后复盘完成率

## 8.2 健康结果指标

1. 餐后峰值下降幅度
2. 餐后 AUC 下降幅度
3. 7d/28d TIR 提升

## 8.3 代理质量指标

1. 误报率（无效提醒）
2. 漏报率（应提醒未提醒）
3. 建议有效率（执行后指标改善）

---

## 9. 风险与约束

1. 不输出医疗诊断与处方建议
2. 对紧急症状必须走固定安全模板
3. 涉及个人敏感数据时，必须最小化上下文与可审计
4. 建议内容要“可执行、可验证、可回溯”

---

## 10. V0.1 Demo 交付建议

1. 主页：今日代谢天气 + 今日计划
2. 吃前页：输入餐次 -> 预演对比 + 替代建议
3. 吃后页：实时救援卡 + 倒计时复盘
4. 周报页：目标完成情况 + 指标变化证据
5. 证据页：每条建议的触发依据与数据窗口

> 这份蓝图的关键不是“多复杂模型”，而是把“观察-决策-行动-复盘”完整交付给用户，让用户实际感受到系统在主动服务。

---
