import { Download, FileVideo, ShieldCheck } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, ApiError } from '../api/client'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/Feedback'
import type { CallRecording } from '../types'

export function DoctorRecordsPage() {
  const query = useQuery({ queryKey: ['recordings'], queryFn: () => api.get<CallRecording[]>('/recordings') })
  const [opening, setOpening] = useState<string | null>(null)
  async function open(recording: CallRecording) {
    setOpening(recording.id)
    try { const blob = await api.blob(`/recordings/${recording.id}/media`); const url = URL.createObjectURL(blob); window.open(url, '_blank', 'noopener,noreferrer'); setTimeout(() => URL.revokeObjectURL(url), 60000) } finally { setOpening(null) }
  }
  return <div className="page-content"><header className="page-heading"><span className="eyebrow">Secure clinical media</span><h1>Consultation recordings</h1><p>Consent-confirmed call recordings accessible only to the assigned veterinarian.</p></header><div className="privacy-banner"><ShieldCheck /><div><strong>Protected clinical records</strong><p>Recordings include consent time and SHA-256 integrity verification. Never share downloaded files through unsecured channels.</p></div></div>
    {query.isLoading ? <LoadingBlock /> : query.isError ? <ErrorBlock message={query.error instanceof ApiError ? query.error.message : 'Unable to load recordings.'} retry={() => void query.refetch()} /> : query.data?.length === 0 ? <EmptyBlock title="No recordings saved" text="During a connected consultation, use the record control after receiving owner consent." /> : <div className="recording-grid">{query.data?.map((item) => <article className="recording-card" key={item.id}><div className="recording-file"><FileVideo /></div><div><h2>Consultation recording</h2><p>{new Date(item.created_at).toLocaleString()}</p><div className="recording-meta"><span>{item.content_type.startsWith('video') ? 'Video' : 'Audio'}</span><span>{(item.size_bytes / 1024 / 1024).toFixed(1)} MB</span>{item.duration_seconds && <span>{Math.floor(item.duration_seconds / 60)}m {item.duration_seconds % 60}s</span>}</div><small>Consent confirmed {new Date(item.consent_confirmed_at).toLocaleString()}</small></div><button className="button secondary" disabled={opening === item.id} onClick={() => void open(item)}><Download size={17} />{opening === item.id ? 'Opening…' : 'Open recording'}</button></article>)}</div>}
  </div>
}
