import { useMe, useUpdateConsent, useSettings, useUpdateSettings } from '../api/hooks'

const LEVEL_META: Record<string, { label: string; desc: string; color: string }> = {
  L1: { label: 'L1 温和', desc: '低打扰，适合新用户或不希望被频繁提醒的用户', color: 'border-emerald-300 bg-emerald-50' },
  L2: { label: 'L2 标准', desc: '平衡提醒频率与效果（默认）', color: 'border-primary/40 bg-teal-50' },
  L3: { label: 'L3 积极', desc: '高敏感触发，适合短期强化管理', color: 'border-orange-300 bg-orange-50' },
}

export function SettingsPage() {
  const { data, isLoading, error } = useMe()
  const updateConsent = useUpdateConsent()
  const { data: settings, isLoading: settingsLoading } = useSettings()
  const updateSettings = useUpdateSettings()

  if (isLoading || settingsLoading) {
    return <div className="rounded-xl bg-white p-4">加载中...</div>
  }

  if (error || !data) {
    return <div className="rounded-xl bg-red-50 p-4 text-red-600">加载设置失败</div>
  }

  const currentLevel = settings?.intervention_level ?? 'L2'
  const strategy = settings?.strategy

  return (
    <div className="grid gap-4">
      {/* --- 干预等级 --- */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        <h3 className="font-heading text-lg font-semibold">干预等级</h3>
        <p className="mt-1 text-sm text-slate-500">选择适合你的提醒强度，等级越高干预越积极</p>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {(['L1', 'L2', 'L3'] as const).map((lv) => {
            const meta = LEVEL_META[lv]
            const selected = currentLevel === lv
            return (
              <button
                key={lv}
                onClick={() => updateSettings.mutate({ intervention_level: lv })}
                disabled={updateSettings.isPending}
                className={`rounded-xl border-2 p-3 text-left transition-all
                  ${selected ? `${meta.color} ring-2 ring-primary/30` : 'border-slate-200 hover:border-slate-300'}
                  disabled:opacity-50`}
              >
                <div className="font-heading text-sm font-semibold">{meta.label}</div>
                <div className="mt-1 text-xs text-slate-600">{meta.desc}</div>
              </button>
            )
          })}
        </div>

        {/* Strategy details */}
        {strategy && (
          <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
            <div className="font-medium text-slate-700">当前策略参数</div>
            <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-1">
              <span>风险触发门槛</span><span className="font-medium">{strategy.trigger_min_risk} 以上</span>
              <span>每日提醒上限</span><span className="font-medium">{strategy.daily_reminder_limit} 次</span>
              <span>单餐最多提醒</span><span className="font-medium">{strategy.per_meal_reminder_limit} 次</span>
              <span>建议动作数</span><span className="font-medium">{strategy.suggestion_count_min}-{strategy.suggestion_count_max} 条</span>
              <span>复盘要求</span><span className="font-medium">{strategy.review_required === 'optional' ? '可选' : strategy.review_required === 'recommended' ? '建议' : '默认'}</span>
              <span>连续异常升级</span><span className="font-medium">{strategy.escalation_consecutive_days ? `${strategy.escalation_consecutive_days} 天` : '不自动升级'}</span>
            </div>
          </div>
        )}
      </div>

      {/* --- 提醒偏好 --- */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        <h3 className="font-heading text-lg font-semibold">提醒偏好</h3>

        <div className="mt-4 grid gap-3 text-sm">
          <label className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
            <div>
              <span>每日提醒上限</span>
              <span className="ml-2 text-xs text-slate-400">
                (等级上限: {strategy?.daily_reminder_limit ?? '-'} 次)
              </span>
            </div>
            <select
              value={settings?.daily_reminder_limit ?? strategy?.daily_reminder_limit ?? 2}
              onChange={(e) => updateSettings.mutate({ daily_reminder_limit: Number(e.target.value) })}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            >
              {Array.from({ length: (strategy?.daily_reminder_limit ?? 4) + 1 }, (_, i) => (
                <option key={i} value={i}>{i} 次</option>
              ))}
            </select>
          </label>

          <label className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
            <div>
              <span>允许连续异常时自动建议升级</span>
              <span className="ml-2 text-xs text-slate-400">
                {strategy?.escalation_consecutive_days
                  ? `连续 ${strategy.escalation_consecutive_days} 天异常时建议`
                  : '当前等级不支持'}
              </span>
            </div>
            <input
              type="checkbox"
              checked={settings?.allow_auto_escalation ?? false}
              onChange={(e) => updateSettings.mutate({ allow_auto_escalation: e.target.checked })}
              disabled={!strategy?.escalation_consecutive_days}
              className="h-4 w-4 rounded border-slate-300 text-primary disabled:opacity-40"
            />
          </label>
        </div>
      </div>

      {/* --- 账号与隐私 --- */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        <h3 className="font-heading text-lg font-semibold">账号与隐私</h3>
        <p className="mt-1 text-sm text-slate-500">邮箱：{data.email}</p>

        <div className="mt-4 grid gap-3 text-sm">
          <label className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
            <span>允许使用我的数据进行 AI 问答</span>
            <input
              type="checkbox"
              checked={data.consent.allow_ai_chat}
              onChange={(e) => updateConsent.mutate({ allow_ai_chat: e.target.checked })}
              className="h-4 w-4 rounded border-slate-300 text-primary"
            />
          </label>

          <label className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
            <span>允许上传健康相关文件</span>
            <input
              type="checkbox"
              checked={data.consent.allow_data_upload}
              onChange={(e) => updateConsent.mutate({ allow_data_upload: e.target.checked })}
              className="h-4 w-4 rounded border-slate-300 text-primary"
            />
          </label>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft text-sm text-slate-600">
        <div className="font-medium text-slate-900">LLM 调用与数据保留说明</div>
        <p className="mt-2">
          系统会记录模型供应商、模型名、延迟、上下文摘要哈希用于审计。你可随时关闭 AI 开关，关闭后 Chat API 返回 403。
        </p>
      </div>
    </div>
  )
}
