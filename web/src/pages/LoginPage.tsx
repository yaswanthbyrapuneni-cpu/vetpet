import { HeartPulse, KeyRound, PawPrint, Phone, ShieldCheck, Video } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { SESSION_EXPIRED_FLAG } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { LanguageSwitcher } from '../components/LanguageSwitcher'

export function LoginPage() {
  const { requestOtp, verifyOtp, loading, error, clearError } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const next = searchParams.get('next')
  const [step, setStep] = useState<'mobile' | 'code'>('mobile')
  const [mobileNumber, setMobileNumber] = useState('')
  const [fullName, setFullName] = useState('')
  const [code, setCode] = useState('')
  const [devOtp, setDevOtp] = useState<string | null>(null)
  const [sessionExpired, setSessionExpired] = useState(false)

  useEffect(() => clearError, [clearError])

  useEffect(() => {
    try {
      if (sessionStorage.getItem(SESSION_EXPIRED_FLAG)) {
        setSessionExpired(true)
        sessionStorage.removeItem(SESSION_EXPIRED_FLAG)
      }
    } catch {
      /* sessionStorage unavailable — just skip the banner */
    }
  }, [])

  async function submitMobile(event: FormEvent) {
    event.preventDefault()
    const otp = await requestOtp(mobileNumber)
    if (otp !== null) {
      setDevOtp(otp)
      setStep('code')
    }
  }

  async function submitCode(event: FormEvent) {
    event.preventDefault()
    if (await verifyOtp(mobileNumber, code, fullName || undefined)) navigate(next || '/app')
  }

  return (
    <main className="auth-layout">
      <section className="auth-hero">
        <div className="hero-content">
          <span className="brand light"><PawPrint /> {t('app.brand')}</span>
          <h1>{t('login.tagline')}</h1>
          <p>{t('login.subtitle')}</p>
          <div className="feature-list">
            <span><Video />{t('login.featureCalls')}</span>
            <span><HeartPulse />{t('login.featureRecords')}</span>
            <span><ShieldCheck />{t('login.featureVerified')}</span>
          </div>
        </div>
      </section>
      <section className="auth-panel">
        <LanguageSwitcher className="login-language" />
        {step === 'mobile' && (
          <form className="auth-card" onSubmit={submitMobile}>
            <div className="mobile-brand brand"><PawPrint /> {t('app.brand')}</div>
            <div><span className="eyebrow">{t('login.welcome')}</span><h2>{t('login.signInHeading')}</h2><p>{t('login.signInSubtitle')}</p></div>
            {sessionExpired && <div className="info-banner">{t('login.sessionExpired')}</div>}
            <label>{t('login.mobileLabel')}<div className="input-with-icon"><Phone /><input type="tel" value={mobileNumber} onChange={(event) => setMobileNumber(event.target.value)} autoComplete="tel" required placeholder="+91 98765 43210" /></div></label>
            <label>{t('login.nameLabel')} <small>{t('login.nameHint')}</small><input type="text" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder={t('login.nameLabel')} /></label>
            {error && <div className="inline-error" role="alert">{error}</div>}
            <button className="button primary full" disabled={loading}>{loading ? <><span className="spinner small" />{t('login.sending')}</> : t('login.sendOtp')}</button>
          </form>
        )}
        {step === 'code' && (
          <form className="auth-card" onSubmit={submitCode}>
            <div className="mobile-brand brand"><PawPrint /> {t('app.brand')}</div>
            <div><span className="eyebrow">{t('login.welcome')}</span><h2>{t('login.verifyHeading')}</h2><p>{t('login.sentTo', { mobile: mobileNumber })}</p></div>
            {devOtp && <div className="info-banner">{t('login.devOtp', { code: devOtp })}</div>}
            <label>{t('login.codeLabel')}<div className="input-with-icon"><KeyRound /><input type="text" inputMode="numeric" value={code} onChange={(event) => setCode(event.target.value)} autoComplete="one-time-code" required placeholder="123456" /></div></label>
            {error && <div className="inline-error" role="alert">{error}</div>}
            <button className="button primary full" disabled={loading}>{loading ? <><span className="spinner small" />{t('login.verifying')}</> : t('login.verify')}</button>
            <p className="auth-switch"><button type="button" className="link-button" onClick={() => setStep('mobile')}>{t('login.changeNumber')}</button></p>
          </form>
        )}
      </section>
    </main>
  )
}
