import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from './client'
import type {
  AgentAction,
  ChatResult,
  GlucoseImportResult,
  GlucosePoint,
  GlucoseRange,
  HealthDashboard,
  HealthReport,
  Meal,
  MealPhoto,
  PreMealSimPayload,
  ProactiveMessage,
  SampleFile,
  SubjectInfo,
  TodayBriefing,
  UploadTicket,
  UserMe,
  UserSettings,
  WeeklyReview,
} from './types'

export function useHealthDashboard() {
  return useQuery({
    queryKey: ['dashboard-health'],
    queryFn: () => api.get<HealthDashboard>('/api/dashboard/health'),
  })
}

export function useGlucoseRange() {
  return useQuery({
    queryKey: ['glucose-range'],
    queryFn: () => api.get<GlucoseRange>('/api/glucose/range'),
  })
}

export function useGlucosePoints(from: string | null, to: string | null) {
  return useQuery({
    queryKey: ['glucose-points', from, to],
    queryFn: () =>
      api.get<GlucosePoint[]>(
        `/api/glucose?from=${encodeURIComponent(from!)}&to=${encodeURIComponent(to!)}&limit=2000`,
      ),
    enabled: !!from && !!to,
  })
}

export function useMealPhotos() {
  return useQuery({
    queryKey: ['dashboard-meals'],
    queryFn: () => api.get<MealPhoto[]>('/api/dashboard/meals'),
  })
}

export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: () => api.get<UserMe>('/api/users/me'),
  })
}

export function useUpdateConsent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { allow_ai_chat?: boolean; allow_data_upload?: boolean }) =>
      api.patch('/api/users/consent', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useCreateMeal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      meal_ts: string
      meal_ts_source: string
      kcal: number
      tags: string[]
      photo_id?: string
      notes?: string
    }) => api.post<Meal>('/api/meals', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dashboard-health'] })
    },
  })
}

export function useCreateUploadTicket() {
  return useMutation({
    mutationFn: (payload: { filename: string; content_type: string }) =>
      api.post<UploadTicket>('/api/meals/photo/upload-url', payload),
  })
}

export function useCompletePhoto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { object_key: string; exif_ts?: string | null }) =>
      api.post<MealPhoto>('/api/meals/photo/complete', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dashboard-meals'] })
    },
  })
}

export function useAuth() {
  return {
    signup: (payload: { email: string; password: string }) =>
      api.post<{ access_token: string }>('/api/auth/signup', payload),
    login: (payload: { email: string; password: string }) =>
      api.post<{ access_token: string }>('/api/auth/login', payload),
  }
}

// ── Subject-based login ─────────────────────────────────────

export function useSubjects() {
  return useQuery({
    queryKey: ['subjects'],
    queryFn: () => api.get<SubjectInfo[]>('/api/auth/subjects'),
  })
}

export function useSubjectLogin() {
  return useMutation({
    mutationFn: (subjectId: string) =>
      api.post<{ access_token: string }>('/api/auth/login-subject', { subject_id: subjectId }),
  })
}

// ── Health Reports (Liver exam data) ────────────────────────

export function useHealthReports() {
  return useQuery({
    queryKey: ['health-reports'],
    queryFn: () => api.get<HealthReport>('/api/health-reports'),
  })
}

export function useChatOnce() {
  return useMutation({
    mutationFn: (message: string) => api.post<ChatResult>('/api/chat', { message }),
  })
}

export function useImportGlucose() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => api.postFile('/api/glucose/import', file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dashboard-health'] })
    },
  })
}

export function useGlucoseSamples() {
  return useQuery({
    queryKey: ['glucose-samples'],
    queryFn: () => api.get<SampleFile[]>('/api/glucose/samples'),
  })
}

export function useMealSamples() {
  return useQuery({
    queryKey: ['meal-samples'],
    queryFn: () => api.get<SampleFile[]>('/api/glucose/meal-samples'),
  })
}

export function useImportSampleGlucose() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (filename: string) =>
      api.post<GlucoseImportResult>(`/api/glucose/import-sample?filename=${encodeURIComponent(filename)}`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dashboard-health'] })
    },
  })
}

export function useRunBatchETL() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (opts?: { skip_glucose?: boolean; skip_meals?: boolean; skip_features?: boolean }) => {
      const params = new URLSearchParams()
      if (opts?.skip_glucose) params.set('skip_glucose', 'true')
      if (opts?.skip_meals) params.set('skip_meals', 'true')
      if (opts?.skip_features) params.set('skip_features', 'true')
      const qs = params.toString()
      return api.post<Record<string, unknown>>(`/api/etl/run-batch${qs ? `?${qs}` : ''}`, {})
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dashboard-health'] })
    },
  })
}

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get<UserSettings>('/api/users/settings'),
  })
}

export function useUpdateSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      intervention_level?: 'L1' | 'L2' | 'L3'
      daily_reminder_limit?: number | null
      allow_auto_escalation?: boolean
    }) => api.patch<UserSettings>('/api/users/settings', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings'] })
      qc.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

// ── Agent hooks ──────────────────────────────────────────

export function useProactiveMessage() {
  return useQuery({
    queryKey: ['proactive-message'],
    queryFn: () => api.get<ProactiveMessage>('/api/agent/proactive'),
    retry: false,
    refetchInterval: 60_000, // refresh every 60s for rescue detection
  })
}

export function useRescueCheck() {
  return useQuery({
    queryKey: ['rescue-check'],
    queryFn: () => api.get<Record<string, unknown>>('/api/agent/rescue'),
    retry: false,
    refetchInterval: 30_000, // poll every 30s
  })
}

export function useTodayBriefing() {
  return useQuery({
    queryKey: ['today-briefing'],
    queryFn: () => api.get<TodayBriefing>('/api/agent/today'),
    retry: false,
  })
}

export function useWeeklyReview() {
  return useQuery({
    queryKey: ['weekly-review'],
    queryFn: () => api.get<WeeklyReview>('/api/agent/weekly'),
    retry: false,
  })
}

export function useAgentActions(actionType?: string) {
  return useQuery({
    queryKey: ['agent-actions', actionType],
    queryFn: () =>
      api.get<AgentAction[]>(
        `/api/agent/actions${actionType ? `?action_type=${actionType}` : ''}`,
      ),
    retry: false,
  })
}

export function useRequestPreMealSim() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { kcal: number; meal_time: string }) =>
      api.post<PreMealSimPayload>('/api/agent/premeal-sim', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['today-briefing'] })
      qc.invalidateQueries({ queryKey: ['agent-actions'] })
    },
  })
}

export function useSubmitFeedback() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      action_id: string
      user_feedback: 'executed' | 'not_executed' | 'partial'
    }) => api.post('/api/agent/feedback', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['today-briefing'] })
      qc.invalidateQueries({ queryKey: ['agent-actions'] })
    },
  })
}
