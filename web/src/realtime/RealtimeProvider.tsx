import { Phone, PhoneOff, Video } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthContext'
import { api, tokenStore } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { RING_TIMEOUT_MS } from './constants'

type RealtimeEvent =
  | { type: 'connected' }
  | { type: 'chat_message'; appointment_id: string }
  | { type: 'chat_attachment'; appointment_id: string }
  | { type: 'call_invite'; appointment_id: string; doctor_name: string; consultation_type: 'video' | 'audio' }
  | { type: 'call_declined'; appointment_id: string }
  | { type: 'call_cancelled'; appointment_id: string }
  | { type: 'notification' }
  | { type: 'appointment_cancelled'; appointment_id: string }
  | { type: 'appointment_completed'; appointment_id: string }

interface IncomingCall {
  appointmentId: string
  doctorName: string
  consultationType: 'video' | 'audio'
}

const RECONNECT_DELAY_MS = 3000

/** Dispatched on window so any mounted page (chiefly CallPage) can react without a shared context. */
function dispatchCallStatus(detail: { type: 'call_declined' | 'call_cancelled'; appointment_id: string }) {
  window.dispatchEvent(new CustomEvent('realtime:call-status', { detail }))
}

function useRingtone(active: boolean) {
  useEffect(() => {
    if (!active) return
    const ctx = new AudioContext()

    function ring() {
      const now = ctx.currentTime
      for (const start of [0, 0.35]) {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.frequency.value = 950
        gain.gain.setValueAtTime(0.0001, now + start)
        gain.gain.exponentialRampToValueAtTime(0.25, now + start + 0.02)
        gain.gain.exponentialRampToValueAtTime(0.0001, now + start + 0.3)
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.start(now + start)
        osc.stop(now + start + 0.32)
      }
    }

    ring()
    const interval = setInterval(ring, 2000)
    return () => {
      clearInterval(interval)
      void ctx.close()
    }
  }, [active])
}

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const { t } = useLanguage()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const socketRef = useRef<WebSocket | null>(null)
  const ringTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [incomingCall, setIncomingCall] = useState<IncomingCall | null>(null)

  useRingtone(Boolean(incomingCall))

  const clearIncoming = useCallback((appointmentId?: string) => {
    setIncomingCall((current) => (appointmentId && current?.appointmentId !== appointmentId ? current : null))
    if (ringTimeout.current) clearTimeout(ringTimeout.current)
  }, [])

  useEffect(() => {
    if (!user) return
    let cancelled = false
    let reconnectTimer: ReturnType<typeof setTimeout>

    function connect() {
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const socket = new WebSocket(`${protocol}//${location.host}/api/v1/ws/events`)
      socketRef.current = socket

      socket.onopen = () => socket.send(JSON.stringify({ type: 'auth', token: tokenStore.get() }))

      socket.onmessage = (event) => {
        let payload: RealtimeEvent
        try {
          payload = JSON.parse(event.data)
        } catch {
          return
        }
        if (payload.type === 'chat_message') {
          void queryClient.invalidateQueries({ queryKey: ['messages', payload.appointment_id] })
          void queryClient.invalidateQueries({ queryKey: ['message-threads'] })
        } else if (payload.type === 'chat_attachment') {
          void queryClient.invalidateQueries({ queryKey: ['attachments', payload.appointment_id] })
          void queryClient.invalidateQueries({ queryKey: ['message-threads'] })
        } else if (payload.type === 'call_invite') {
          setIncomingCall({
            appointmentId: payload.appointment_id,
            doctorName: payload.doctor_name,
            consultationType: payload.consultation_type,
          })
          if (ringTimeout.current) clearTimeout(ringTimeout.current)
          ringTimeout.current = setTimeout(() => clearIncoming(payload.appointment_id), RING_TIMEOUT_MS)
        } else if (payload.type === 'call_cancelled') {
          clearIncoming(payload.appointment_id)
          dispatchCallStatus(payload)
        } else if (payload.type === 'call_declined') {
          dispatchCallStatus(payload)
        } else if (payload.type === 'notification') {
          void queryClient.invalidateQueries({ queryKey: ['notifications'] })
        } else if (payload.type === 'appointment_cancelled' || payload.type === 'appointment_completed') {
          void queryClient.invalidateQueries({ queryKey: ['appointments'] })
          void queryClient.invalidateQueries({ queryKey: ['appointment', payload.appointment_id] })
          void queryClient.invalidateQueries({ queryKey: ['message-threads'] })
        }
      }

      socket.onclose = () => {
        if (!cancelled) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    connect()

    return () => {
      cancelled = true
      clearTimeout(reconnectTimer)
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [user, queryClient, clearIncoming])

  function acceptCall() {
    if (!incomingCall) return
    const appointmentId = incomingCall.appointmentId
    clearIncoming()
    navigate(`/app/call/${appointmentId}?autojoin=1`)
  }

  function declineCall() {
    if (!incomingCall) return
    void api.post(`/appointments/${incomingCall.appointmentId}/call/decline`)
    clearIncoming()
  }

  return (
    <>
      {children}
      {incomingCall && (
        <div className="incoming-call-overlay">
          <div className="incoming-call-card">
            <div className="incoming-call-avatar">
              {incomingCall.consultationType === 'video' ? <Video size={30} /> : <Phone size={30} />}
            </div>
            <h2>{incomingCall.doctorName}</h2>
            <p>{incomingCall.consultationType === 'video' ? t('call.incomingVideo') : t('call.incomingAudio')}</p>
            <div className="incoming-call-actions">
              <button className="incoming-call-btn decline" onClick={declineCall} title={t('call.decline')}><PhoneOff /></button>
              <button className="incoming-call-btn accept" onClick={acceptCall} title={t('call.accept')}><Phone /></button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
