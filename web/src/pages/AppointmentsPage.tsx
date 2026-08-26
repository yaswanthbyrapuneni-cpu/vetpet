import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { useState } from 'react'
import { api, ApiError } from '../api/client'
import { AppointmentCard } from '../components/AppointmentCard'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import type { Appointment } from '../types'

const ACTIVE_STATUSES = ['requested', 'confirmed'] as const
const HISTORY_STATUSES = ['completed', 'cancelled', 'rejected', 'no_show'] as const
const HISTORY_PAGE_SIZE = 10

function statusQuery(statuses: readonly string[], limit: number): string {
  return statuses.map((value) => `status_in=${value}`).join('&') + `&limit=${limit}`
}

function AppointmentSection({
  heading,
  query,
  data,
  emptyTitle,
  emptyText,
  onPaid,
  footer,
}: {
  heading: string
  query: UseQueryResult<Appointment[]>
  data: Appointment[]
  emptyTitle: string
  emptyText: string
  onPaid: () => void
  footer?: React.ReactNode
}) {
  return (
    <section className="appt-section">
      <h3 className="appt-section-heading">{heading}</h3>
      {query.isLoading ? (
        <LoadingBlock />
      ) : query.isError ? (
        <ErrorBlock
          message={query.error instanceof ApiError ? query.error.message : 'Unable to load appointments.'}
          retry={() => void query.refetch()}
        />
      ) : data.length === 0 ? (
        <EmptyBlock title={emptyTitle} text={emptyText} />
      ) : (
        <>
          <div className="appointment-list">
            {data.map((appointment) => (
              <AppointmentCard key={appointment.id} appointment={appointment} onPaid={onPaid} />
            ))}
          </div>
          {footer}
        </>
      )}
    </section>
  )
}

export function AppointmentsPage() {
  const { user } = useAuth()
  const { t } = useLanguage()
  const [historyLimit, setHistoryLimit] = useState(HISTORY_PAGE_SIZE)

  const active = useQuery({
    queryKey: ['appointments', 'active'],
    queryFn: () => api.get<Appointment[]>(`/appointments?${statusQuery(ACTIVE_STATUSES, 100)}`),
  })
  const history = useQuery({
    queryKey: ['appointments', 'history', historyLimit],
    queryFn: () => api.get<Appointment[]>(`/appointments?${statusQuery(HISTORY_STATUSES, historyLimit)}`),
  })

  const sortedActive = [...(active.data ?? [])].sort((a, b) => {
    if (a.status !== b.status) return a.status === 'confirmed' ? -1 : 1
    return new Date(b.scheduled_start).getTime() - new Date(a.scheduled_start).getTime()
  })

  return <div className="page-content">
    <header className="page-heading"><span className="eyebrow">{t('appt.eyebrow')}</span><h1>{t('appt.heading')}</h1><p>{user?.role === 'doctor' ? t('appt.doctorSubtitle') : t('appt.ownerSubtitle')}</p></header>

    <AppointmentSection
      heading={t('appt.sectionActive')}
      query={active}
      data={sortedActive}
      emptyTitle={t('appt.emptyTitle')}
      emptyText={user?.role === 'owner' ? t('appt.emptyOwnerText') : t('appt.emptyDoctorText')}
      onPaid={() => void active.refetch()}
    />

    <AppointmentSection
      heading={t('appt.sectionHistory')}
      query={history}
      data={history.data ?? []}
      emptyTitle={t('appt.sectionHistory')}
      emptyText={t('appt.noHistory')}
      onPaid={() => void history.refetch()}
      footer={
        (history.data?.length ?? 0) >= historyLimit && historyLimit < 100 ? (
          <button className="button secondary" style={{ marginTop: 14 }} onClick={() => setHistoryLimit((value) => Math.min(value + HISTORY_PAGE_SIZE, 100))}>
            {t('appt.loadMore')}
          </button>
        ) : undefined
      }
    />
  </div>
}
