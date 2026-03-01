// ── Subject login ───────────────────────────────────────────

export type SubjectInfo = {
  subject_id: string
  cohort: 'cgm' | 'liver'
  has_meals: boolean
  has_glucose: boolean
  display_name: string | null
}

// ── Glucose ─────────────────────────────────────────────────

export type GlucoseSummary = {
  window: string
  avg: number | null
  min: number | null
  max: number | null
  tir_70_180_pct: number | null
  variability: 'low' | 'medium' | 'high' | 'unknown' | string
  gaps_hours: number
}

export type GlucosePoint = {
  id: string
  ts: string
  glucose_mgdl: number
  source: string
}

export type GlucoseRange = {
  min_ts: string | null
  max_ts: string | null
  count: number
}

export type HealthDashboard = {
  glucose: {
    last_24h: GlucoseSummary
    last_7d: GlucoseSummary
  }
  kcal_today: number
  meals_today: Array<{
    id: string
    ts: string
    kcal: number
    tags: string[]
    source: string
  }>
  data_quality: {
    glucose_gaps_hours: number
    variability: string
  }
}

export type UploadTicket = {
  upload_url: string
  object_key: string
  expires_in: number
}

export type MealPhoto = {
  id: string
  uploaded_at: string
  status: 'uploaded' | 'processed' | 'failed' | string
  calorie_estimate_kcal: number | null
  confidence: number | null
  vision_json: Record<string, unknown>
  suggested_meal_ts?: string | null
  suggested_confidence?: number | null
}

export type Meal = {
  id: string
  meal_ts: string
  meal_ts_source: string
  kcal: number
  tags: string[]
  notes?: string | null
  photo_id?: string | null
}

export type UserMe = {
  id: string
  email: string
  created_at: string
  consent: {
    allow_ai_chat: boolean
    allow_data_upload: boolean
    version: string
    updated_at: string
  }
  settings?: UserSettings | null
}

export type UserSettings = {
  intervention_level: 'L1' | 'L2' | 'L3'
  daily_reminder_limit: number | null
  allow_auto_escalation: boolean
  updated_at?: string | null
  strategy?: InterventionStrategy | null
}

export type InterventionStrategy = {
  trigger_min_risk: string
  daily_reminder_limit: number
  per_meal_reminder_limit: number
  suggestion_count_min: number
  suggestion_count_max: number
  review_required: string
  escalation_consecutive_days: number | null
}

export type ChatResult = {
  answer_markdown: string
  confidence: number
  followups: string[]
  safety_flags: string[]
  used_context: Record<string, unknown>
}

/** 样本文件 */
export type SampleFile = {
  filename: string
  subject_id?: string
  size_kb: number
}

export type GlucoseImportResult = {
  inserted: number
  skipped: number
  errors: Array<{ row: number | null; reason: string }>
}

// ── AgentAction 判别联合类型 ─────────────────────────────

export type ActionStatus = 'valid' | 'invalid' | 'degraded'

/** 所有 action 共享的头部字段 */
type AgentActionBase = {
  id: string
  user_id: string
  action_type: string
  payload_version: string
  status: ActionStatus
  priority?: string | null
  reason_evidence: {
    window?: string
    signals?: string[]
    summary?: string
  }
  error_code?: string | null
  trace_id?: string | null
  created_ts: string
}

// ── per‑action payload types ────────────────────────────

export type PreMealSimPayload = {
  title: string
  meal_input: { kcal: number; meal_time: string }
  prediction: {
    peak_glucose: number
    time_to_peak_min: number
    auc_0_120: number
    liver_load_score?: number
  }
  alternatives: Array<{
    id: string
    label: string
    expected_delta_peak: number
  }>
}

export type RescuePayload = {
  title: string
  risk_level: string
  trigger_evidence: string[]
  steps: Array<{ id: string; label: string; duration_min?: number }>
  expected_effect: { delta_peak_low: number; delta_peak_high: number }
  followup?: { checkpoints_min: number[] }
  expires_at?: string
}

export type DailyPlanPayload = {
  title: string
  risk_windows: Array<{ start: string; end: string; risk: string }>
  today_goals: string[]
}

export type WeeklyGoalPayload = {
  title: string
  focus: string
  target: {
    metric: string
    baseline: number
    goal: number
    unit: string
    window_days: number
  }
  tasks: string[]
}

// ── 判别联合 ────────────────────────────────────────────

export type PreMealSimAction = AgentActionBase & {
  action_type: 'pre_meal_sim'
  payload: PreMealSimPayload
}

export type RescueAction = AgentActionBase & {
  action_type: 'rescue'
  payload: RescuePayload
}

export type DailyPlanAction = AgentActionBase & {
  action_type: 'daily_plan'
  payload: DailyPlanPayload
}

export type WeeklyGoalAction = AgentActionBase & {
  action_type: 'weekly_goal'
  payload: WeeklyGoalPayload
}

export type AgentAction =
  | PreMealSimAction
  | RescueAction
  | DailyPlanAction
  | WeeklyGoalAction

/** 今日简报 */
export type TodayBriefing = {
  daily_plan: DailyPlanAction | null
  pending_rescues: RescueAction[]
  recent_actions: AgentAction[]
  glucose_status: {
    current_mgdl: number | null
    trend: 'rising' | 'falling' | 'stable' | 'unknown'
    tir_24h: number | null
  }
}

/** 周复盘 */
export type WeeklyReview = {
  goal: WeeklyGoalAction | null
  progress: {
    metric: string
    baseline: number
    current: number
    goal: number
    unit: string
    completion_pct: number
  } | null
  highlights: string[]
  next_focus: string | null
}

// ── Proactive Dog Message ────────────────────────────────────

export type ProactiveMessage = {
  message: string
  cards: Array<Record<string, unknown>>
  has_rescue: boolean
}

// ── Health Reports (Liver exam data) ────────────────────────

export type LabItem = {
  name: string
  value: string | null
  unit: string | null
  reference: string | null
  abnormal: string | null
  order_name: string | null
  audit_date: string | null
}

export type ExamPhase = {
  phase: '初始' | '结束'
  label: string
  dates: string[]
  items: LabItem[]
}

export type HealthReport = {
  subject_id: string
  cohort: string
  patient: { name?: string; age?: string; sex?: string }
  phases: ExamPhase[]
}
