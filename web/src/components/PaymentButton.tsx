import { CreditCard } from 'lucide-react'
import { usePayment } from '../hooks/usePayment'
import { useLanguage } from '../i18n/LanguageContext'
import type { Appointment } from '../types'

export function PaymentButton({ appointment, onPaid }: { appointment: Appointment; onPaid: () => void }) {
  const { t } = useLanguage()
  const { paying, error, payNow } = usePayment(onPaid)

  return (
    <div className="booking-payment">
      <p>{t('book.feeLabel')} <strong>₹{(appointment.payment_amount_paise / 100).toFixed(2)}</strong></p>
      {error && <div className="inline-error">{error}</div>}
      <button className="button primary" onClick={() => void payNow(appointment)} disabled={paying}>
        <CreditCard size={16} />{paying ? t('book.opening') : t('book.payNow')}
      </button>
    </div>
  )
}
