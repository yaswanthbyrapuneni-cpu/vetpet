import { Bell, CalendarCheck, Check, CheckCheck, Pill, Sparkles } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import type { Notification } from '../types'

const icons = { appointment: CalendarCheck, prescription: Pill, reminder: Bell, system: Sparkles }

export function NotificationsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: ['notifications'],
    queryFn: () => api.get<Notification[]>('/notifications'),
    refetchInterval: 15000,
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

  return <div className="page-content">
    <header className="page-heading split"><div><span className="eyebrow">Updates</span><h1>Notifications</h1><p>Appointment, prescription, and care reminders for your account.</p></div>{unread > 0 && <button className="button secondary" disabled={readAll.isPending} onClick={() => readAll.mutate()}><CheckCheck size={18} />Mark all read</button>}</header>
    {query.isLoading ? <LoadingBlock /> : query.isError ? <ErrorBlock message={query.error instanceof ApiError ? query.error.message : 'Unable to load notifications.'} retry={() => void query.refetch()} /> : notifications.length === 0 ? <EmptyBlock title="You're all caught up" text="New appointment and care updates will appear here." /> : <div className="notification-list">{notifications.map((item) => {
      const Icon = icons[item.notification_type] ?? Bell
      return <article className={`notification-card ${item.read_at ? '' : 'unread'}`} key={item.id}><div className={`notification-icon ${item.notification_type}`}><Icon /></div><div><div className="notification-title"><h2>{item.title}</h2>{!item.read_at && <span>New</span>}</div><p>{item.message}</p><time>{new Date(item.created_at).toLocaleString()}</time></div>{!item.read_at && <button className="icon-button mark-read" disabled={read.isPending} onClick={() => read.mutate(item.id)} title="Mark as read"><Check /></button>}</article>
    })}</div>}
  </div>
}
