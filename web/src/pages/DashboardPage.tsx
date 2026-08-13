import { Bell, CalendarDays, ChevronRight, FileHeart, PawPrint, Stethoscope } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function DashboardPage() {
  const { user } = useAuth()
  if (!user) return null
  const firstName = user.full_name.split(' ')[0]
  return (
    <div className="page-content">
      <header className="page-heading"><div><span className="eyebrow">Your care dashboard</span><h1>Good day, {firstName}</h1><p>{user.role === 'owner' ? "Everything about your pets' care, in one calm place." : 'Your veterinary workspace is ready.'}</p></div></header>
      {user.role === 'owner' ? <>
        <section className="hero-card"><div><span className="hero-kicker">Start here</span><h2>Build a complete health profile for every pet.</h2><p>Add your pets, keep their records organized, and connect with verified veterinarians when care is needed.</p><Link to="/app/pets" className="button light">Manage my pets <ChevronRight size={18} /></Link></div><PawPrint className="hero-mark" /></section>
        <section><div className="section-heading"><h2>Quick actions</h2></div><div className="action-grid">
          <Link className="action-tile" to="/app/pets"><span className="tile-icon mint"><PawPrint /></span><div><h3>My pets</h3><p>Profiles and health details</p></div><ChevronRight /></Link>
          <Link className="action-tile" to="/app/doctors"><span className="tile-icon blue"><Stethoscope /></span><div><h3>Find a veterinarian</h3><p>Browse verified doctors</p></div><ChevronRight /></Link>
          <div className="action-tile disabled"><span className="tile-icon amber"><CalendarDays /></span><div><h3>Appointments</h3><p>Booking screen coming next</p></div></div>
          <div className="action-tile disabled"><span className="tile-icon rose"><FileHeart /></span><div><h3>Medical records</h3><p>Clinical history coming next</p></div></div>
        </div></section>
        <section className="empty-panel"><Bell /><div><h3>No urgent reminders</h3><p>Medicine, vaccination, and follow-up reminders will appear here.</p></div></section>
      </> : <section className="hero-card"><div><span className="hero-kicker">Professional account</span><h2>Welcome to your veterinary workspace.</h2><p>Availability, appointment, patient, and consultation screens will connect to the existing backend next.</p></div><Stethoscope className="hero-mark" /></section>}
    </div>
  )
}

