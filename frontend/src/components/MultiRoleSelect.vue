<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { popEnter, popLeave } from '../motion'

const props = defineProps({
  modelValue: { type: Array, default: () => [] }, // array of role names
  options: { type: Array, default: () => [] }, // { value, label, icon?, color? }
  width: { type: String, default: 'auto' },
  label: { type: String, default: 'Cargos' },
})
const emit = defineEmits(['update:modelValue'])

const uid = `mrs-${Math.random().toString(36).slice(2, 9)}`
const open = ref(false)
const rootEl = ref(null)
const triggerEl = ref(null)
const panelPos = ref({ top: 0, left: 0, minWidth: 0 })

const selectedOptions = computed(() => props.options.filter((o) => props.modelValue.includes(o.value)))
const triggerText = computed(() => {
  if (!selectedOptions.value.length) return 'Nenhum cargo'
  return selectedOptions.value.map((o) => o.label).join(', ')
})

function updatePanelPos() {
  if (!triggerEl.value) return
  const r = triggerEl.value.getBoundingClientRect()
  panelPos.value = { top: r.bottom + 6, left: r.left, minWidth: r.width }
}
function onWindowScrollOrResize() {
  if (open.value) closePanel()
}

function toggle() {
  if (open.value) closePanel()
  else {
    open.value = true
    updatePanelPos()
  }
}
function closePanel() {
  open.value = false
}
function toggleOption(opt) {
  const set = new Set(props.modelValue)
  if (set.has(opt.value)) set.delete(opt.value)
  else set.add(opt.value)
  emit('update:modelValue', Array.from(set))
}

function onDocClick(e) {
  if (!open.value || !rootEl.value) return
  if (rootEl.value.contains(e.target)) return
  if (e.target.closest?.(`#${uid}-panel`)) return
  closePanel()
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  window.addEventListener('scroll', onWindowScrollOrResize, true)
  window.addEventListener('resize', onWindowScrollOrResize)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  window.removeEventListener('scroll', onWindowScrollOrResize, true)
  window.removeEventListener('resize', onWindowScrollOrResize)
})
</script>

<template>
  <div ref="rootEl" style="position:relative; display:inline-block;" :style="{ width: width === 'auto' ? 'auto' : width }">
    <button
      ref="triggerEl" type="button" @click="toggle"
      :aria-label="label" :aria-expanded="open" aria-haspopup="listbox"
      style="display:flex; align-items:center; gap:8px; width:100%; box-sizing:border-box; border:1px solid #22222f; background:#0e0e14; border-radius:9px; padding:9px 11px; font-size:12.5px; font-weight:600; color:#c7c5dc; cursor:pointer; outline:none;"
      :style="{ borderColor: open ? '#7c6fff' : '#22222f' }">
      <span style="flex:1; text-align:left; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ triggerText }}</span>
      <i class="fi fi-sr-angle-small-down" aria-hidden="true" :style="{ flex: 'none', fontSize: '10px', opacity: 0.6, transition: 'transform .18s ease', transform: open ? 'rotate(180deg)' : 'none' }"></i>
    </button>

    <Teleport to="body">
      <Transition :css="false" @enter="popEnter" @leave="popLeave">
        <div v-if="open" :id="`${uid}-panel`" role="listbox" aria-multiselectable="true"
          :style="{
            position: 'fixed', top: `${panelPos.top}px`, left: `${panelPos.left}px`,
            minWidth: `${panelPos.minWidth}px`, width: 'max-content', maxWidth: '260px', background: '#14141d',
            border: '1px solid #26263a', borderRadius: '10px', padding: '5px', zIndex: 1000,
            boxShadow: '0 14px 40px rgba(0,0,0,.5)', maxHeight: '260px', overflowY: 'auto',
          }">
          <div v-for="opt in options" :key="String(opt.value)" role="option" :aria-selected="modelValue.includes(opt.value)"
            @click="toggleOption(opt)"
            style="display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius:7px; font-size:12.5px; cursor:pointer;"
            :style="{ background: modelValue.includes(opt.value) ? 'rgba(124,111,255,.14)' : 'transparent', color: modelValue.includes(opt.value) ? '#f5f4fb' : '#c7c5dc' }">
            <span :style="{ width: '14px', height: '14px', flex: 'none', borderRadius: '4px', border: `1.5px solid ${modelValue.includes(opt.value) ? '#7c6fff' : '#33313f'}`, background: modelValue.includes(opt.value) ? '#7c6fff' : 'transparent', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }">
              <i v-if="modelValue.includes(opt.value)" class="fi fi-sr-check" style="font-size:8px; color:#0a0a10;" aria-hidden="true"></i>
            </span>
            <i v-if="opt.icon" :class="`fi ${opt.icon}`" :style="{ color: opt.color || 'inherit', flex: 'none' }" aria-hidden="true"></i>
            <span style="white-space:nowrap;">{{ opt.label }}</span>
          </div>
          <div v-if="!options.length" style="padding:10px; font-size:12px; color:#8f8da8;">Nenhum cargo cadastrado.</div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
