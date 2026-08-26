import { ArrowLeft, Circle, Mic, MicOff, PhoneOff, Square, Video, VideoOff } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api, ApiError, tokenStore } from '../api/client'
import { ErrorBlock, LoadingBlock } from '../components/Feedback'
import { RING_TIMEOUT_MS } from '../realtime/constants'
import type { Appointment } from '../types'
import { useAuth } from '../auth/AuthContext'

type Signal = { type: string; initiator?: boolean; sdp?: RTCSessionDescriptionInit; candidate?: RTCIceCandidateInit }

export function CallPage() {
  const { appointmentId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const autojoin = searchParams.get('autojoin') === '1'
  const navigate = useNavigate()
  const { user } = useAuth()
  const query = useQuery({ queryKey: ['appointment', appointmentId], queryFn: () => api.get<Appointment>(`/appointments/${appointmentId}`), enabled: Boolean(appointmentId) })
  const localVideo = useRef<HTMLVideoElement>(null)
  const remoteVideo = useRef<HTMLVideoElement>(null)
  const peer = useRef<RTCPeerConnection | null>(null)
  const socket = useRef<WebSocket | null>(null)
  const localStream = useRef<MediaStream | null>(null)
  const pendingCandidates = useRef<RTCIceCandidateInit[]>([])
  const recorder = useRef<MediaRecorder | null>(null)
  const recordingChunks = useRef<Blob[]>([])
  const recordingStarted = useRef(0)
  const recordingAudioContext = useRef<AudioContext | null>(null)
  const connectedOnce = useRef(false)
  const ringTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const autojoinedRef = useRef(false)
  const [joined, setJoined] = useState(false)
  const [status, setStatus] = useState('Ready to join')
  const [error, setError] = useState<string | null>(null)
  const [micOn, setMicOn] = useState(true)
  const [cameraOn, setCameraOn] = useState(true)
  const [hasRemoteVideo, setHasRemoteVideo] = useState(false)
  const [recording, setRecording] = useState(false)
  const [savingRecording, setSavingRecording] = useState(false)

  const endCall = useCallback(() => {
    if (ringTimeout.current) clearTimeout(ringTimeout.current)
    socket.current?.close(); peer.current?.close(); localStream.current?.getTracks().forEach((track) => track.stop())
    socket.current = null; peer.current = null; localStream.current = null; setJoined(false)
  }, [])
  useEffect(() => endCall, [endCall])

  useEffect(() => {
    function onCallStatus(event: Event) {
      const detail = (event as CustomEvent<{ type: string; appointment_id: string }>).detail
      if (detail.appointment_id !== appointmentId || connectedOnce.current) return
      setStatus(detail.type === 'call_declined' ? 'Call declined' : 'Call ended')
      setError(detail.type === 'call_declined' ? 'The pet owner declined this call.' : 'The call was ended before connecting.')
      endCall()
    }
    window.addEventListener('realtime:call-status', onCallStatus)
    return () => window.removeEventListener('realtime:call-status', onCallStatus)
  }, [appointmentId, endCall])

  async function addPendingCandidates(connection: RTCPeerConnection) {
    for (const candidate of pendingCandidates.current) await connection.addIceCandidate(candidate)
    pendingCandidates.current = []
  }

  const joinCall = useCallback(async () => {
    if (!query.data) return
    setError(null); setStatus('Requesting camera and microphone…')
    try {
      const wantsVideo = query.data.consultation_type === 'video'
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: wantsVideo })
      localStream.current = stream; if (localVideo.current) localVideo.current.srcObject = stream
      setCameraOn(wantsVideo)
      const connection = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] })
      peer.current = connection; stream.getTracks().forEach((track) => connection.addTrack(track, stream))
      connection.ontrack = (event) => { if (remoteVideo.current) remoteVideo.current.srcObject = event.streams[0]; setHasRemoteVideo(true) }
      connection.onconnectionstatechange = () => {
        const connected = connection.connectionState === 'connected'
        setStatus(connected ? 'Connected' : connection.connectionState)
        if (connected) {
          connectedOnce.current = true
          if (ringTimeout.current) clearTimeout(ringTimeout.current)
        }
      }
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(`${protocol}//${location.host}/api/v1/calls/ws/${appointmentId}`)
      socket.current = ws
      connection.onicecandidate = (event) => { if (event.candidate && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ice-candidate', candidate: event.candidate.toJSON() })) }
      ws.onopen = () => { ws.send(JSON.stringify({ type: 'auth', token: tokenStore.get() })); setStatus('Waiting for the other participant…') }
      ws.onmessage = async (event) => {
        const signal = JSON.parse(event.data) as Signal
        if (signal.type === 'peer-ready' && signal.initiator) { const offer = await connection.createOffer(); await connection.setLocalDescription(offer); ws.send(JSON.stringify({ type: 'offer', sdp: offer })) }
        if (signal.type === 'offer' && signal.sdp) { await connection.setRemoteDescription(signal.sdp); await addPendingCandidates(connection); const answer = await connection.createAnswer(); await connection.setLocalDescription(answer); ws.send(JSON.stringify({ type: 'answer', sdp: answer })) }
        if (signal.type === 'answer' && signal.sdp) { await connection.setRemoteDescription(signal.sdp); await addPendingCandidates(connection) }
        if (signal.type === 'ice-candidate' && signal.candidate) { if (connection.remoteDescription) await connection.addIceCandidate(signal.candidate); else pendingCandidates.current.push(signal.candidate) }
        if (signal.type === 'peer-left') setStatus('The other participant left the call')
      }
      ws.onerror = () => setError('Unable to connect to the secure call room. Make sure the backend is running.')
      ws.onclose = (event) => { if (event.code === 1008) setError(event.reason || 'Call access was denied.') }
      setJoined(true)
      if (user?.role === 'doctor') {
        ringTimeout.current = setTimeout(() => {
          if (!connectedOnce.current) {
            setError('The pet owner did not answer.')
            setStatus('No answer')
            void api.post(`/appointments/${appointmentId}/call/cancel`)
            endCall()
          }
        }, RING_TIMEOUT_MS)
      }
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Camera or microphone access failed.'); endCall() }
  }, [query.data, appointmentId, user, endCall])
  function toggleAudio() { const track = localStream.current?.getAudioTracks()[0]; if (track) { track.enabled = !track.enabled; setMicOn(track.enabled) } }
  function toggleVideo() { const track = localStream.current?.getVideoTracks()[0]; if (track) { track.enabled = !track.enabled; setCameraOn(track.enabled) } }
  async function startRecording() {
    if (!query.data || !localStream.current) return
    if (!window.confirm('Confirm that the pet owner has clearly consented to this consultation being recorded. Recording without consent may violate privacy laws.')) return
    const remote = remoteVideo.current?.srcObject as MediaStream | null
    if (!remote) { setError('Wait until the other participant is connected before recording.'); return }
    try {
      const context = new AudioContext()
      const destination = context.createMediaStreamDestination()
      for (const stream of [localStream.current, remote]) {
        if (stream.getAudioTracks().length) context.createMediaStreamSource(stream).connect(destination)
      }
      recordingAudioContext.current = context
      const tracks = [...destination.stream.getAudioTracks()]
      if (query.data.consultation_type === 'video') {
        const videoTrack = remote.getVideoTracks()[0] ?? localStream.current.getVideoTracks()[0]
        if (videoTrack) tracks.push(videoTrack)
      }
      const mixedStream = new MediaStream(tracks)
      const mimeType = query.data.consultation_type === 'video' && MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus') ? 'video/webm;codecs=vp8,opus' : 'audio/webm;codecs=opus'
      const mediaRecorder = new MediaRecorder(mixedStream, { mimeType })
      recordingChunks.current = []; recordingStarted.current = Date.now(); recorder.current = mediaRecorder
      mediaRecorder.ondataavailable = (event) => { if (event.data.size) recordingChunks.current.push(event.data) }
      mediaRecorder.onstop = () => void saveRecording(mimeType.split(';')[0])
      mediaRecorder.start(1000); setRecording(true); setStatus('Connected · Recording with consent')
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Unable to start recording.') }
  }
  async function saveRecording(contentType: string) {
    if (!query.data) return
    setSavingRecording(true)
    try {
      const blob = new Blob(recordingChunks.current, { type: contentType })
      const duration = Math.max(1, Math.round((Date.now() - recordingStarted.current) / 1000))
      const data = new FormData(); data.append('file', blob, `consultation-${query.data.id}.webm`); data.append('consent_confirmed', 'true'); data.append('duration_seconds', String(duration))
      await api.upload(`/recordings/appointments/${query.data.id}`, data)
      setStatus('Recording securely saved to doctor records')
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Unable to save recording.') }
    finally { recordingChunks.current = []; recordingAudioContext.current?.close(); recordingAudioContext.current = null; setSavingRecording(false) }
  }
  function stopRecording() { if (recorder.current?.state === 'recording') recorder.current.stop(); recorder.current = null; setRecording(false) }
  function leave() {
    if (recording) stopRecording()
    if (user?.role === 'doctor' && joined && !connectedOnce.current) {
      void api.post(`/appointments/${appointmentId}/call/cancel`)
    }
    endCall()
    navigate('/app/appointments')
  }

  useEffect(() => {
    if (autojoin && query.data && !autojoinedRef.current && !joined) {
      autojoinedRef.current = true
      void joinCall()
    }
  }, [autojoin, query.data, joined, joinCall])

  if (query.isLoading) return <div className="page-content"><LoadingBlock /></div>
  if (query.isError) return <div className="page-content"><ErrorBlock message={query.error instanceof ApiError ? query.error.message : 'Unable to open appointment.'} /></div>
  if (query.data?.status !== 'confirmed') return <div className="page-content"><ErrorBlock message="The doctor must confirm this appointment before the call can begin." /></div>
  return <div className="call-page"><div className="call-header"><Link to="/app/appointments" className="back-link"><ArrowLeft size={18} />Appointments</Link><div><strong>{query.data.consultation_type === 'video' ? 'Video consultation' : 'Audio consultation'}</strong><span className="call-status">{status}</span></div></div>
    <div className="video-stage"><video ref={remoteVideo} autoPlay playsInline className={`remote-video ${hasRemoteVideo ? 'active' : ''}`} /><div className="remote-placeholder"><Video /><p>{joined ? 'Waiting for the other participant to join…' : 'Your private consultation room is ready'}</p></div><video ref={localVideo} autoPlay muted playsInline className="local-video" /></div>
    {recording && <div className="recording-indicator"><Circle />Recording</div>}{error && <div className="call-error">{error}</div>}<div className="call-controls">{!joined ? <button className="button primary join-call" onClick={() => void joinCall()}>{query.data.consultation_type === 'video' ? <Video /> : <Mic />}Join {query.data.consultation_type} call</button> : <><button className={`call-control ${micOn ? '' : 'off'}`} onClick={toggleAudio} title={micOn ? 'Mute' : 'Unmute'}>{micOn ? <Mic /> : <MicOff />}</button>{query.data.consultation_type === 'video' && <button className={`call-control ${cameraOn ? '' : 'off'}`} onClick={toggleVideo} title={cameraOn ? 'Turn camera off' : 'Turn camera on'}>{cameraOn ? <Video /> : <VideoOff />}</button>}{user?.role === 'doctor' && <button className={`call-control record ${recording ? 'active' : ''}`} disabled={savingRecording} onClick={recording ? stopRecording : () => void startRecording()} title={recording ? 'Stop and save recording' : 'Record with consent'}>{recording ? <Square /> : <Circle />}</button>}<button className="call-control hangup" onClick={leave} title="Leave call"><PhoneOff /></button></>}</div>
  </div>
}
