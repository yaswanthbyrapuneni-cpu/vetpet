import { CalendarPlus, Clock3, Trash2 } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { api, ApiError } from '../api/client'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import type { Availability } from '../types'

export function AvailabilityPage() {
  const queryClient = useQueryClient()
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const query = useQuery({ queryKey: ['my-availability'], queryFn: () => api.get<Availability[]>('/doctors/me/availability') })
  const create = useMutation({ mutationFn: () => api.post('/doctors/me/availability', { starts_at: new Date(start).toISOString(), ends_at: new Date(end).toISOString() }), onSuccess: async () => { setStart(''); setEnd(''); await queryClient.invalidateQueries({ queryKey: ['my-availability'] }) } })
  const remove = useMutation({ mutationFn: (id: string) => api.delete(`/doctors/me/availability/${id}`), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['my-availability'] }) })
  function submit(event: FormEvent) { event.preventDefault(); create.mutate() }
  const error = create.error ?? remove.error
  return <div className="page-content"><header className="page-heading"><span className="eyebrow">Schedule</span><h1>Appointment availability</h1><p>Add times when owners can request a consultation with you.</p></header>
    <form className="availability-form" onSubmit={submit}><CalendarPlus /><label>Starts at<input type="datetime-local" value={start} min={new Date().toISOString().slice(0, 16)} onChange={(event) => setStart(event.target.value)} required /></label><label>Ends at<input type="datetime-local" value={end} min={start} onChange={(event) => setEnd(event.target.value)} required /></label><button className="button primary" disabled={create.isPending || !start || !end}>Add time</button></form>
    {error && <div className="inline-error">{error instanceof ApiError ? error.message : 'Unable to update availability.'}</div>}
    <section className="review-section"><div className="section-heading"><h2>Your appointment times</h2></div>{query.isLoading ? <LoadingBlock /> : query.isError ? <ErrorBlock message="Unable to load availability." retry={() => void query.refetch()} /> : query.data?.length === 0 ? <EmptyBlock title="No appointment times" text="Add your first available time above so owners can book you." /> : <div className="availability-list">{query.data?.map((slot) => <article key={slot.id}><Clock3 /><div><strong>{new Date(slot.starts_at).toLocaleString()}</strong><small>Until {new Date(slot.ends_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small></div><span className={`status-badge ${slot.is_booked ? 'verified' : ''}`}>{slot.is_booked ? 'Booked' : 'Open'}</span><button className="icon-button" disabled={slot.is_booked || remove.isPending} onClick={() => remove.mutate(slot.id)} title="Delete time"><Trash2 size={17} /></button></article>)}</div>}</section>
  </div>
}
