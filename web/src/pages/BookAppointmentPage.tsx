import { ArrowLeft, CalendarDays, CheckCircle2, Clock3, Stethoscope } from 'lucide-react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { ErrorBlock, LoadingBlock } from '../components/Feedback'
import type { Appointment, Availability, Doctor, Pet } from '../types'

export function BookAppointmentPage() {
  const { doctorId = '' } = useParams()
  const doctor = useQuery({ queryKey: ['doctor', doctorId], queryFn: () => api.get<Doctor>(`/doctors/${doctorId}`), enabled: Boolean(doctorId) })
  const slots = useQuery({ queryKey: ['doctor-slots', doctorId], queryFn: () => api.get<Availability[]>(`/doctors/${doctorId}/availability`), enabled: Boolean(doctorId) })
  const pets = useQuery({ queryKey: ['pets'], queryFn: () => api.get<Pet[]>('/pets') })
  const [slotId, setSlotId] = useState('')
  const [petId, setPetId] = useState('')
  const [reason, setReason] = useState('')
  const [consultationType, setConsultationType] = useState<'video' | 'audio'>('video')
  const [booked, setBooked] = useState<Appointment | null>(null)
  const booking = useMutation({ mutationFn: () => api.post<Appointment>('/appointments', { pet_id: petId, availability_id: slotId, reason, consultation_type: consultationType }), onSuccess: setBooked })

  function submit(event: FormEvent) { event.preventDefault(); booking.mutate() }
  if (doctor.isLoading || slots.isLoading || pets.isLoading) return <div className="page-content"><LoadingBlock /></div>
  if (doctor.isError) return <div className="page-content"><ErrorBlock message={doctor.error instanceof ApiError ? doctor.error.message : 'Unable to load veterinarian.'} /></div>
  if (!doctor.data) return null

  return <div className="page-content booking-page"><Link className="back-link" to="/app/doctors"><ArrowLeft size={18} />Back to veterinarians</Link>
    <header className="booking-doctor"><div className="doctor-avatar"><Stethoscope /></div><div><span className="verified-badge">Verified veterinarian</span><h1>{doctor.data.user.full_name}</h1><p>{doctor.data.specialization || 'General veterinary medicine'} · {doctor.data.qualification}</p></div></header>
    {booked ? <section className="booking-success"><CheckCircle2 /><h2>Appointment requested</h2><p>Your request for {new Date(booked.scheduled_start).toLocaleString()} was sent to the veterinarian.</p><Link className="button primary" to="/app">Return to overview</Link></section> : <form className="booking-card" onSubmit={submit}><div><span className="eyebrow">Book consultation</span><h2>Choose an available time</h2></div>
      {(slots.data?.length ?? 0) === 0 ? <div className="info-banner">This veterinarian has not added any available appointment times yet. Please check again later.</div> : <div className="slot-grid">{slots.data?.map((slot) => <label className={`slot-option ${slotId === slot.id ? 'selected' : ''}`} key={slot.id}><input type="radio" name="slot" value={slot.id} checked={slotId === slot.id} onChange={() => setSlotId(slot.id)} required /><CalendarDays /><span><strong>{new Date(slot.starts_at).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</strong><small><Clock3 size={13} />{new Date(slot.starts_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}–{new Date(slot.ends_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small></span></label>)}</div>}
      <div className="form-grid"><label>Select pet<select value={petId} onChange={(event) => setPetId(event.target.value)} required><option value="">Choose your pet</option>{pets.data?.map((pet) => <option value={pet.id} key={pet.id}>{pet.name} ({pet.species})</option>)}</select></label><label>Consultation type<select value={consultationType} onChange={(event) => setConsultationType(event.target.value as 'video' | 'audio')}><option value="video">Video call</option><option value="audio">Audio call</option></select></label><label className="span-two">Reason for appointment<textarea value={reason} onChange={(event) => setReason(event.target.value)} required minLength={3} maxLength={2000} placeholder="Describe your pet's symptoms or concern" /></label></div>
      {pets.data?.length === 0 && <div className="info-banner">Add a pet profile before booking. <Link to="/app/pets">Add a pet</Link></div>}{booking.isError && <div className="inline-error">{booking.error instanceof ApiError ? booking.error.message : 'Unable to book appointment.'}</div>}<button className="button primary" disabled={booking.isPending || !slotId || !petId}>{booking.isPending ? 'Sending request…' : 'Request appointment'}</button>
    </form>}
  </div>
}
