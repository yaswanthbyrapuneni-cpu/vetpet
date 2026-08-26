import { ArrowLeft, FileDown, Lock, MessageCircle, Stethoscope } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { ErrorBlock, LoadingBlock } from '../components/Feedback'
import { PaymentButton } from '../components/PaymentButton'
import { RatingPrompt } from '../components/RatingPrompt'
import { useLanguage } from '../i18n/LanguageContext'
import type { Appointment } from '../types'

interface Consultation {
  id: string
  diagnosis: string | null
  approved_summary: string | null
  follow_up_date: string | null
}

export function ConsultationPage() {
  const { t } = useLanguage()
  const { appointmentId = '' } = useParams()
  const appointment = useQuery({
    queryKey: ['appointment', appointmentId],
    queryFn: () => api.get<Appointment>(`/appointments/${appointmentId}`),
  })
  const consultation = useQuery({
    queryKey: ['consultation', appointmentId],
    queryFn: () => api.getOptional<Consultation>(`/appointments/${appointmentId}/consultation`),
    enabled: appointment.data?.payment_status === 'paid',
  })
  const [downloading, setDownloading] = useState(false)

  async function downloadPrescription() {
    if (!consultation.data) return
    setDownloading(true)
    try {
      const blob = await api.blob(`/consultations/${consultation.data.id}/prescription.pdf`)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank', 'noopener,noreferrer')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } finally {
      setDownloading(false)
    }
  }

  if (appointment.isLoading) return <div className="page-content"><LoadingBlock /></div>
  if (appointment.isError || !appointment.data) {
    return <div className="page-content"><ErrorBlock message={appointment.error instanceof ApiError ? appointment.error.message : 'Unable to load appointment.'} /></div>
  }

  const paid = appointment.data.payment_status === 'paid'

  return (
    <div className="page-content">
      <Link className="back-link" to="/app/appointments"><ArrowLeft size={18} />{t('appt.heading')}</Link>
      <header className="page-heading clinical-heading">
        <span className="eyebrow">{t('consult.eyebrow')}</span>
        <h1>{t('consult.heading')}</h1>
      </header>

      {!paid ? (
        <div className="lock">
          <div className="li"><Lock size={30} /></div>
          <h3>{t('lock.title')}</h3>
          <div className="cm">{t('lock.body')}</div>
          <div style={{ marginTop: 14 }}>
            <PaymentButton appointment={appointment.data} onPaid={() => void appointment.refetch()} />
          </div>
        </div>
      ) : <>
        <div className="trust">
          <Lock size={16} />
          <div>{t('lock.unlocked')}</div>
        </div>
        {consultation.data ? (
          <section className="clinical-panel">
            <div className="panel-title"><Stethoscope /><div><h2>{t('consult.careSummary')}</h2></div></div>
            <p>{consultation.data.approved_summary || consultation.data.diagnosis || t('consult.noSummary')}</p>
            {consultation.data.follow_up_date && <p>{t('consult.followUp', { date: new Date(consultation.data.follow_up_date).toLocaleDateString() })}</p>}
            <button type="button" className="button secondary" disabled={downloading} onClick={() => void downloadPrescription()}>
              <FileDown size={16} />{downloading ? t('consult.opening') : t('consult.downloadPdf')}
            </button>
          </section>
        ) : (
          <div className="info-banner">{t('consult.noNotesYet')}</div>
        )}
        <Link className="button primary" to={`/app/messages/${appointmentId}`}>
          <MessageCircle size={17} />{t('chat.heading')}
        </Link>
        {appointment.data.status === 'completed' && <RatingPrompt appointmentId={appointmentId} />}
      </>}
    </div>
  )
}
