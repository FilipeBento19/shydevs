<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { formatTime } from '../mediaUtils'

const props = defineProps({
  src: { type: String, required: true },
  autoplay: { type: Boolean, default: true },
})

const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2]

const root = ref(null)
const video = ref(null)
const playing = ref(false)
const current = ref(0)
const duration = ref(0)
const buffered = ref(0)
const volume = ref(1)
const muted = ref(false)
const rate = ref(1)
const speedOpen = ref(false)
const fullscreen = ref(false)
const controlsVisible = ref(true)
const seeking = ref(false)
const error = ref(false)
const loading = ref(true)

const progress = computed(() => (duration.value ? (current.value / duration.value) * 100 : 0))
const bufferedPct = computed(() => (duration.value ? (buffered.value / duration.value) * 100 : 0))
const effectiveVolume = computed(() => (muted.value ? 0 : volume.value))
const volumeIcon = computed(() => (effectiveVolume.value === 0 ? 'fi-sr-volume-mute' : 'fi-sr-volume'))

// ---- remember volume across videos ----
function loadPrefs() {
  try {
    const v = parseFloat(localStorage.getItem('shydevs_player_volume'))
    if (Number.isFinite(v)) volume.value = Math.min(1, Math.max(0, v))
    muted.value = localStorage.getItem('shydevs_player_muted') === '1'
  } catch (e) {
    // storage unavailable — defaults are fine
  }
}
function savePrefs() {
  try {
    localStorage.setItem('shydevs_player_volume', String(volume.value))
    localStorage.setItem('shydevs_player_muted', muted.value ? '1' : '0')
  } catch (e) {
    // ignore
  }
}

function applyVolume() {
  if (!video.value) return
  video.value.volume = volume.value
  video.value.muted = muted.value
}

// ---- controls auto-hide while playing ----
let hideTimer = null
function poke() {
  controlsVisible.value = true
  clearTimeout(hideTimer)
  if (playing.value && !speedOpen.value) {
    hideTimer = setTimeout(() => { controlsVisible.value = false }, 2600)
  }
}

// ---- playback ----
function toggle() {
  const el = video.value
  if (!el) return
  if (el.paused || el.ended) el.play().catch(() => {})
  else el.pause()
  poke()
}
function seekTo(seconds) {
  const el = video.value
  if (!el || !duration.value) return
  el.currentTime = Math.min(duration.value, Math.max(0, seconds))
  current.value = el.currentTime
}
function skip(delta) {
  seekTo((video.value?.currentTime || 0) + delta)
  poke()
}
function setVolume(v) {
  volume.value = Math.min(1, Math.max(0, v))
  muted.value = volume.value === 0
  applyVolume()
  savePrefs()
}
function toggleMute() {
  muted.value = !muted.value
  if (!muted.value && volume.value === 0) volume.value = 0.5
  applyVolume()
  savePrefs()
}
function setRate(r) {
  rate.value = r
  if (video.value) video.value.playbackRate = r
  speedOpen.value = false
  poke()
}
function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen?.()
  else root.value?.requestFullscreen?.()
}

// ---- progress bar (click + drag) ----
const track = ref(null)
function ratioFromEvent(e) {
  const rect = track.value.getBoundingClientRect()
  return Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
}
function onTrackDown(e) {
  if (!duration.value) return
  seeking.value = true
  track.value.setPointerCapture(e.pointerId)
  seekTo(ratioFromEvent(e) * duration.value)
}
function onTrackMove(e) {
  if (seeking.value) seekTo(ratioFromEvent(e) * duration.value)
}
function onTrackUp() {
  seeking.value = false
}
function onTrackKey(e) {
  if (e.key === 'ArrowLeft') { skip(-5); e.preventDefault(); e.stopPropagation() }
  else if (e.key === 'ArrowRight') { skip(5); e.preventDefault(); e.stopPropagation() }
}

// ---- volume slider ----
const volTrack = ref(null)
let volDragging = false
function volFromEvent(e) {
  const rect = volTrack.value.getBoundingClientRect()
  return (e.clientX - rect.left) / rect.width
}
function onVolDown(e) {
  volDragging = true
  volTrack.value.setPointerCapture(e.pointerId)
  setVolume(volFromEvent(e))
}
function onVolMove(e) {
  if (volDragging) setVolume(volFromEvent(e))
}
function onVolUp() {
  volDragging = false
}

