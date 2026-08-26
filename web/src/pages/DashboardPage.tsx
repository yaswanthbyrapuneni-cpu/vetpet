import { Bell, ChevronRight, Circle, CreditCard, FileText, PawPrint, Pill, ShieldAlert, Truck } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { AppointmentCard } from '../components/AppointmentCard'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import { useAuth } from '../auth/AuthContext'
import { usePayment } from '../hooks/usePayment'
import { usePricing } from '../hooks/usePricing'
import { useSpeciesLabel } from '../hooks/useSpeciesLabel'
import { useLanguage } from '../i18n/LanguageContext'
import { SPECIES_GROUPS, speciesEmoji, speciesLabel } from '../species'
import { speakTelugu } from '../voice'
import type { Appointment, Doctor, PetSpecies } from '../types'

type DateFilter = 'today' | 'week' | 'month'

function withinRange(scheduledStart: string, filter: DateFilter): boolean {
  const date = new Date(scheduledStart)
  const now = new Date()
  if (filter === 'today') return date.toDateString() === now.toDateString()
  if (filter === 'week') {
    const weekAgo = new Date(now)
    weekAgo.setDate(now.getDate() - 7)
    return date >= weekAgo && date <= now
  }
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth()
}

export function DashboardPage() {
  const { user } = useAuth()
  const { t, language } = useLanguage()
  const { feeRupees } = usePricing()
  const speciesDisplay = useSpeciesLabel()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [dateFilter, setDateFilter] = useState<DateFilter>('today')
  const appointments = useQuery({
    queryKey: ['appointments'],
    queryFn: () => api.get<Appointment[]>('/appointments'),
    enabled: user?.role === 'owner',
  })
  const primaryDoctor = useQuery({
    queryKey: ['doctor', 'primary'],
    queryFn: () => api.get<Doctor>('/doctors/primary'),
    enabled: user?.role === 'owner',
  })
  const ownProfile = useQuery({
    queryKey: ['doctor', 'me'],
    queryFn: () => api.get<Doctor>('/doctors/me'),
    enabled: user?.role === 'doctor',
  })
  const doctorAppointments = useQuery({
    queryKey: ['appointments', 'dashboard'],
    queryFn: () => api.get<Appointment[]>('/appointments?limit=100'),
    enabled: user?.role === 'doctor',
  })
  const toggleStatus = useMutation({
    mutationFn: (isOnline: boolean) => api.patch<Doctor>('/doctors/me/status', { is_online: isOnline }),
    onSuccess: (doctor) => queryClient.setQueryData(['doctor', 'me'], doctor),
  })
  // Tapping a species tile books and pays in one motion — no separate confirmation
  // screen, since there's only ever one doctor to confirm.
  const { paying, error: payError, payNow } = usePayment((appointment) => {
    if (language === 'te') speakTelugu(t('voice.paidTe'), t('voice.paidEn'))
    navigate(`/app/messages/${appointment.id}`)
  })
  const booking = useMutation({
    mutationFn: (species: PetSpecies) => api.post<Appointment>('/appointments', { pet_name: speciesLabel(species), species }),
  })
  async function bookAndPay(species: PetSpecies) {
    const appointment = await booking.mutateAsync(species)
    if (language === 'te') speakTelugu(t('voice.bookedTe'), t('voice.bookedEn'))
    await payNow(appointment)
  }
  const cancelUpcoming = useMutation({
    mutationFn: (id: string) => api.post(`/appointments/${id}/cancel`, { reason: 'Cancelled from dashboard' }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['appointments'] }),
  })
  if (!user) return null
  const firstName = user.full_name.split(' ')[0]
  const upcoming = appointments.data
    ?.filter((item) => item.status === 'requested' || item.status === 'confirmed')
    .sort((a, b) => new Date(a.scheduled_start).getTime() - new Date(b.scheduled_start).getTime())[0]
  const filteredPatients = (doctorAppointments.data ?? [])
    .filter((item) => withinRange(item.scheduled_start, dateFilter))
    .sort((a, b) => new Date(b.scheduled_start).getTime() - new Date(a.scheduled_start).getTime())

  return (
    <div className="page-content">
      <header className="page-heading"><div><span className="eyebrow">{t('dashboard.eyebrow')}</span><h1>{t('dashboard.greeting', { name: firstName })}</h1><p>{user.role === 'owner' ? t('dashboard.ownerSubtitle') : t('dashboard.doctorSubtitle')}</p></div></header>
      {user.role === 'owner' ? <>
        {upcoming && (
          <div className="card" style={{ borderLeft: '4px solid var(--primary)', marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
              <div>
                <h3>{t('dashboard.upcomingTitle')}</h3>
                <div className="cm">{new Date(upcoming.scheduled_start).toLocaleString()} · {speciesDisplay(upcoming.species)}</div>
              </div>
              <span className={`badge ${upcoming.payment_status === 'paid' ? 'teal' : 'warn'}`}>{upcoming.payment_status === 'paid' ? t('dashboard.paid') : t('dashboard.paymentPending')}</span>
            </div>
            {cancelUpcoming.isError && <div className="inline-error" style={{ marginTop: 10 }}>{cancelUpcoming.error instanceof ApiError ? cancelUpcoming.error.message : 'Unable to cancel.'}</div>}
            <div style={{ display: 'flex', gap: 10, marginTop: 12, flexWrap: 'wrap' }}>
              <Link className="button light" to={`/app/appointments/${upcoming.id}/consultation`}>
                {upcoming.payment_status === 'paid' ? t('dashboard.openConsult') : t('dashboard.completePayment')}
              </Link>
              {upcoming.payment_status !== 'paid' && (
                <button type="button" className="button secondary" disabled={cancelUpcoming.isPending} onClick={() => cancelUpcoming.mutate(upcoming.id)}>
                  {cancelUpcoming.isPending ? t('dashboard.cancelling') : t('dashboard.cancelBooking')}
                </button>
              )}
            </div>
          </div>
        )}

        {primaryDoctor.data && (
          <div className={`doctor-status-banner ${primaryDoctor.data.is_online ? 'online' : 'offline'}`}>
            <Circle size={9} />
            {primaryDoctor.data.is_online ? t('dashboard.doctorAvailable', { name: primaryDoctor.data.user.full_name }) : t('dashboard.doctorBusy', { name: primaryDoctor.data.user.full_name })}
          </div>
        )}

        <label className="label" style={{ display: 'block', margin: '0 0 10px', fontWeight: 700 }}>{t('dashboard.chooseAnimal')}</label>
        {(booking.isError || payError) && <div className="inline-error" style={{ marginBottom: 10 }}>{booking.error instanceof ApiError ? booking.error.message : payError ?? 'Unable to start payment.'}</div>}
        <div className="catgrid" style={{ marginBottom: 8 }}>
          {SPECIES_GROUPS.map((group) => (
            <div className={`catcard ${group.length > 1 ? 'multi' : ''}`} key={group.join('-')}>
              <div className="catcard-options">
                {group.map((species) => (
                  <button type="button" className="catcard-option" disabled={booking.isPending || paying} onClick={() => void bookAndPay(species)} key={species}>
                    <div className="em">{speciesEmoji(species)}</div>
                    <div className="nm">{speciesDisplay(species)}</div>
                  </button>
                ))}
              </div>
              <span className="fee">{booking.isPending || paying ? <CreditCard size={14} /> : `₹${feeRupees(group[0])}`}</span>
            </div>
          ))}
        </div>
        <p className="hint" style={{ margin: '0 0 22px', color: 'var(--muted)', fontSize: '.82rem' }}>{t('dashboard.payFirstHint')}</p>

        <label className="label" style={{ display: 'block', margin: '0 0 10px', fontWeight: 700 }}>{t('dashboard.moreServices')}</label>
        <div className="catgrid" style={{ marginBottom: 24 }}>
          <div className="catcard disabled"><Truck size={26} /><div className="nm">{t('dashboard.homeVisit')}</div><span className="soon">{t('dashboard.comingSoon')}</span></div>
          <div className="catcard disabled"><PawPrint size={26} /><div className="nm">{t('dashboard.petCare')}</div><span className="soon">{t('dashboard.comingSoon')}</span></div>
          <div className="catcard disabled"><ShieldAlert size={26} /><div className="nm">{t('dashboard.emergency')}</div><span className="soon">{t('dashboard.comingSoon')}</span></div>
          <div className="catcard disabled"><Pill size={26} /><div className="nm">{t('dashboard.pharmacy')}</div><span className="soon">{t('dashboard.comingSoon')}</span></div>
        </div>

        <section className="hero-card"><div><span className="hero-kicker">{t('dashboard.eyebrow')}</span><h2>{t('dashboard.heroTitle')}</h2><p>{t('dashboard.heroText')}</p><Link to="/app/records" className="button light"><FileText size={18} />{t('dashboard.managePets')} <ChevronRight size={18} /></Link></div><PawPrint className="hero-mark" /></section>
        <section className="empty-panel"><Bell /><div><h3>{t('dashboard.noReminders')}</h3><p>{t('dashboard.noRemindersText')}</p></div></section>
      </> : <>
        {ownProfile.data && (
          <div className="card status-toggle-card">
            <div>
              <h3>{t('dashboard.statusToggleTitle')}</h3>
              <p className="cm">{ownProfile.data.is_online ? t('dashboard.statusToggleOnlineText') : t('dashboard.statusToggleOfflineText')}</p>
              {toggleStatus.isError && <div className="inline-error">{toggleStatus.error instanceof ApiError ? toggleStatus.error.message : 'Unable to update status.'}</div>}
            </div>
            <button
              type="button"
              className={`status-switch ${ownProfile.data.is_online ? 'on' : ''}`}
              role="switch"
              aria-checked={ownProfile.data.is_online}
              disabled={toggleStatus.isPending}
              onClick={() => toggleStatus.mutate(!ownProfile.data!.is_online)}
            >
              <span className="knob" />
            </button>
          </div>
        )}

        <div className="filter-pills">
          <button type="button" className={`pill ${dateFilter === 'today' ? 'active' : ''}`} onClick={() => setDateFilter('today')}>{t('dashboard.filterToday')}</button>
          <button type="button" className={`pill ${dateFilter === 'week' ? 'active' : ''}`} onClick={() => setDateFilter('week')}>{t('dashboard.filterWeek')}</button>
          <button type="button" className={`pill ${dateFilter === 'month' ? 'active' : ''}`} onClick={() => setDateFilter('month')}>{t('dashboard.filterMonth')}</button>
        </div>

        {doctorAppointments.isLoading ? (
          <LoadingBlock />
        ) : doctorAppointments.isError ? (
          <ErrorBlock
            message={doctorAppointments.error instanceof ApiError ? doctorAppointments.error.message : 'Unable to load patients.'}
            retry={() => void doctorAppointments.refetch()}
          />
        ) : filteredPatients.length === 0 ? (
          <EmptyBlock title={t('dashboard.noPatients')} text={t('dashboard.noPatientsText')} />
        ) : (
          <div className="appointment-list">
            {filteredPatients.map((appointment) => (
              <AppointmentCard key={appointment.id} appointment={appointment} onPaid={() => void doctorAppointments.refetch()} />
            ))}
          </div>
        )}
      </>}
    </div>
  )
}
