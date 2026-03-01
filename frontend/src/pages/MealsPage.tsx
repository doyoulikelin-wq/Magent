import { useState } from 'react'

import { useCreateMeal, useMealPhotos } from '../api/hooks'
import type { MealPhoto } from '../api/types'
import { MealTimeConfirmModal } from '../components/meals/MealTimeConfirmModal'
import { MealsTable } from '../components/meals/MealsTable'
import { MealUploadCard } from '../components/meals/MealUploadCard'

export function MealsPage() {
  const { data = [], isLoading } = useMealPhotos()
  const createMeal = useCreateMeal()
  const [currentPhoto, setCurrentPhoto] = useState<MealPhoto | null>(null)

  return (
    <div className="grid gap-4">
      <MealUploadCard
        onCompleted={(photo) => {
          setCurrentPhoto(photo)
        }}
      />

      {isLoading ? <div className="rounded-xl bg-white p-4">加载餐图记录...</div> : <MealsTable photos={data} />}

      <MealTimeConfirmModal
        photo={currentPhoto}
        onClose={() => setCurrentPhoto(null)}
        onConfirm={async (payload) => {
          if (!currentPhoto) {
            return
          }
          await createMeal.mutateAsync({
            ...payload,
            photo_id: currentPhoto.id,
          })
          setCurrentPhoto(null)
        }}
      />
    </div>
  )
}
