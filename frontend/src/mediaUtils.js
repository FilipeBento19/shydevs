// Pure helpers for the references feature (kept separate so they're easy to reason about).

export function youtubeId(url) {
  try {
    const u = new URL(url)
    const host = u.hostname.replace(/^www\.|^m\./, '')
    if (host === 'youtu.be') return u.pathname.slice(1).split('/')[0] || null
    if (host === 'youtube.com' || host === 'youtube-nocookie.com') {
      if (u.pathname === '/watch') return u.searchParams.get('v')
      const m = u.pathname.match(/^\/(?:shorts|embed|live)\/([\w-]{6,})/)
      return m ? m[1] : null
    }
  } catch (e) {
    // not a valid URL
  }
  return null
}

export function vimeoId(url) {
  try {
    const u = new URL(url)
    if (u.hostname.replace(/^www\./, '') !== 'vimeo.com') return null
    const m = u.pathname.match(/^\/(\d+)/)
    return m ? m[1] : null
  } catch (e) {
    return null
  }
}

// Start offset in seconds from a link's ?t= / ?start= / #t= ("90", "1m30s", "1h2m3s").
export function startSeconds(url) {
  try {
    const u = new URL(url)
    const raw = u.searchParams.get('t') || u.searchParams.get('start') || new URLSearchParams(u.hash.slice(1)).get('t')
    if (!raw) return 0
    if (/^\d+$/.test(raw)) return Number(raw)
    const m = raw.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/)
    return m ? (+m[1] || 0) * 3600 + (+m[2] || 0) * 60 + (+m[3] || 0) : 0
  } catch (e) {
    return 0
  }
}

// An iframe-embeddable URL for links we know how to embed, else null.
export function embedUrl(url) {
  const start = startSeconds(url)
  const yt = youtubeId(url)
  if (yt) return `https://www.youtube-nocookie.com/embed/${yt}?rel=0${start ? `&start=${start}` : ''}`
  const vm = vimeoId(url)
  if (vm) return `https://player.vimeo.com/video/${vm}${start ? `#t=${start}s` : ''}`
  return null
}

export function linkThumbnail(url) {
  const yt = youtubeId(url)
  return yt ? `https://img.youtube.com/vi/${yt}/mqdefault.jpg` : null
}

export function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch (e) {
    return url
  }
}

export function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00'
  const s = Math.floor(seconds)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = String(s % 60).padStart(2, '0')
  return h ? `${h}:${String(m).padStart(2, '0')}:${sec}` : `${m}:${sec}`
}

// The URL a reference should be opened/played from.
export function referenceSource(ref) {
  return ref.file || ref.url || ''
}

export function referenceTitle(ref) {
  return ref.caption || ref.file_name || (ref.url ? hostOf(ref.url) : 'Referência')
}
