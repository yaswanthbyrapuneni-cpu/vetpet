let captionEl: HTMLDivElement | null = null
let captionTimer: ReturnType<typeof setTimeout> | undefined

if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  window.speechSynthesis.getVoices()
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices()
}

function showCaption(text: string) {
  if (typeof document === 'undefined') return
  if (!captionEl) {
    captionEl = document.createElement('div')
    captionEl.className = 'voice-toast'
    document.body.appendChild(captionEl)
  }
  captionEl.textContent = `🔊 ${text}`
  captionEl.style.opacity = '1'
  clearTimeout(captionTimer)
  captionTimer = setTimeout(() => {
    if (captionEl) captionEl.style.opacity = '0'
  }, 3200)
}

/** Speaks teText in Telugu when a Telugu voice is available, otherwise falls back to
 * enFallback in English. Always shows a visible caption matching whichever text is actually
 * spoken, so the confirmation works even when the device is muted, and never shows Telugu
 * text while an English fallback is what's actually spoken (or vice versa). */
export function speakTelugu(teText: string, enFallback: string) {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    showCaption(teText)
    return
  }
  try {
    window.speechSynthesis.cancel()
    setTimeout(() => {
      const voices = window.speechSynthesis.getVoices()
      let voice = voices.find((item) => item.lang?.toLowerCase().startsWith('te'))
      let text = teText
      let lang = 'te-IN'
      if (!voice) {
        voice = voices.find((item) => /en[-_]in/i.test(item.lang)) ?? voices.find((item) => item.lang?.toLowerCase().startsWith('en'))
        text = enFallback
        lang = voice?.lang ?? 'en-IN'
      }
      showCaption(text)
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = lang
      utterance.rate = 0.95
      if (voice) utterance.voice = voice
      window.speechSynthesis.speak(utterance)
    }, 60)
  } catch {
    showCaption(teText)
  }
}
