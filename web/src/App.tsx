import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { DoctorsPage } from './pages/DoctorsPage'
import { LoginPage } from './pages/LoginPage'
import { PetsPage } from './pages/PetsPage'
import { RegisterPage } from './pages/RegisterPage'
import { AdminDoctorsPage } from './pages/AdminDoctorsPage'
import { AvailabilityPage } from './pages/AvailabilityPage'
import { BookAppointmentPage } from './pages/BookAppointmentPage'
import { AppointmentsPage } from './pages/AppointmentsPage'
import { CallPage } from './pages/CallPage'
import { DoctorRecordsPage } from './pages/DoctorRecordsPage'
import { ClinicalCarePage } from './pages/ClinicalCarePage'
import { NotificationsPage } from './pages/NotificationsPage'

function ProtectedApp() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return (
    <AppShell>
      <Routes>
        <Route index element={<DashboardPage />} />
        <Route path="doctors" element={<DoctorsPage />} />
        <Route path="doctors/:doctorId" element={user.role === 'owner' ? <BookAppointmentPage /> : <Navigate to="/app/doctors" replace />} />
        <Route path="availability" element={user.role === 'doctor' ? <AvailabilityPage /> : <Navigate to="/app" replace />} />
        <Route path="appointments" element={user.role === 'admin' ? <Navigate to="/app" replace /> : <AppointmentsPage />} />
        <Route path="call/:appointmentId" element={user.role === 'admin' ? <Navigate to="/app" replace /> : <CallPage />} />
        <Route path="recordings" element={user.role === 'doctor' ? <DoctorRecordsPage /> : <Navigate to="/app" replace />} />
        <Route path="appointments/:appointmentId/care" element={user.role === 'doctor' ? <ClinicalCarePage /> : <Navigate to="/app" replace />} />
        <Route path="notifications" element={user.role === 'admin' ? <Navigate to="/app" replace /> : <NotificationsPage />} />
        <Route path="admin/doctors" element={user.role === 'admin' ? <AdminDoctorsPage /> : <Navigate to="/app" replace />} />
        <Route
          path="pets"
          element={user.role === 'owner' ? <PetsPage /> : <Navigate to="/app" replace />}
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
      <Route path="/register" element={user ? <Navigate to="/app" replace /> : <RegisterPage />} />
      <Route path="/app/*" element={<ProtectedApp />} />
      <Route path="*" element={<Navigate to={user ? '/app' : '/login'} replace />} />
    </Routes>
  )
}