// ---- keyboard (player focused) ----
function onKey(e) {
  if (e.target.closest?.('.vp-speed-menu')) return
  const handled = () => { e.preventDefault(); e.stopPropagation(); poke() }
  switch (e.key) {
    case ' ': case 'k': case 'K': toggle(); handled(); break
    case 'ArrowLeft': skip(-5); handled(); break
    case 'ArrowRight': skip(5); handled(); break
    case 'j': case 'J': skip(-10); handled(); break
    case 'l': case 'L': skip(10); handled(); break
    case 'ArrowUp': setVolume(volume.value + 0.1); handled(); break
    case 'ArrowDown': setVolume(volume.value - 0.1); handled(); break
    case 'm': case 'M': toggleMute(); handled(); break
    case 'f': case 'F': toggleFullscreen(); handled(); break
    default:
  }
}

// ---- <video> events ----
function updateBuffered() {
  const el = video.value
  if (!el || !el.buffered.length) return
  const t = el.currentTime
  for (let i = 0; i < el.buffered.length; i++) {
    if (el.buffered.start(i) <= t && t <= el.buffered.end(i)) {
      buffered.value = el.buffered.end(i)
      return
    }
  }
}
function onLoadedMetadata() {
  duration.value = video.value.duration
  loading.value = false
  applyVolume()
}
function onTimeUpdate() {
  if (!seeking.value) current.value = video.value.currentTime
  updateBuffered()
}
function onPlay() { playing.value = true; poke() }
function onPause() { playing.value = false; clearTimeout(hideTimer); controlsVisible.value = true }
function onError() { error.value = true; loading.value = false }
function onFullscreenChange() { fullscreen.value = document.fullscreenElement === root.value }

// The viewer's open animation can leave the player briefly invisible, and
// hidden elements refuse focus — so retry for a moment until it takes, which
// is what makes space/arrows control the video as soon as it opens.
let focusTries = 0
function focusSelf() {
  root.value?.focus({ preventScroll: true })
  if (document.activeElement !== root.value && focusTries++ < 8) setTimeout(focusSelf, 90)
}

onMounted(() => {
  loadPrefs()
  applyVolume()
  document.addEventListener('fullscreenchange', onFullscreenChange)
  focusSelf()
})
onBeforeUnmount(() => {
  clearTimeout(hideTimer)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  video.value?.pause()
})
watch(() => props.src, () => {
  error.value = false
  loading.value = true
  current.value = 0
  duration.value = 0
  buffered.value = 0
})
</script>

