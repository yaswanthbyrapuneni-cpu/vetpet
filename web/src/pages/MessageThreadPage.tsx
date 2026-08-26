import { ArrowLeft, ClipboardPlus, FileText, Phone, Video } from 'lucide-react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { AppointmentThread } from '../components/AppointmentThread'
import { ErrorBlock, LoadingBlock } from '../components/Feedback'
import { useAuth } from '../auth/AuthContext'
import { useSpeciesLabel } from '../hooks/useSpeciesLabel'
import { useLanguage } from '../i18n/LanguageContext'
import type { AppointmentThreadSummary } from '../types'

export function MessageThreadPage() {
  const { user } = useAuth()
  const { t } = useLanguage()
  const speciesLabel = useSpeciesLabel()
  const navigate = useNavigate()
  const { appointmentId = '' } = useParams()
  const threads = useQuery({
    queryKey: ['message-threads'],
    queryFn: () => api.get<AppointmentThreadSummary[]>('/messages/threads'),
  })
  const thread = threads.data?.find((item) => item.appointment_id === appointmentId)
  const startCall = useMutation({
    mutationFn: () => api.post(`/appointments/${appointmentId}/call/invite`),
    onSuccess: () => navigate(`/app/call/${appointmentId}?autojoin=1`),
  })

  if (threads.isLoading) return <div className="page-content"><LoadingBlock /></div>
  if (threads.isError) {
    return (
      <div className="page-content">
        <ErrorBlock message={threads.error instanceof ApiError ? threads.error.message : 'Unable to load this conversation.'} />
      </div>
    )
  }

  const title = thread ? (user?.role === 'doctor' ? `${thread.owner_name} — ${speciesLabel(thread.species)} visit` : `${speciesLabel(thread.species)} visit`) : ''
  const canCall = thread?.status === 'confirmed'
  const CallIcon = thread?.consultation_type === 'audio' ? Phone : Video

  return (
    <div className="page-content">
      <Link className="back-link" to="/app/messages"><ArrowLeft size={18} />{t('messages.backToMessages')}</Link>
      <header className="page-heading split" style={{ marginTop: 14 }}>
        <div><span className="eyebrow">{t('messages.eyebrow')}</span><h1>{title}</h1></div>
        <div style={{ display: 'flex', gap: 8 }}>
          {user?.role === 'doctor' ? (
            <button
              type="button"
              className="icon-button thread-call-btn"
              disabled={!canCall || startCall.isPending}
              onClick={() => startCall.mutate()}
              title={canCall ? 'Start call' : 'Available once the appointment is confirmed'}
            >
              <CallIcon />
            </button>
          ) : (
            <button type="button" className="icon-button thread-call-btn" disabled title="Only the veterinarian can start a call">
              <CallIcon />
            </button>
          )}
          {user?.role === 'doctor' ? (
            <Link className="button secondary" to={`/app/appointments/${appointmentId}/care`}>
              <ClipboardPlus size={17} />{t('messages.openNotes')}
            </Link>
          ) : (
            <Link className="button secondary" to={`/app/appointments/${appointmentId}/consultation`}>
              <FileText size={17} />{t('messages.openConsultation')}
            </Link>
          )}
        </div>
      </header>
      {startCall.isError && <div className="inline-error">{startCall.error instanceof ApiError ? startCall.error.message : 'Unable to start the call.'}</div>}
      <AppointmentThread appointmentId={appointmentId} />
    </div>
  )
}
