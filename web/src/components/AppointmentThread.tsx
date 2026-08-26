import { Camera, Mic, Paperclip, Send, Square, Video } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { LoadingBlock } from './Feedback'
import type { AppointmentAttachment, AppointmentMessage } from '../types'

type TFunction = ReturnType<typeof useLanguage>['t']

const CLUSTER_WINDOW_MS = 90_000

interface AttachmentGroup {
  key: string
  senderId: string
  createdAt: string
  kind: 'photo' | 'video' | 'voice'
  items: AppointmentAttachment[]
}

type TimelineEntry =
  | { kind: 'message'; key: string; senderId: string; createdAt: string; message: AppointmentMessage }
  | { kind: 'attachments'; key: string; senderId: string; createdAt: string; group: AttachmentGroup }

function groupAttachments(attachments: AppointmentAttachment[]): AttachmentGroup[] {
  const sorted = [...attachments].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  const groups: AttachmentGroup[] = []
  for (const attachment of sorted) {
    const last = groups[groups.length - 1]
    const canJoin = last && attachment.kind === 'photo' && last.kind === 'photo' && last.senderId === attachment.uploaded_by_user_id &&
      new Date(attachment.created_at).getTime() - new Date(last.createdAt).getTime() < CLUSTER_WINDOW_MS
    if (canJoin) {
      last.items.push(attachment)
      last.createdAt = attachment.created_at
    } else {
      groups.push({ key: `group-${attachment.id}`, senderId: attachment.uploaded_by_user_id, createdAt: attachment.created_at, kind: attachment.kind, items: [attachment] })
    }
  }
  return groups
}

function buildTimeline(messages: AppointmentMessage[], attachments: AppointmentAttachment[]): TimelineEntry[] {
  const messageEntries: TimelineEntry[] = messages.map((message) => ({ kind: 'message', key: message.id, senderId: message.sender_user_id, createdAt: message.created_at, message }))
  const attachmentEntries: TimelineEntry[] = groupAttachments(attachments).map((group) => ({ kind: 'attachments', key: group.key, senderId: group.senderId, createdAt: group.createdAt, group }))
  return [...messageEntries, ...attachmentEntries].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
}

