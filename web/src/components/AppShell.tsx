import { Bell, CalendarDays, FileVideo, LayoutDashboard, LogOut, Menu, PawPrint, ShieldCheck, Stethoscope, Video, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../auth/AuthContext'
import { api } from '../api/client'
import type { Notification } from '../types'

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const notifications = useQuery({ queryKey: ['notifications'], queryFn: () => api.get<Notification[]>('/notifications'), refetchInterval: 15000 })
  if (!user) return null
  const unreadCount = notifications.data?.filter((item) => !item.read_at).length ?? 0
  const links = [
    { to: '/app', label: 'Overview', icon: LayoutDashboard, end: true },
    ...(user.role === 'owner' ? [{ to: '/app/pets', label: 'My pets', icon: PawPrint }] : []),
    ...(user.role !== 'admin' ? [{ to: '/app/appointments', label: 'Appointments', icon: Video }] : []),
    { to: '/app/doctors', label: 'Veterinarians', icon: Stethoscope },
    ...(user.role === 'doctor' ? [{ to: '/app/availability', label: 'My availability', icon: CalendarDays }] : []),
    ...(user.role === 'doctor' ? [{ to: '/app/recordings', label: 'Recordings', icon: FileVideo }] : []),
    ...(user.role !== 'admin' ? [{ to: '/app/notifications', label: 'Notifications', icon: Bell }] : []),
    ...(user.role === 'admin' ? [{ to: '/app/admin/doctors', label: 'Doctor approvals', icon: ShieldCheck }] : []),
  ]
  return (
    <div className="app-layout">
      <header className="mobile-header">
        <button className="icon-button" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu /></button>
        <span className="brand"><PawPrint /> VetPet Connect</span>
      </header>
      {open && <button className="sidebar-backdrop" onClick={() => setOpen(false)} aria-label="Close navigation" />}
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-brand"><PawPrint /><span>VetPet Connect</span><button className="close-nav" onClick={() => setOpen(false)}><X /></button></div>
        <nav>
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)}><Icon size={19} />{label}{label === 'Notifications' && unreadCount > 0 && <small className="notification-count">{unreadCount > 99 ? '99+' : unreadCount}</small>}</NavLink>
          ))}
          {user.role !== 'admin' && unreadCount > 0 && <span className="sr-only" aria-live="polite">You have {unreadCount} unread notifications</span>}
        </nav>
        <div className="account-card">
          <span className="avatar">{user.full_name.charAt(0).toUpperCase()}</span>
          <div><strong>{user.full_name}</strong><small>{user.role}</small></div>
          <button className="icon-button" onClick={logout} title="Sign out"><LogOut size={18} /></button>
        </div>
      </aside>
      <main className="app-main">{children}</main>
    </div>
  )
}
