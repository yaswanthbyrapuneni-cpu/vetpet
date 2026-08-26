import { Bell, CalendarCheck, Check, CheckCheck, Pill, Sparkles } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import { useLanguage } from '../i18n/LanguageContext'
import type { Notification } from '../types'

const icons = { appointment: CalendarCheck, prescription: Pill, reminder: Bell, system: Sparkles }

function notificationTarget(notification: Notification): string | null {
  const appointmentId = notification.data.appointment_id
  if (typeof appointmentId !== 'string') return notification.notification_type === 'reminder' ? '/app/records' : null
  if (notification.notification_type === 'prescription') return `/app/appointments/${appointmentId}/consultation`
  if (notification.notification_type === 'appointment') {
    // "Consultation completed" is where the owner rates the visit — send them there, not to the chat.
    if (notification.title === 'Consultation completed') return `/app/appointments/${appointmentId}/consultation`
    return `/app/messages/${appointmentId}`
  }
  return null
}

export function NotificationsPage() {
  const { t } = useLanguage()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: ['notifications'],
    queryFn: () => api.get<Notification[]>('/notifications'),
    refetchInterval: 60000,
  })
  const read = useMutation({
    mutationFn: (id: string) => api.post(`/notifications/${id}/read`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })
  const readAll = useMutation({
    mutationFn: () => api.post('/notifications/read-all'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })
  const notifications = query.data ?? []
  const unread = notifications.filter((item) => !item.read_at).length

  function openNotification(item: Notification) {
    if (!item.read_at) read.mutate(item.id)
    const target = notificationTarget(item)
    if (target) navigate(target)
  }

  return <div className="page-content">
    <header className="page-heading split"><div><span className="eyebrow">{t('notif.eyebrow')}</span><h1>{t('notif.heading')}</h1><p>{t('notif.subtitle')}</p></div>{unread > 0 && <button className="button secondary" disabled={readAll.isPending} onClick={() => readAll.mutate()}><CheckCheck size={18} />{t('notif.markAllRead')}</button>}</header>
    {query.isLoading ? <LoadingBlock /> : query.isError ? <ErrorBlock message={query.error instanceof ApiError ? query.error.message : 'Unable to load notifications.'} retry={() => void query.refetch()} /> : notifications.length === 0 ? <EmptyBlock title={t('notif.emptyTitle')} text={t('notif.emptyText')} /> : <div className="notification-list">{notifications.map((item) => {
      const Icon = icons[item.notification_type] ?? Bell
      const clickable = Boolean(notificationTarget(item))
      return <article className={`notification-card ${item.read_at ? '' : 'unread'} ${clickable ? 'clickable' : ''}`} key={item.id} onClick={() => openNotification(item)} role={clickable ? 'button' : undefined} tabIndex={clickable ? 0 : undefined}><div className={`notification-icon ${item.notification_type}`}><Icon /></div><div><div className="notification-title"><h2>{item.title}</h2>{!item.read_at && <span>{t('notif.new')}</span>}</div><p>{item.message}</p><time>{new Date(item.created_at).toLocaleString()}</time></div>{!item.read_at && <button className="icon-button mark-read" disabled={read.isPending} onClick={(event) => { event.stopPropagation(); read.mutate(item.id) }} title={t('notif.markRead')}><Check /></button>}</article>
    })}</div>}
  </div>
}
