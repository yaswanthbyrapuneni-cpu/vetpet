import { ArrowLeft, PawPrint } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'

type Role = 'owner' | 'doctor'

export function RegisterPage() {
  const navigate = useNavigate()
  const [role, setRole] = useState<Role>('owner')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const data = new FormData(event.currentTarget)
    const common = {
      full_name: data.get('name'),
      email: data.get('email'),
      password: data.get('password'),
    }
    try {
      if (role === 'owner') {
        await api.post('/auth/register/owner', { ...common, phone: data.get('phone') || null })
      } else {
        await api.post('/auth/register/doctor', {
          ...common,
          license_number: data.get('license'),
          qualification: data.get('qualification'),
          specialization: data.get('specialization') || null,
        })
      }
      navigate('/login', { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Registration failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="register-page">
      <div className="register-shell">
        <Link className="back-link" to="/login"><ArrowLeft size={18} />Back to sign in</Link>
        <div className="brand"><PawPrint />VetPet Connect</div>
        <form className="register-card" onSubmit={submit}>
          <header><span className="eyebrow">Join the platform</span><h1>Create your account</h1><p>Choose how you will use VetPet Connect.</p></header>
          <div className="role-tabs" role="group" aria-label="Account type">
            <button type="button" className={role === 'owner' ? 'active' : ''} onClick={() => setRole('owner')}>Pet owner<small>Manage pets and their care</small></button>
            <button type="button" className={role === 'doctor' ? 'active' : ''} onClick={() => setRole('doctor')}>Veterinarian<small>Provide professional care</small></button>
          </div>
          <div className="form-grid">
            <label>Full name<input name="name" required minLength={2} /></label>
            <label>Email address<input name="email" type="email" required /></label>
            {role === 'owner' && <label>Phone number <small>Optional</small><input name="phone" type="tel" /></label>}
            {role === 'doctor' && <>
              <label>Licence number<input name="license" required minLength={3} /></label>
              <label>Qualification<input name="qualification" required minLength={2} /></label>
              <label>Specialization <small>Optional</small><input name="specialization" /></label>
            </>}
            <label className="span-two">Password<input name="password" type="password" required minLength={8} autoComplete="new-password" /><small>Use at least 8 characters.</small></label>
          </div>
          {role === 'doctor' && <div className="info-banner">Veterinarian accounts require administrator verification before appearing publicly.</div>}
          {error && <div className="inline-error" role="alert">{error}</div>}
          <button className="button primary full" disabled={busy}>{busy ? 'Creating account…' : 'Create account'}</button>
        </form>
      </div>
    </main>
  )
}

