import { Camera, MessageCircle, Mic, Video } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import { useAuth } from '../auth/AuthContext'
import { useSpeciesLabel } from '../hooks/useSpeciesLabel'
import { useLanguage, type TranslationKey } from '../i18n/LanguageContext'
import type { AppointmentThreadSummary } from '../types'

const previewIcons = { photo: Camera, video: Video, voice: Mic }
const previewLabelKeys: Record<'photo' | 'video' | 'voice', TranslationKey> = {
  photo: 'messages.previewPhoto',
  video: 'messages.previewVideo',
  voice: 'messages.previewVoice',
}

export function MessagesPage() {
  const { user } = useAuth()
  const { t } = useLanguage()
  const speciesLabel = useSpeciesLabel()
  const query = useQuery({
    queryKey: ['message-threads'],
    queryFn: () => api.get<AppointmentThreadSummary[]>('/messages/threads'),
  })

  function previewLine(thread: AppointmentThreadSummary): { icon: typeof MessageCircle | null; text: string } {
    if (!thread.preview) return { icon: null, text: '' }
    const mine = thread.preview.sender_user_id === user?.id
    const prefix = mine ? `${t('messages.you')}: ` : ''
    if (thread.preview.kind === 'message') return { icon: null, text: `${prefix}${thread.preview.text ?? ''}` }
    return { icon: previewIcons[thread.preview.kind], text: `${prefix}${t(previewLabelKeys[thread.preview.kind])}` }
  }

  return (
    <div className="page-content">
      <header className="page-heading">
        <span className="eyebrow">{t('messages.eyebrow')}</span>
        <h1>{t('messages.heading')}</h1>
        <p>{user?.role === 'doctor' ? t('messages.doctorSubtitle') : t('messages.ownerSubtitle')}</p>
      </header>
      {query.isLoading ? (
        <LoadingBlock />
      ) : query.isError ? (
        <ErrorBlock
          message={query.error instanceof ApiError ? query.error.message : 'Unable to load messages.'}
          retry={() => void query.refetch()}
        />
      ) : !query.data || query.data.length === 0 ? (
        <EmptyBlock
          title={t('messages.emptyTitle')}
          text={user?.role === 'doctor' ? t('messages.emptyDoctorText') : t('messages.emptyOwnerText')}
        />
      ) : (
        <div className="notification-list">
          {query.data.map((thread) => {
            const { icon: PreviewIcon, text } = previewLine(thread)
            const title = user?.role === 'doctor' ? `${thread.owner_name} — ${speciesLabel(thread.species)} visit` : `${speciesLabel(thread.species)} visit`
            return (
              <Link
                to={`/app/messages/${thread.appointment_id}`}
                className="notification-card"
                key={thread.appointment_id}
                style={{ textDecoration: 'none', color: 'inherit' }}
              >
                <div className="notification-icon"><MessageCircle /></div>
                <div>
                  <div className="notification-title">
                    <h2>{title}</h2>
                  </div>
                  <p style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    {PreviewIcon && <PreviewIcon size={14} />}
                    {text || ' '}
                  </p>
                  <time>{new Date(thread.last_activity_at).toLocaleString()}</time>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
