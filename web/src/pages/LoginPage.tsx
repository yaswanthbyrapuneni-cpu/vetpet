import { HeartPulse, LockKeyhole, Mail, PawPrint, ShieldCheck, Video } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function LoginPage() {
  const { login, loading, error, clearError } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  useEffect(() => clearError, [clearError])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (await login(email, password)) navigate('/app')
  }

  return (
    <main className="auth-layout">
      <section className="auth-hero">
        <div className="hero-content">
          <span className="brand light"><PawPrint /> VetPet Connect</span>
          <h1>Thoughtful veterinary care, wherever you are.</h1>
          <p>Manage pet health records, meet verified veterinarians, and keep every treatment organized.</p>
          <div className="feature-list">
            <span><Video />Secure online consultations</span>
            <span><HeartPulse />Complete digital health history</span>
            <span><ShieldCheck />Verified veterinary professionals</span>
          </div>
        </div>
      </section>
      <section className="auth-panel">
        <form className="auth-card" onSubmit={submit}>
          <div className="mobile-brand brand"><PawPrint /> VetPet Connect</div>
          <div><span className="eyebrow">Welcome back</span><h2>Sign in to your account</h2><p>Continue managing your pet's healthcare.</p></div>
          <label>Email address<div className="input-with-icon"><Mail /><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required placeholder="you@example.com" /></div></label>
          <label>Password<div className="input-with-icon"><LockKeyhole /><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required placeholder="Your password" /></div></label>
          {error && <div className="inline-error" role="alert">{error}</div>}
          <button className="button primary full" disabled={loading}>{loading ? <><span className="spinner small" />Signing in…</> : 'Sign in'}</button>
          <p className="auth-switch">New to VetPet Connect? <Link to="/register">Create an account</Link></p>
        </form>
      </section>
    </main>
  )
}

