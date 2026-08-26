import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Capacitor } from '@capacitor/core'
import { App as CapacitorApp } from '@capacitor/app'
import { Browser } from '@capacitor/browser'
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

interface PaymentLinkResponse {
  payment_link_url: string
}

const NATIVE_CALLBACK_PREFIX = 'madinavetpet://payment-complete'

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

  // Razorpay's checkout runs redirect-heavy payment methods (netbanking,
  // UPI, wallets) that need a real browser — our own app's embedded WebView
  // handles third-party cookies and window.open() hand-offs unreliably even
  // though the identical flow works fine in any normal browser. A system
  // browser tab (Chrome Custom Tabs) sidesteps that entirely; a deep link
  // (registered in AndroidManifest.xml) hands control back to the app once
  // payment finishes.
  async function payWithSystemBrowser(appointment: Appointment) {
    const link = await api.post<PaymentLinkResponse>(
      `/appointments/${appointment.id}/payment/link`,
    )

    let settled = false

    const urlListener = await CapacitorApp.addListener('appUrlOpen', (event) => {
      if (settled || !event.url.startsWith(NATIVE_CALLBACK_PREFIX)) return
      const status = new URL(event.url).searchParams.get('status')
      void cleanup().then(async () => {
        await Browser.close().catch(() => undefined)
        setPaying(false)
        if (status === 'success') {
          onPaid(appointment)
        } else {
          setError('Payment could not be completed. Please try again.')
        }
      })
    })

    const finishedListener = await Browser.addListener('browserFinished', () => {
      if (settled) return
      // The tab was closed by the user without ever reaching the success
      // deep link — same "don't leave a stuck unpaid booking behind" rule
      // as the web checkout's modal-dismiss handler.
      void cleanup().then(() => {
        setPaying(false)
        void api
          .post(`/appointments/${appointment.id}/cancel`, {
            reason: 'Payment window closed before completing payment',
          })
          .then(() => queryClient.invalidateQueries({ queryKey: ['appointments'] }))
          .catch(() => undefined)
      })
    })

    async function cleanup() {
      if (settled) return
      settled = true
      await Promise.all([urlListener.remove(), finishedListener.remove()])
    }

    await Browser.open({ url: link.payment_link_url })
  }

  async function payWithEmbeddedCheckout(appointment: Appointment) {
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
  }

  async function payNow(appointment: Appointment) {
    setPaying(true)
    setError(null)
    const native = Capacitor.isNativePlatform()
    try {
      if (native) {
        await payWithSystemBrowser(appointment)
      } else {
        await payWithEmbeddedCheckout(appointment)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to start payment.')
      setPaying(false)
      return
    }
    // The native path resolves as soon as the system browser opens, well
    // before the user has actually paid — `paying` gets cleared later, from
    // inside the appUrlOpen/browserFinished handlers above, once there's a
    // real outcome to react to.
    if (!native) setPaying(false)
  }

  return { paying, error, payNow }
}
