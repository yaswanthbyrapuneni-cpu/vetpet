import { useLanguage } from '../i18n/LanguageContext'

export function LanguageSwitcher({ className = '' }: { className?: string }) {
  const { language, setLanguage, t } = useLanguage()
  return (
    <div className={`language-switcher ${className}`} role="group" aria-label="Language">
      <button type="button" className={language === 'te' ? 'active' : ''} onClick={() => setLanguage('te')}>{t('language.telugu')}</button>
      <button type="button" className={language === 'en' ? 'active' : ''} onClick={() => setLanguage('en')}>{t('language.english')}</button>
    </div>
  )
}
