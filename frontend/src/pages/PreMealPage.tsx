import { useState } from 'react'

import { useRequestPreMealSim } from '../api/hooks'
import type { PreMealSimPayload } from '../api/types'
import { PreMealSimulatorCard } from '../components/agent/PreMealSimulatorCard'

export function PreMealPage() {
  const mutation = useRequestPreMealSim()
  const [result, setResult] = useState<PreMealSimPayload | null>(null)

  function handleSimulate(input: { kcal: number; meal_time: string }) {
    mutation.mutate(input, {
      onSuccess: (data) => setResult(data),
    })
  }

  return (
    <div className="grid gap-4">
      <PreMealSimulatorCard
        onSimulate={handleSimulate}
        isPending={mutation.isPending}
        result={result}
      />

      {mutation.isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          预演失败 — {(mutation.error as Error)?.message ?? '请检查网络或稍后重试'}
        </div>
      )}
    </div>
  )
}
