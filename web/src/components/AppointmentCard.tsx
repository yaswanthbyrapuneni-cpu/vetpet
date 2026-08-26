import { CalendarDays, CheckCircle2, ClipboardPlus, Clock3, FileText, MessageCircle, MoreVertical, PhoneCall, Receipt, Video, X } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useSpeciesLabel } from '../hooks/useSpeciesLabel'
import { useLanguage } from '../i18n/LanguageContext'
import { PaymentButton } from './PaymentButton'
import type { Appointment } from '../types'

export function AppointmentCard({ appointment, onPaid }: { appointment: Appointment; onPaid: () => void }) {
  const { user } = useAuth()
  const { t } = useLanguage()
  const speciesLabel = useSpeciesLabel()
  const queryClient = useQueryClient()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // A tap on iOS Safari doesn't reliably focus a <button>, so a menu that only
  // opens via CSS :hover/:focus-within can silently fail to open on iPhones.
  // Track open/close explicitly instead, with an outside-click/tap to close.
  useEffect(() => {
    if (!menuOpen) return
    function onOutside(event: MouseEvent | TouchEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onOutside)
    document.addEventListener('touchstart', onOutside)
    return () => {
      document.removeEventListener('mousedown', onOutside)
      document.removeEventListener('touchstart', onOutside)
    }
  }, [menuOpen])
  const awaitingPayment = appointment.payment_status !== 'paid'
  // Pay/cancel only make sense while the appointment is still actually pending action.
  // An unpaid appointment that's already cancelled/rejected/no-show is a finished record,
  // not something still waiting on the owner — re-offering those buttons on it is what
  // caused "Appointment cannot be cancelled" when tapped.
  const canActOnPayment = awaitingPayment && appointment.status === 'requested'
  const title = user?.role === 'doctor'
    ? `${appointment.owner_name} — ${speciesLabel(appointment.species)} visit`
    : `${speciesLabel(appointment.species)} visit`

  const complete = useMutation({
    mutationFn: () => api.post<Appointment>(`/appointments/${appointment.id}/complete`),
    onSuccess: () => {
      setMenuOpen(false)
      void queryClient.invalidateQueries({ queryKey: ['appointments'] })
      void queryClient.invalidateQueries({ queryKey: ['appointment', appointment.id] })
    },
  })
  const cancel = useMutation({
    mutationFn: () => api.post(`/appointments/${appointment.id}/cancel`, { reason: 'Cancelled by owner' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['appointments'] })
      void queryClient.invalidateQueries({ queryKey: ['appointment', appointment.id] })
    },
  })

  return (
    <article className={`appointment-card ${awaitingPayment ? 'muted-card' : ''}`}>
      <div className="appointment-icon">{appointment.consultation_type === 'video' ? <Video /> : <PhoneCall />}</div>
      <div className="appointment-details">
        <div className="appointment-title">
          <h2>{title}</h2>
          <span className={`status-badge ${appointment.status === 'confirmed' ? 'verified' : appointment.status === 'rejected' || appointment.status === 'cancelled' ? 'rejected' : ''}`}>
            {canActOnPayment ? t('appt.paymentPending') : appointment.status}
          </span>
        </div>
        {user?.role === 'doctor' && <p>{appointment.owner_mobile_number}</p>}
        <div className="appointment-time">
          <CalendarDays size={15} />{new Date(appointment.scheduled_start).toLocaleDateString()}
          <Clock3 size={15} />{new Date(appointment.scheduled_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
        {!awaitingPayment && <p className="payment-line">₹{(appointment.payment_amount_paise / 100).toFixed(0)} · {t('appt.paid')}</p>}
        {complete.isError && <div className="inline-error">{complete.error instanceof ApiError ? complete.error.message : 'Unable to complete this visit.'}</div>}
        {cancel.isError && <div className="inline-error">{cancel.error instanceof ApiError ? cancel.error.message : 'Unable to cancel this booking.'}</div>}
      </div>
      <div className="appointment-actions">
        {canActOnPayment ? (
          user?.role === 'owner'
            ? <>
                <PaymentButton appointment={appointment} onPaid={onPaid} />
                <button type="button" className="button secondary" disabled={cancel.isPending} onClick={() => cancel.mutate()}>
                  <X size={17} />{cancel.isPending ? t('dashboard.cancelling') : t('dashboard.cancelBooking')}
                </button>
              </>
            : <span className="muted" style={{ fontSize: '.85rem' }}>{t('appt.waitingForPayment')}</span>
        ) : awaitingPayment ? null : (
          <>
            <Link className="button primary" to={`/app/messages/${appointment.id}`}><MessageCircle size={17} />{t('nav.messages')}</Link>
            {user?.role === 'doctor' && ['confirmed', 'completed'].includes(appointment.status) && (
              <Link className="button secondary" to={`/app/appointments/${appointment.id}/care`}><ClipboardPlus size={17} />{t('appt.notesMedicines')}</Link>
            )}
            {user?.role === 'owner' && ['confirmed', 'completed'].includes(appointment.status) && (
              <Link className="button secondary" to={`/app/appointments/${appointment.id}/consultation`}><FileText size={17} />{t('appt.consultationMedia')}</Link>
            )}
            <div className="menu-wrap" ref={menuRef}>
              <button
                type="button"
                className="icon-button"
                title="More actions"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((open) => !open)}
              >
                <MoreVertical size={18} />
              </button>
              <div className={`card-menu ${menuOpen ? 'open' : ''}`} role="menu">
                {user?.role === 'doctor' && appointment.status === 'confirmed' && (
                  <button type="button" disabled={complete.isPending} onClick={() => complete.mutate()}>
                    <CheckCircle2 />{complete.isPending ? t('appt.completing') : t('appt.completeVisit')}
                  </button>
                )}
                <Link to={`/app/appointments/${appointment.id}/payment`} onClick={() => setMenuOpen(false)}>
                  <Receipt />{t('appt.paymentDetails')}
                </Link>
              </div>
            </div>
          </>
        )}
      </div>
    </article>
  )
}
