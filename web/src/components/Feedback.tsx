import { AlertCircle, Inbox } from 'lucide-react'

export function LoadingBlock() {
  return <div className="feedback"><span className="spinner" /><p>Loading…</p></div>
}

export function ErrorBlock({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="feedback error"><AlertCircle /><p>{message}</p>{retry && <button className="button secondary" onClick={retry}>Try again</button>}</div>
}

export function EmptyBlock({ title, text }: { title: string; text: string }) {
  return <div className="feedback"><Inbox /><h3>{title}</h3><p>{text}</p></div>
}
