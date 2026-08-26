import { ArrowLeft, Receipt } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { ErrorBlock, LoadingBlock } from '../components/Feedback'
import { useAuth } from '../auth/AuthContext'
import { useSpeciesLabel } from '../hooks/useSpeciesLabel'
import type { Appointment } from '../types'

export function PaymentDetailsPage() {
  const { user } = useAuth()
  const speciesLabel = useSpeciesLabel()
  const { appointmentId = '' } = useParams()
  const appointment = useQuery({
    queryKey: ['appointment', appointmentId],
    queryFn: () => api.get<Appointment>(`/appointments/${appointmentId}`),
  })

  if (appointment.isLoading) return <div className="page-content"><LoadingBlock /></div>
  if (appointment.isError || !appointment.data) {
    return <div className="page-content"><ErrorBlock message={appointment.error instanceof ApiError ? appointment.error.message : 'Unable to load payment details.'} /></div>
  }

  const data = appointment.data
  const paid = data.payment_status === 'paid'
  const statusLabel = paid ? 'Paid' : data.payment_status === 'failed' ? 'Payment failed' : 'Payment pending'

  return (
    <div className="page-content">
      <Link className="back-link" to={`/app/messages/${appointmentId}`}><ArrowLeft size={18} />Back</Link>
      <header className="page-heading"><span className="eyebrow">Payment</span><h1>Payment details</h1></header>
      <section className="clinical-panel">
        <div className="panel-title">
          <Receipt />
          <div>
            <h2>{speciesLabel(data.species)} visit{user?.role === 'doctor' ? ` — ${data.owner_name}` : ''}</h2>
            <p>{statusLabel}</p>
          </div>
        </div>
        <dl className="receipt-details">
          <div><dt>Amount</dt><dd>₹{(data.payment_amount_paise / 100).toFixed(2)}</dd></div>
          <div><dt>Status</dt><dd><span className={`status-badge ${paid ? 'verified' : data.payment_status === 'failed' ? 'rejected' : ''}`}>{data.payment_status}</span></dd></div>
          {data.paid_at && <div><dt>Paid on</dt><dd>{new Date(data.paid_at).toLocaleString()}</dd></div>}
          {data.razorpay_payment_id && <div><dt>Reference</dt><dd>{data.razorpay_payment_id}</dd></div>}
          <div><dt>Appointment date</dt><dd>{new Date(data.scheduled_start).toLocaleString()}</dd></div>
        </dl>
      </section>
    </div>
  )
}