<template>
  <div ref="root" class="vp" :class="{ 'vp-idle': playing && !controlsVisible, 'vp-full': fullscreen }" tabindex="0"
    role="group" aria-label="Player de vídeo" @keydown="onKey" @mousemove="poke" @touchstart.passive="poke">
    <video ref="video" class="vp-video" :src="src" :autoplay="autoplay" playsinline preload="metadata"
      @click="toggle" @dblclick="toggleFullscreen" @loadedmetadata="onLoadedMetadata" @timeupdate="onTimeUpdate"
      @progress="updateBuffered" @play="onPlay" @pause="onPause" @error="onError" @waiting="loading = true"
      @canplay="loading = false" @ended="onPause"></video>

    <div v-if="loading && !error" class="vp-center" aria-live="polite"><span class="btn-spinner vp-spinner" aria-hidden="true"></span></div>
    <button v-else-if="!playing && !error" type="button" class="vp-center vp-big" aria-label="Reproduzir" @click="toggle">
      <i class="fi fi-sr-play" aria-hidden="true"></i>
    </button>
    <div v-if="error" class="vp-center vp-error" role="alert">
      <i class="fi fi-sr-video-camera" aria-hidden="true"></i>
      <span>Não foi possível reproduzir este vídeo aqui.</span>
      <a :href="src" target="_blank" rel="noopener" download>Abrir / baixar o arquivo</a>
    </div>

    <div class="vp-controls" @click.stop>
      <div ref="track" class="vp-track" role="slider" tabindex="0" aria-label="Progresso do vídeo"
        :aria-valuemin="0" :aria-valuemax="Math.round(duration)" :aria-valuenow="Math.round(current)"
        :aria-valuetext="`${formatTime(current)} de ${formatTime(duration)}`"
        @pointerdown="onTrackDown" @pointermove="onTrackMove" @pointerup="onTrackUp" @pointercancel="onTrackUp" @keydown="onTrackKey">
        <div class="vp-buffered" :style="{ width: bufferedPct + '%' }"></div>
        <div class="vp-played" :style="{ width: progress + '%' }"></div>
        <div class="vp-thumb" :style="{ left: progress + '%' }"></div>
      </div>

      <div class="vp-row">
        <button type="button" class="vp-btn" :aria-label="playing ? 'Pausar' : 'Reproduzir'" @click="toggle">
          <i :class="`fi ${playing ? 'fi-sr-pause' : 'fi-sr-play'}`" aria-hidden="true"></i>
        </button>
        <button type="button" class="vp-btn" aria-label="Voltar 10 segundos" @click="skip(-10)">
          <i class="fi fi-sr-rewind" aria-hidden="true"></i>
        </button>

        <div class="vp-volume">
          <button type="button" class="vp-btn" :aria-label="muted ? 'Ativar som' : 'Silenciar'" @click="toggleMute">
            <i :class="`fi ${volumeIcon}`" aria-hidden="true"></i>
          </button>
          <div ref="volTrack" class="vp-vol-track" role="slider" tabindex="0" aria-label="Volume"
            :aria-valuemin="0" :aria-valuemax="100" :aria-valuenow="Math.round(effectiveVolume * 100)"
            @pointerdown="onVolDown" @pointermove="onVolMove" @pointerup="onVolUp" @pointercancel="onVolUp"
            @keydown.left.stop.prevent="setVolume(volume - 0.1)" @keydown.right.stop.prevent="setVolume(volume + 0.1)">
            <div class="vp-vol-fill" :style="{ width: effectiveVolume * 100 + '%' }"></div>
          </div>
        </div>

        <span class="vp-time">{{ formatTime(current) }} <span class="vp-dim">/ {{ formatTime(duration) }}</span></span>
        <span class="vp-spacer"></span>

        <div class="vp-speed">
          <button type="button" class="vp-btn vp-speed-btn" aria-haspopup="menu" :aria-expanded="speedOpen" aria-label="Velocidade de reprodução"
            @click="speedOpen = !speedOpen; poke()">{{ rate }}×</button>
          <div v-if="speedOpen" class="vp-speed-menu" role="menu">
            <button v-for="s in SPEEDS" :key="s" type="button" role="menuitemradio" :aria-checked="rate === s"
              :class="{ active: rate === s }" @click="setRate(s)">{{ s }}×</button>
          </div>
        </div>

        <button type="button" class="vp-btn" :aria-label="fullscreen ? 'Sair da tela cheia' : 'Tela cheia'" @click="toggleFullscreen">
          <i :class="`fi ${fullscreen ? 'fi-sr-compress' : 'fi-sr-expand'}`" aria-hidden="true"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vp { position: relative; width: 100%; height: 100%; background: #000; border-radius: 12px; overflow: hidden; outline: none; user-select: none; }
.vp:focus-visible { box-shadow: 0 0 0 2px #7c6fff; }
.vp-full { border-radius: 0; }
.vp-video { display: block; width: 100%; height: 100%; object-fit: contain; background: #000; cursor: pointer; }
.vp-idle { cursor: none; }
.vp-idle .vp-controls { opacity: 0; pointer-events: none; }

.vp-center { position: absolute; inset: 0; margin: auto; width: 64px; height: 64px; display: flex; align-items: center; justify-content: center; pointer-events: none; }
.vp-big { pointer-events: auto; border: none; border-radius: 50%; background: rgba(20, 20, 29, .72); color: #fff; font-size: 22px; cursor: pointer; backdrop-filter: blur(6px); transition: transform .15s ease, background-color .15s ease; }
.vp-big:hover { background: rgba(124, 111, 255, .85); transform: scale(1.06); }
.vp-big i { margin-left: 3px; }
.vp-spinner { width: 28px; height: 28px; border-width: 3px; }
.vp-error { width: auto; height: auto; flex-direction: column; gap: 8px; color: #c7c5dc; font-size: 13px; text-align: center; padding: 20px; pointer-events: auto; }
.vp-error i { font-size: 26px; opacity: .6; }
.vp-error a { color: #b3aaff; font-weight: 700; }

.vp-controls { position: absolute; left: 0; right: 0; bottom: 0; padding: 26px 14px 10px; background: linear-gradient(transparent, rgba(0, 0, 0, .78)); transition: opacity .2s ease; }
.vp-track { position: relative; height: 16px; display: flex; align-items: center; cursor: pointer; touch-action: none; }
.vp-track::before { content: ''; position: absolute; left: 0; right: 0; height: 4px; border-radius: 4px; background: rgba(255, 255, 255, .22); transition: height .12s ease; }
.vp-track:hover::before, .vp-track:focus-visible::before { height: 6px; }
.vp-buffered, .vp-played { position: absolute; left: 0; height: 4px; border-radius: 4px; transition: height .12s ease; }
.vp-buffered { background: rgba(255, 255, 255, .34); }
.vp-played { background: #7c6fff; }
.vp-track:hover .vp-buffered, .vp-track:hover .vp-played, .vp-track:focus-visible .vp-buffered, .vp-track:focus-visible .vp-played { height: 6px; }
.vp-thumb { position: absolute; width: 13px; height: 13px; margin-left: -6.5px; border-radius: 50%; background: #fff; box-shadow: 0 0 0 3px rgba(124, 111, 255, .45); transform: scale(0); transition: transform .12s ease; }
.vp-track:hover .vp-thumb, .vp-track:focus-visible .vp-thumb { transform: scale(1); }

.vp-row { display: flex; align-items: center; gap: 4px; margin-top: 2px; }
.vp-btn { border: none; background: transparent; color: #f5f4fb; width: 34px; height: 34px; border-radius: 8px; font-size: 14px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; transition: background-color .12s ease; }
.vp-btn:hover { background: rgba(255, 255, 255, .14); }
.vp-btn:focus-visible { outline: 2px solid #7c6fff; }
.vp-time { font-size: 12px; font-weight: 600; color: #f5f4fb; margin-left: 6px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.vp-dim { color: rgba(255, 255, 255, .6); }
.vp-spacer { flex: 1; }

.vp-volume { display: flex; align-items: center; }
.vp-vol-track { position: relative; width: 0; height: 16px; opacity: 0; cursor: pointer; touch-action: none; transition: width .18s ease, opacity .18s ease, margin .18s ease; display: flex; align-items: center; }
.vp-volume:hover .vp-vol-track, .vp-vol-track:focus-visible { width: 70px; opacity: 1; margin: 0 8px 0 2px; }
.vp-vol-track::before { content: ''; position: absolute; left: 0; right: 0; height: 4px; border-radius: 4px; background: rgba(255, 255, 255, .25); }
.vp-vol-fill { position: relative; height: 4px; border-radius: 4px; background: #fff; }

.vp-speed { position: relative; }
.vp-speed-btn { width: auto; padding: 0 9px; font-size: 12px; font-weight: 700; }
.vp-speed-menu { position: absolute; right: 0; bottom: 40px; background: rgba(20, 20, 29, .96); border: 1px solid #26263a; border-radius: 10px; padding: 4px; display: flex; flex-direction: column; min-width: 64px; box-shadow: 0 10px 30px rgba(0, 0, 0, .5); }
.vp-speed-menu button { border: none; background: transparent; color: #c7c5dc; font-size: 12px; font-weight: 600; text-align: left; padding: 6px 10px; border-radius: 6px; cursor: pointer; }
.vp-speed-menu button:hover { background: rgba(255, 255, 255, .08); }
.vp-speed-menu button.active { color: #fff; background: rgba(124, 111, 255, .3); }

@media (max-width: 760px) {
  .vp-controls { padding: 22px 8px 6px; }
  .vp-vol-track { display: none; }
  .vp-btn { width: 32px; height: 32px; }
}
</style>
