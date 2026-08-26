import { Star } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, ApiError } from '../api/client'
import { useLanguage, type TranslationKey } from '../i18n/LanguageContext'
import type { AppointmentRating } from '../types'

// Stored values are stable identifiers, independent of the i18n key used to display them —
// renaming a translation key must never change what's persisted in past ratings.
const RATING_TAGS: { value: string; labelKey: TranslationKey }[] = [
  { value: 'clear_explanation', labelKey: 'rating.tagClear' },
  { value: 'on_time', labelKey: 'rating.tagOnTime' },
  { value: 'caring', labelKey: 'rating.tagCaring' },
  { value: 'prescription_helped', labelKey: 'rating.tagHelped' },
]

export function RatingPrompt({ appointmentId }: { appointmentId: string }) {
  const { t } = useLanguage()
  const queryClient = useQueryClient()
  const existing = useQuery({
    queryKey: ['rating', appointmentId],
    queryFn: () => api.getOptional<AppointmentRating>(`/appointments/${appointmentId}/rating`),
  })
  const [stars, setStars] = useState(5)
  const [tags, setTags] = useState<string[]>([])
  const [comment, setComment] = useState('')
  const submit = useMutation({
    mutationFn: () => api.post(`/appointments/${appointmentId}/rating`, { stars, tags, comment: comment || null }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['rating', appointmentId] }),
  })

  function toggleTag(value: string) {
    setTags((prev) => (prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value]))
  }

  if (existing.isLoading) return null
  if (existing.data) {
    return (
      <section className="clinical-panel">
        <div className="panel-title"><Star /><div><h2>{t('rating.heading')}</h2></div></div>
        <div className="stars">{[1, 2, 3, 4, 5].map((value) => <span key={value} className={value <= existing.data!.stars ? 'on' : ''} style={{ color: value <= existing.data!.stars ? '#E8A93B' : '#D8E2E0' }}>★</span>)}</div>
        {existing.data.comment && <p className="muted">{existing.data.comment}</p>}
      </section>
    )
  }

  return (
    <section className="clinical-panel">
      <div className="panel-title"><Star /><div><h2>{t('rating.heading')}</h2><p>{t('rating.subtitle')}</p></div></div>
      <div className="stars">
        {[1, 2, 3, 4, 5].map((value) => (
          <button type="button" key={value} className={value <= stars ? 'on' : ''} onClick={() => setStars(value)} aria-label={`${value} star`}>★</button>
        ))}
      </div>
      <div className="chipset" style={{ margin: '10px 0' }}>
        {RATING_TAGS.map(({ value, labelKey }) => (
          <button type="button" key={value} className={`tag-toggle ${tags.includes(value) ? 'on' : ''}`} onClick={() => toggleTag(value)}>{t(labelKey)}</button>
        ))}
      </div>
      <input value={comment} onChange={(event) => setComment(event.target.value)} placeholder={t('rating.commentPlaceholder')} maxLength={1000} />
      {submit.isError && <div className="inline-error">{submit.error instanceof ApiError ? submit.error.message : 'Unable to submit rating.'}</div>}
      <button className="button primary" style={{ marginTop: 12 }} disabled={submit.isPending} onClick={() => submit.mutate()}>{submit.isPending ? t('rating.submitting') : t('rating.submit')}</button>
    </section>
  )
}