function useBlobUrl(attachmentId: string, enabled: boolean) {
  const [url, setUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    if (!enabled) return
    let active = true
    let objectUrl: string | null = null
    setLoading(true)
    api.blob(`/attachments/${attachmentId}/download`)
      .then((blob) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .finally(() => { if (active) setLoading(false) })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [attachmentId, enabled])
  return { url, loading }
}

function PhotoTile({ attachment, extra }: { attachment: AppointmentAttachment; extra?: number }) {
  const { url } = useBlobUrl(attachment.id, true)
  return (
    <a className="thread-phototile" href={url ?? undefined} target="_blank" rel="noopener noreferrer" onClick={(event) => { if (!url) event.preventDefault() }}>
      {url ? <img src={url} alt={attachment.original_filename} /> : <Camera size={20} />}
      {extra ? <span className="more-overlay">+{extra}</span> : null}
    </a>
  )
}

function MediaBubble({ group, mine, kind, t }: { group: AttachmentGroup; mine: boolean; kind: 'video' | 'voice'; t: TFunction }) {
  const attachment = group.items[0]
  const [open, setOpen] = useState(false)
  const { url, loading } = useBlobUrl(attachment.id, open)

  if (kind === 'video' && open) {
    return <div className={`thread-mediatile ${mine ? 'me' : 'them'} playing`}>{url ? <video src={url} controls autoPlay /> : <LoadingBlock />}</div>
  }

  return (
    <button type="button" className={`thread-mediatile ${kind === 'voice' ? 'voice ' : ''}${mine ? 'me' : 'them'}`} onClick={() => setOpen(true)} disabled={loading}>
      <span className="mi">{kind === 'video' ? <Video size={17} /> : <Mic size={17} />}</span>
      {kind === 'voice' && (
        <span className="thread-voice-bars" aria-hidden>{Array.from({ length: 14 }).map((_, index) => <span key={index} style={{ height: `${6 + ((index * 7) % 16)}px` }} />)}</span>
      )}
      {kind === 'video' ? (
        <span>{loading ? t('common.loading') : attachment.original_filename}</span>
      ) : open ? (
        url ? <audio src={url} controls autoPlay style={{ height: 30, maxWidth: 130 }} /> : <span>{t('common.loading')}</span>
      ) : (
        <span>{t('messages.play')}</span>
      )}
    </button>
  )
}

export function AppointmentThread({ appointmentId }: { appointmentId: string }) {
  const { user } = useAuth()
  const { t } = useLanguage()
  const queryClient = useQueryClient()
  const messagesKey = ['messages', appointmentId]
  const attachmentsKey = ['attachments', appointmentId]
  // The realtime channel invalidates these instantly on a new message/attachment;
  // this interval is just a fallback in case a push is missed while the socket reconnects.
  const messages = useQuery({ queryKey: messagesKey, queryFn: () => api.get<AppointmentMessage[]>(`/appointments/${appointmentId}/messages`), refetchInterval: 60000 })
  const attachments = useQuery({ queryKey: attachmentsKey, queryFn: () => api.get<AppointmentAttachment[]>(`/appointments/${appointmentId}/attachments`), refetchInterval: 60000 })

  const [body, setBody] = useState('')
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const threadEnd = useRef<HTMLDivElement>(null)

  const send = useMutation({
    mutationFn: (text: string) => api.post<AppointmentMessage>(`/appointments/${appointmentId}/messages`, { body: text }),
    onSuccess: () => { setBody(''); void queryClient.invalidateQueries({ queryKey: messagesKey }) },
  })
  const upload = useMutation({
    mutationFn: (file: File | Blob) => {
      const data = new FormData()
      data.append('file', file, file instanceof File ? file.name : `voice-note-${Date.now()}.webm`)
      return api.upload<AppointmentAttachment>(`/appointments/${appointmentId}/attachments`, data)
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: attachmentsKey }),
    onError: (caught) => setError(caught instanceof ApiError ? caught.message : 'Unable to upload attachment.'),
  })

  const timeline = useMemo(() => buildTimeline(messages.data ?? [], attachments.data ?? []), [messages.data, attachments.data])

  useEffect(() => { threadEnd.current?.scrollIntoView({ block: 'end' }) }, [timeline.length])

  function submit(event: FormEvent) {
    event.preventDefault()
    if (body.trim()) send.mutate(body.trim())
  }

  function pickFiles() { fileInput.current?.click() }
  async function onFilesChosen(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ''
    for (const file of files) await upload.mutateAsync(file)
  }

  async function startRecording() {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      chunks.current = []
      mediaRecorder.ondataavailable = (event) => { if (event.data.size) chunks.current.push(event.data) }
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        upload.mutate(new Blob(chunks.current, { type: 'audio/webm' }))
      }
      recorder.current = mediaRecorder
      mediaRecorder.start()
      setRecording(true)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Microphone access failed.')
    }
  }
  function stopRecording() {
    recorder.current?.stop()
    recorder.current = null
    setRecording(false)
  }

  const loading = messages.isLoading || attachments.isLoading

  return (
    <section className="clinical-panel thread-panel">
      <div className="panel-title"><Send /><div><h2>{t('chat.heading')}</h2><p>{t('chat.subtitle')}</p></div></div>
      {loading ? <LoadingBlock /> : (
        <div className="thread">
          {timeline.length === 0 && <p className="muted">{t('chat.empty')}</p>}
          {timeline.map((entry) => {
            const mine = entry.senderId === user?.id
            const time = new Date(entry.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            if (entry.kind === 'message') {
              return (
                <div key={entry.key} className={`chat-msg ${mine ? 'me' : 'them'}`}>
                  {entry.message.body}
                  <span className="ts">{time}</span>
                </div>
              )
            }
            const { group } = entry
            if (group.kind === 'photo') {
              const shown = group.items.slice(0, 4)
              const remaining = group.items.length - shown.length
              return (
                <div key={entry.key} className={`thread-block ${mine ? 'me' : 'them'}`}>
                  <div className="thread-photogrid" data-count={shown.length}>
                    {shown.map((attachment, index) => (
                      <PhotoTile key={attachment.id} attachment={attachment} extra={index === shown.length - 1 && remaining > 0 ? remaining : undefined} />
                    ))}
                  </div>
                  <span className="ts block">{group.items.length > 1 ? `${group.items.length} photos · ${time}` : time}</span>
                </div>
              )
            }
            return (
              <div key={entry.key} className={`thread-block ${mine ? 'me' : 'them'}`}>
                <MediaBubble group={group} mine={mine} kind={group.kind === 'video' ? 'video' : 'voice'} t={t} />
                <span className="ts block">{time}</span>
              </div>
            )
          })}
          <div ref={threadEnd} />
        </div>
      )}
      {(send.isError || error) && <div className="inline-error">{error ?? (send.error instanceof ApiError ? send.error.message : 'Unable to send message.')}</div>}
      <form className="thread-composer" onSubmit={submit}>
        <input ref={fileInput} type="file" accept="image/jpeg,image/png,video/webm,video/mp4" multiple hidden onChange={(event) => void onFilesChosen(event)} />
        <button type="button" className="icon-button attach" onClick={pickFiles} disabled={upload.isPending} title={t('attach.addPhotoVideo')}><Paperclip size={18} /></button>
        <input value={body} onChange={(event) => setBody(event.target.value)} placeholder={t('chat.placeholder')} maxLength={4000} />
        {!recording ? (
          <button type="button" className="icon-button attach" onClick={() => void startRecording()} disabled={upload.isPending} title={t('attach.recordVoice')}><Mic size={18} /></button>
        ) : (
          <button type="button" className="icon-button attach recording" onClick={stopRecording} title={t('attach.stopUpload')}><Square size={18} /></button>
        )}
        <button className="button primary" disabled={send.isPending || !body.trim()}><Send size={16} /></button>
      </form>
    </section>
  )
}
