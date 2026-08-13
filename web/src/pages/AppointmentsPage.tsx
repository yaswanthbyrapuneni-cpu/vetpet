import { CalendarDays, CheckCircle2, ClipboardPlus, Clock3, PhoneCall, Video, XCircle } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import { useAuth } from '../auth/AuthContext'
import type { Appointment } from '../types'

export function AppointmentsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['appointments'], queryFn: () => api.get<Appointment[]>('/appointments') })
  const decision = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'confirm' | 'reject' }) => api.post<Appointment>(`/appointments/${id}/${action}`, action === 'reject' ? { reason: 'The requested time is unavailable.' } : {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['appointments'] }),
  })
  return <div className="page-content"><header className="page-heading"><span className="eyebrow">Consultations</span><h1>Appointments</h1><p>{user?.role === 'doctor' ? 'Review requests and meet pet owners online.' : 'Track requests and join confirmed consultations.'}</p></header>
    {decision.isError && <div className="inline-error">{decision.error instanceof ApiError ? decision.error.message : 'Unable to update appointment.'}</div>}
    {query.isLoading ? <LoadingBlock /> : query.isError ? <ErrorBlock message={query.error instanceof ApiError ? query.error.message : 'Unable to load appointments.'} retry={() => void query.refetch()} /> : query.data?.length === 0 ? <EmptyBlock title="No appointments yet" text={user?.role === 'owner' ? 'Book a verified veterinarian to create your first appointment.' : 'New requests from pet owners will appear here.'} /> : <div className="appointment-list">{query.data?.map((appointment) => <article className="appointment-card" key={appointment.id}>
      <div className="appointment-icon">{appointment.consultation_type === 'video' ? <Video /> : <PhoneCall />}</div><div className="appointment-details"><div className="appointment-title"><h2>{appointment.consultation_type === 'video' ? 'Video consultation' : 'Audio consultation'}</h2><span className={`status-badge ${appointment.status === 'confirmed' ? 'verified' : appointment.status === 'rejected' || appointment.status === 'cancelled' ? 'rejected' : ''}`}>{appointment.status}</span></div><p>{appointment.reason}</p><div className="appointment-time"><CalendarDays size={15} />{new Date(appointment.scheduled_start).toLocaleDateString()}<Clock3 size={15} />{new Date(appointment.scheduled_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div></div>
      <div className="appointment-actions">{user?.role === 'doctor' && appointment.status === 'requested' && <><button className="button primary" disabled={decision.isPending} onClick={() => decision.mutate({ id: appointment.id, action: 'confirm' })}><CheckCircle2 size={17} />Confirm</button><button className="button secondary danger-button" disabled={decision.isPending} onClick={() => decision.mutate({ id: appointment.id, action: 'reject' })}><XCircle size={17} />Reject</button></>}{appointment.status === 'confirmed' && <Link className="button primary" to={`/app/call/${appointment.id}`}>{appointment.consultation_type === 'video' ? <Video size={17} /> : <PhoneCall size={17} />}Join call</Link>}{user?.role === 'doctor' && ['confirmed', 'completed'].includes(appointment.status) && <Link className="button secondary" to={`/app/appointments/${appointment.id}/care`}><ClipboardPlus size={17} />Notes &amp; medicines</Link>}</div>
    </article>)}</div>}
  </div>
}
