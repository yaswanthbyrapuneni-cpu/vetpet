import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { AppointmentsPage } from './pages/AppointmentsPage'
import { CallPage } from './pages/CallPage'
import { DoctorRecordsPage } from './pages/DoctorRecordsPage'
import { ClinicalCarePage } from './pages/ClinicalCarePage'
import { ConsultationPage } from './pages/ConsultationPage'
import { MessagesPage } from './pages/MessagesPage'
import { MessageThreadPage } from './pages/MessageThreadPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { PaymentDetailsPage } from './pages/PaymentDetailsPage'
import { RecordsPage } from './pages/RecordsPage'

function ProtectedApp() {
  const { user } = useAuth()
  const location = useLocation()
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
  return (
    <AppShell>
      <Routes>
        <Route index element={<DashboardPage />} />
        <Route path="appointments" element={user.role === 'admin' ? <Navigate to="/app" replace /> : <AppointmentsPage />} />
        <Route path="appointments/:appointmentId/payment" element={user.role === 'admin' ? <Navigate to="/app" replace /> : <PaymentDetailsPage />} />
        <Route path="call/:appointmentId" element={user.role === 'admin' ? <Navigate to="/app" replace /> : <CallPage />} />
        <Route path="recordings" element={user.role === 'doctor' ? <DoctorRecordsPage /> : <Navigate to="/app" replace />} />
        <Route path="appointments/:appointmentId/care" element={user.role === 'doctor' ? <ClinicalCarePage /> : <Navigate to="/app" replace />} />
        <Route path="appointments/:appointmentId/consultation" element={user.role === 'admin' ? <Navigate to="/app" replace /> : <ConsultationPage />} />
        <Route path="messages" element={user.role === 'admin' ? <Navigate to="/app" replace /> : <MessagesPage />} />
        <Route path="messages/:appointmentId" element={user.role === 'admin' ? <Navigate to="/app" replace /> : <MessageThreadPage />} />
        <Route path="notifications" element={user.role === 'admin' ? <Navigate to="/app" replace /> : <NotificationsPage />} />
        <Route
          path="records"
          element={user.role === 'owner' ? <RecordsPage /> : <Navigate to="/app" replace />}
        />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </AppShell>
  )
}

export function App() {
  const { user, loading } = useAuth()
  if (loading && !user) {
    return <div className="page-loader" role="status"><span className="spinner" />Loading…</div>
  }
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/app" replace /> : <LoginPage />} />
      <Route path="/app/*" element={<ProtectedApp />} />
      <Route path="*" element={<Navigate to={user ? '/app' : '/login'} replace />} />
    </Routes>
  )
}
