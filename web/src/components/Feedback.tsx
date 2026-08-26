import { AlertCircle, Inbox } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'

export function LoadingBlock() {
  const { t } = useLanguage()
  return <div className="feedback"><span className="spinner" /><p>{t('common.loading')}</p></div>
}

export function ErrorBlock({ message, retry }: { message: string; retry?: () => void }) {
  const { t } = useLanguage()
  return <div className="feedback error"><AlertCircle /><p>{message}</p>{retry && <button className="button secondary" onClick={retry}>{t('common.tryAgain')}</button>}</div>
}

export function EmptyBlock({ title, text }: { title: string; text: string }) {
  return <div className="feedback"><Inbox /><h3>{title}</h3><p>{text}</p></div>
}
