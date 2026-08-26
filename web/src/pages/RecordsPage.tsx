import { FileText } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import { useSpeciesLabel } from '../hooks/useSpeciesLabel'
import { useLanguage } from '../i18n/LanguageContext'
import type { Appointment, Pet } from '../types'

export function RecordsPage() {
  const { t } = useLanguage()
  const speciesLabel = useSpeciesLabel()
  const appointments = useQuery({ queryKey: ['appointments'], queryFn: () => api.get<Appointment[]>('/appointments') })
  const pets = useQuery({ queryKey: ['pets'], queryFn: () => api.get<Pet[]>('/pets') })
  const completed = appointments.data?.filter((item) => item.status === 'completed') ?? []

  return (
    <div className="page-content">
      <header className="page-heading"><span className="eyebrow">{t('records.eyebrow')}</span><h1>{t('records.heading')}</h1><p>{t('records.subtitle')}</p></header>
      {(appointments.isLoading || pets.isLoading) ? <LoadingBlock /> : appointments.isError ? (
        <ErrorBlock message={appointments.error instanceof ApiError ? appointments.error.message : 'Unable to load records.'} retry={() => void appointments.refetch()} />
      ) : completed.length === 0 ? (
        <EmptyBlock title={t('records.emptyTitle')} text={t('records.emptyText')} />
      ) : (
        <div className="pet-grid">
          {completed.map((appointment) => {
            const pet = pets.data?.find((item) => item.id === appointment.pet_id)
            return (
              <Link className="rx" to={`/app/appointments/${appointment.id}/consultation`} key={appointment.id} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="rx-head">
                  <div className="t">{pet ? speciesLabel(pet.species) : t('records.heading')}</div>
                  <div className="m">{new Date(appointment.scheduled_start).toLocaleDateString()}</div>
                </div>
                <div className="rx-body">
                  <div className="kv"><span>{t('records.reason')}</span><b>{appointment.reason}</b></div>
                  <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 6, color: 'var(--primary)', fontWeight: 700, fontSize: '.85rem' }}><FileText size={15} />{t('records.view')}</div>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
