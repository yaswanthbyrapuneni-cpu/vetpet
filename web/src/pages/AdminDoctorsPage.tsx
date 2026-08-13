import { Award, Building2, CheckCircle2, ShieldCheck, XCircle } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import type { Doctor } from '../types'

export function AdminDoctorsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['admin-doctors'], queryFn: () => api.get<Doctor[]>('/admin/doctors') })
  const review = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'verified' | 'rejected' }) => api.post<Doctor>(`/admin/doctors/${id}/verification`, {
      decision,
      note: decision === 'verified' ? 'Credentials reviewed by administrator.' : 'Credentials could not be verified.',
    }),
    onSuccess: async () => Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-doctors'] }),
      queryClient.invalidateQueries({ queryKey: ['doctors'] }),
    ]),
  })
  const doctors = query.data ?? []
  const pending = doctors.filter((doctor) => doctor.verification_status === 'pending')
  const reviewed = doctors.filter((doctor) => doctor.verification_status !== 'pending')

  return <div className="page-content">
    <header className="page-heading"><div><span className="eyebrow">Administrator workspace</span><h1>Veterinarian verification</h1><p>Review professional accounts before they appear in public search.</p></div></header>
    {query.isLoading ? <LoadingBlock /> : query.isError ? <ErrorBlock message={query.error instanceof ApiError ? query.error.message : 'Unable to load veterinarians.'} retry={() => void query.refetch()} /> : <>
      {review.isError && <div className="inline-error" role="alert">{review.error instanceof ApiError ? review.error.message : 'Could not update verification.'}</div>}
      <section className="review-section"><div className="section-heading"><h2>Pending review <span className="count-badge">{pending.length}</span></h2></div>
        {pending.length === 0 ? <EmptyBlock title="No pending veterinarians" text="New veterinarian accounts will appear here for review." /> : <div className="review-list">{pending.map((doctor) => <DoctorReviewCard key={doctor.id} doctor={doctor} busy={review.isPending} onReview={(decision) => review.mutate({ id: doctor.id, decision })} />)}</div>}
      </section>
      {reviewed.length > 0 && <section className="review-section"><div className="section-heading"><h2>Previously reviewed</h2></div><div className="review-list">{reviewed.map((doctor) => <DoctorReviewCard key={doctor.id} doctor={doctor} busy={review.isPending} onReview={(decision) => review.mutate({ id: doctor.id, decision })} />)}</div></section>}
    </>}
  </div>
}

function DoctorReviewCard({ doctor, busy, onReview }: { doctor: Doctor; busy: boolean; onReview: (decision: 'verified' | 'rejected') => void }) {
  return <article className="review-card"><div className="doctor-avatar"><ShieldCheck /></div><div className="review-details">
    <div className="review-title"><div><h3>{doctor.user.full_name}</h3><p>{doctor.user.email}</p></div><span className={`status-badge ${doctor.verification_status}`}>{doctor.verification_status === 'verified' ? <Award size={14} /> : doctor.verification_status === 'rejected' ? <XCircle size={14} /> : null}{doctor.verification_status}</span></div>
    <dl><div><dt>Licence</dt><dd>{doctor.license_number}</dd></div><div><dt>Qualification</dt><dd>{doctor.qualification}</dd></div><div><dt>Specialization</dt><dd>{doctor.specialization || 'Not provided'}</dd></div>{doctor.hospital_name && <div><dt><Building2 size={14} /> Hospital</dt><dd>{doctor.hospital_name}</dd></div>}</dl>
    <div className="review-actions"><button className="button primary" disabled={busy || doctor.verification_status === 'verified'} onClick={() => onReview('verified')}><CheckCircle2 size={17} />Approve</button><button className="button secondary danger-button" disabled={busy || doctor.verification_status === 'rejected'} onClick={() => onReview('rejected')}><XCircle size={17} />Reject</button></div>
  </div></article>
}
