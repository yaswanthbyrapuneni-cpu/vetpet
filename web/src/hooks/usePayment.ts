import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import type { Appointment } from '../types'

interface RazorpayOrder {
  order_id: string
  amount_paise: number
  currency: string
  key_id: string
}

interface RazorpaySuccess {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open(): void }
  }
}

function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true)
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.onload = () => resolve(true)
    script.onerror = () => resolve(false)
    document.body.appendChild(script)
  })
}

export function usePayment(onPaid: (appointment: Appointment) => void) {
  const [paying, setPaying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  async function payNow(appointment: Appointment) {
    setPaying(true)
    setError(null)
    try {
      const scriptLoaded = await loadRazorpayScript()
      if (!scriptLoaded || !window.Razorpay) throw new Error('Unable to load the payment gateway.')
      const order = await api.post<RazorpayOrder>(`/appointments/${appointment.id}/payment/order`)
      const razorpay = new window.Razorpay({
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        order_id: order.order_id,
        name: 'Madina Vet Pet',
        description: 'Consultation fee',
        handler: async (response: RazorpaySuccess) => {
          try {
            await api.post(`/appointments/${appointment.id}/payment/verify`, response)
            onPaid(appointment)
          } catch (caught) {
            setError(caught instanceof ApiError ? caught.message : 'Payment verification failed.')
          }
        },
        modal: {
          // Booking creates the appointment before payment even opens — if the owner backs
          // out of the popup without paying, don't leave a permanent unpaid appointment behind.
          ondismiss: () => {
            void api
              .post(`/appointments/${appointment.id}/cancel`, { reason: 'Payment window closed before completing payment' })
              .then(() => queryClient.invalidateQueries({ queryKey: ['appointments'] }))
          },
        },
      })
      razorpay.open()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to start payment.')
    } finally {
      setPaying(false)
    }
  }

  return { paying, error, payNow }
}
