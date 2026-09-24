<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { modalEnter, modalLeave } from '../motion'
import { embedUrl, hostOf, referenceSource, referenceTitle } from '../mediaUtils'
import VideoPlayer from './VideoPlayer.vue'

const props = defineProps({
  items: { type: Array, required: true },
  index: { type: Number, default: 0 },
})
const emit = defineEmits(['close', 'update:index'])

const item = computed(() => props.items[props.index])
const source = computed(() => (item.value ? referenceSource(item.value) : ''))
const embed = computed(() => (item.value?.kind === 'link' ? embedUrl(item.value.url) : null))
const hasPrev = computed(() => props.index > 0)
const hasNext = computed(() => props.index < props.items.length - 1)
const zoomed = ref(false)
const dialog = ref(null)

watch(() => props.index, () => { zoomed.value = false })

function go(delta) {
  const next = props.index + delta
  if (next >= 0 && next < props.items.length) emit('update:index', next)
}

function onKey(e) {
  if (e.key === 'Escape') emit('close')
  else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { go(-1); e.preventDefault() }
  else if (e.key === 'ArrowRight' || e.key === 'PageDown') { go(1); e.preventDefault() }
}

let previousOverflow = ''
onMounted(() => {
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  window.addEventListener('keydown', onKey)
  // Videos focus their own player (so space/arrows control playback);
  // everything else gets the dialog itself so Esc/arrows work right away.
  if (item.value?.kind !== 'video') dialog.value?.focus()
})
onBeforeUnmount(() => {
  document.body.style.overflow = previousOverflow
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <Teleport to="body">
    <Transition :css="false" appear @enter="modalEnter" @leave="modalLeave">
      <div class="mv-backdrop" @click.self="emit('close')">
        <div ref="dialog" class="mv-dialog modal-panel" role="dialog" aria-modal="true" :aria-label="item ? referenceTitle(item) : 'Referência'" tabindex="-1">
          <header class="mv-head">
            <div class="mv-title">
              <strong>{{ item ? referenceTitle(item) : '' }}</strong>
              <span v-if="item">{{ item.group }} · {{ item.uploaded_by_name || 'Alguém' }}</span>
            </div>
            <span class="mv-count" aria-live="polite">{{ index + 1 }} / {{ items.length }}</span>
            <a v-if="source" class="mv-icon-btn" :href="source" target="_blank" rel="noopener" aria-label="Abrir em nova aba">
              <i class="fi fi-sr-arrow-up-right-from-square" aria-hidden="true"></i>
            </a>
            <button type="button" class="mv-icon-btn" aria-label="Fechar" @click="emit('close')">
              <i class="fi fi-sr-cross" aria-hidden="true"></i>
            </button>
          </header>

          <div class="mv-stage" v-if="item">
            <button v-if="hasPrev" type="button" class="mv-nav mv-prev" aria-label="Anterior" @click="go(-1)">
              <i class="fi fi-sr-angle-left" aria-hidden="true"></i>
            </button>
            <button v-if="hasNext" type="button" class="mv-nav mv-next" aria-label="Próximo" @click="go(1)">
              <i class="fi fi-sr-angle-right" aria-hidden="true"></i>
            </button>

            <div v-if="item.kind === 'video'" :key="item.id" class="mv-video">
              <VideoPlayer :src="source" />
            </div>

            <div v-else-if="item.kind === 'image'" class="mv-image-wrap nice-scroll" :class="{ zoomed }">
              <img :key="item.id" :src="source" :alt="referenceTitle(item)" :class="{ zoomed }"
                @click="zoomed = !zoomed" :title="zoomed ? 'Clique para ajustar à tela' : 'Clique para ampliar'" />
            </div>

            <div v-else-if="embed" class="mv-embed">
              <iframe :key="item.id" :src="embed" title="Vídeo incorporado" allow="accelerometer; autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>
            </div>

            <div v-else class="mv-card">
              <i :class="`fi ${item.kind === 'link' ? 'fi-sr-link' : 'fi-sr-file'}`" aria-hidden="true"></i>
              <strong>{{ referenceTitle(item) }}</strong>
              <span v-if="item.kind === 'link'">{{ hostOf(item.url) }}</span>
              <a :href="source" target="_blank" rel="noopener">{{ item.kind === 'link' ? 'Abrir link' : 'Abrir / baixar arquivo' }}</a>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.mv-backdrop { position: fixed; inset: 0; z-index: 1000; background: rgba(3, 3, 8, .9); display: flex; align-items: center; justify-content: center; padding: 20px; }
.mv-dialog { width: min(1280px, 100%); max-height: 100%; display: flex; flex-direction: column; gap: 10px; outline: none; }
.mv-head { display: flex; align-items: center; gap: 10px; color: #f5f4fb; }
.mv-title { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.mv-title strong { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mv-title span { font-size: 11.5px; color: #8b899f; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mv-count { font-size: 11.5px; font-weight: 700; color: #8b899f; background: #14141d; border: 1px solid #22222f; border-radius: 999px; padding: 4px 10px; white-space: nowrap; }
.mv-icon-btn { width: 34px; height: 34px; flex: none; display: inline-flex; align-items: center; justify-content: center; border: 1px solid #26263a; background: #14141d; color: #c7c5dc; border-radius: 9px; font-size: 13px; cursor: pointer; text-decoration: none; }
.mv-icon-btn:hover { background: #1c1c28; color: #fff; }

.mv-stage { position: relative; display: flex; align-items: center; justify-content: center; min-height: 0; }
.mv-video { width: 100%; height: min(78vh, calc((100vw - 40px) * 9 / 16)); max-width: 1280px; }
.mv-image-wrap { max-width: 100%; max-height: 80vh; overflow: auto; display: flex; border-radius: 12px; background: #0b0b11; }
.mv-image-wrap img { display: block; margin: auto; max-width: 100%; max-height: 80vh; object-fit: contain; cursor: zoom-in; }
.mv-image-wrap img.zoomed { max-width: none; max-height: none; cursor: zoom-out; }
.mv-embed { width: 100%; max-width: 1280px; aspect-ratio: 16 / 9; max-height: 80vh; border-radius: 12px; overflow: hidden; background: #000; }
.mv-embed iframe { width: 100%; height: 100%; border: 0; display: block; }
.mv-card { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 40px 32px; background: #14141d; border: 1px solid #22222f; border-radius: 14px; color: #c7c5dc; text-align: center; max-width: 480px; }
.mv-card i { font-size: 30px; color: #9d93ff; }
.mv-card strong { color: #f5f4fb; font-size: 14px; word-break: break-word; }
.mv-card span { font-size: 12px; color: #8b899f; }
.mv-card a { margin-top: 6px; background: #7c6fff; color: #0a0a10; font-weight: 700; font-size: 12.5px; padding: 9px 16px; border-radius: 9px; text-decoration: none; }

.mv-nav { position: absolute; top: 50%; transform: translateY(-50%); z-index: 3; width: 42px; height: 42px; border-radius: 50%; border: 1px solid #26263a; background: rgba(20, 20, 29, .82); color: #f5f4fb; font-size: 15px; cursor: pointer; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(6px); }
.mv-nav:hover { background: rgba(124, 111, 255, .85); }
.mv-prev { left: 10px; }
.mv-next { right: 10px; }

@media (max-width: 760px) {
  .mv-backdrop { padding: 10px; align-items: flex-start; }
  .mv-video { height: min(60vh, calc((100vw - 20px) * 9 / 16)); }
  .mv-nav { width: 36px; height: 36px; }
  .mv-prev { left: 4px; }
  .mv-next { right: 4px; }
}
</style>
