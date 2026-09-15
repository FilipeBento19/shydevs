let ctx = null

function getCtx() {
  if (!ctx) {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (!Ctx) return null
    ctx = new Ctx()
  }
  return ctx
}

function tone(freq, start, duration, gainPeak = 0.08) {
  const c = getCtx()
  if (!c) return
  const osc = c.createOscillator()
  const gain = c.createGain()
  osc.type = 'sine'
  osc.frequency.value = freq
  gain.gain.setValueAtTime(0, c.currentTime + start)
  gain.gain.linearRampToValueAtTime(gainPeak, c.currentTime + start + 0.02)
  gain.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + start + duration)
  osc.connect(gain)
  gain.connect(c.destination)
  osc.start(c.currentTime + start)
  osc.stop(c.currentTime + start + duration + 0.05)
}

export function playDing() {
  tone(880, 0, 0.18)
  tone(1318.5, 0.09, 0.22)
}

export function playPop() {
  tone(520, 0, 0.08, 0.05)
}
