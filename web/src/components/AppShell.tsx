import { Bell, FileText, FileVideo, LayoutDashboard, LogOut, Menu, MessageCircle, PawPrint, Video, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthContext'
import { api } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { LanguageSwitcher } from './LanguageSwitcher'
import type { Notification } from '../types'

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const { t } = useLanguage()
  const [open, setOpen] = useState(false)
  // The realtime channel pushes a 'notification' event that invalidates this query instantly;
  // this interval is just a fallback in case a push is missed while the socket reconnects.
  const notifications = useQuery({ queryKey: ['notifications'], queryFn: () => api.get<Notification[]>('/notifications'), refetchInterval: 60000 })
  if (!user) return null
  const unreadCount = notifications.data?.filter((item) => !item.read_at).length ?? 0
  const links = [
    { to: '/app', key: 'overview', label: t('nav.overview'), icon: LayoutDashboard, end: true },
    ...(user.role !== 'admin' ? [{ to: '/app/appointments', key: 'appointments', label: t('nav.appointments'), icon: Video }] : []),
    ...(user.role !== 'admin' ? [{ to: '/app/messages', key: 'messages', label: t('nav.messages'), icon: MessageCircle }] : []),
    ...(user.role === 'doctor' ? [{ to: '/app/recordings', key: 'recordings', label: t('nav.recordings'), icon: FileVideo }] : []),
    ...(user.role !== 'admin' ? [{ to: '/app/notifications', key: 'notifications', label: t('nav.notifications'), icon: Bell }] : []),
  ]
  return (
    <div className="app-layout">
      <header className="mobile-header">
        <button className="icon-button" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu /></button>
        <span className="brand"><PawPrint /> {t('app.brand')}</span>
      </header>
      {open && <button className="sidebar-backdrop" onClick={() => setOpen(false)} aria-label="Close navigation" />}
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-brand"><PawPrint /><span>{t('app.brand')}</span><button className="close-nav" onClick={() => setOpen(false)}><X /></button></div>
        <nav>
          {links.map(({ to, key, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)}><Icon size={19} />{label}{key === 'notifications' && unreadCount > 0 && <small className="notification-count">{unreadCount > 99 ? '99+' : unreadCount}</small>}</NavLink>
          ))}
          {user.role !== 'admin' && unreadCount > 0 && <span className="sr-only" aria-live="polite">You have {unreadCount} unread notifications</span>}
        </nav>
        <LanguageSwitcher className="sidebar-language" />
        <div className="account-card">
          <span className="avatar">{user.full_name.charAt(0).toUpperCase()}</span>
          <div><strong>{user.full_name}</strong><small>{user.role}</small></div>
          <button className="icon-button" onClick={logout} title={t('nav.signOut')}><LogOut size={18} /></button>
        </div>
      </aside>
      <main className="app-main">{children}</main>
      {user.role === 'owner' && (
        <nav className="bnav">
          <NavLink to="/app" end><LayoutDashboard />{t('nav.overview')}</NavLink>
          <NavLink to="/app/messages"><MessageCircle />{t('nav.messages')}</NavLink>
          <NavLink to="/app/records"><FileText />{t('nav.records')}</NavLink>
          <NavLink to="/app/notifications"><Bell />{t('nav.notifications')}</NavLink>
        </nav>
      )}
    </div>
  )
}
