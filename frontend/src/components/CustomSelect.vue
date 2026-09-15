<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { popEnter, popLeave } from '../motion'

const props = defineProps({
  modelValue: { default: null },
  options: { type: Array, default: () => [] }, // { value, label, icon?, color? }
  placeholder: { type: String, default: 'Selecionar' },
  disabled: { type: Boolean, default: false },
  align: { type: String, default: 'left' }, // left | right
  width: { type: String, default: 'auto' }, // css width for the trigger, e.g. '100%'
  label: { type: String, default: '' }, // accessible name when there's no visible <label for>
})
const emit = defineEmits(['update:modelValue'])

const uid = `cs-${Math.random().toString(36).slice(2, 9)}`
const open = ref(false)
const rootEl = ref(null)
const triggerEl = ref(null)
const optionRefs = ref([])
const activeIndex = ref(-1)

const selected = computed(() => props.options.find((o) => o.value === props.modelValue))
const selectedIndex = computed(() => props.options.findIndex((o) => o.value === props.modelValue))

function setOptionRef(i) {
  return (el) => {
    if (el) optionRefs.value[i] = el
  }
}

function openPanel(focusIndex) {
  if (props.disabled) return
  open.value = true
  activeIndex.value = focusIndex ?? (selectedIndex.value >= 0 ? selectedIndex.value : 0)
  nextTick(() => optionRefs.value[activeIndex.value]?.scrollIntoView({ block: 'nearest' }))
}
function closePanel(refocusTrigger) {
  open.value = false
  if (refocusTrigger) triggerEl.value?.focus()
}
function toggle() {
  if (props.disabled) return
  open.value ? closePanel(false) : openPanel()
}
function select(opt) {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  closePanel(true)
}

function moveActive(delta) {
  if (!props.options.length) return
  let next = activeIndex.value
  do {
    next = (next + delta + props.options.length) % props.options.length
  } while (props.options[next]?.disabled && next !== activeIndex.value)
  activeIndex.value = next
  nextTick(() => optionRefs.value[next]?.scrollIntoView({ block: 'nearest' }))
}

// Focus stays on the trigger the whole time (standard combobox pattern); the
// currently-highlighted option is only communicated via aria-activedescendant,
// so all keyboard handling lives here rather than needing the (non-focusable)
// listbox panel to own its own key handler.
function onTriggerKeydown(e) {
  if (!open.value) {
    if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) {
      e.preventDefault()
      openPanel()
    }
    return
  }
  if (e.key === 'Escape') {
    e.preventDefault()
    closePanel(true)
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    moveActive(1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    moveActive(-1)
  } else if (e.key === 'Home') {
    e.preventDefault()
    activeIndex.value = 0
  } else if (e.key === 'End') {
    e.preventDefault()
    activeIndex.value = props.options.length - 1
  } else if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    if (activeIndex.value >= 0) select(props.options[activeIndex.value])
  }
}

function onDocClick(e) {
  if (open.value && rootEl.value && !rootEl.value.contains(e.target)) closePanel(false)
}
onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div ref="rootEl" class="cs-root" :style="{ position: 'relative', width: width === 'auto' ? 'auto' : width, display: 'inline-block' }">
    <button
      ref="triggerEl"
      type="button"
      class="cs-trigger"
      role="combobox"
      :aria-expanded="open"
      :aria-controls="`${uid}-listbox`"
      :aria-activedescendant="open && activeIndex >= 0 ? `${uid}-opt-${activeIndex}` : undefined"
      :aria-label="label || undefined"
      aria-haspopup="listbox"
      @click="toggle"
      @keydown="onTriggerKeydown"
      :disabled="disabled"
      :style="{
        display: 'flex', alignItems: 'center', gap: '8px', width: '100%', boxSizing: 'border-box',
        border: `1px solid ${open ? '#7c6fff' : '#22222f'}`, background: disabled ? '#131319' : '#0e0e14',
        borderRadius: '9px', padding: '9px 11px', fontSize: '12.5px', fontWeight: '600',
        color: disabled ? '#5f5d78' : '#c7c5dc', cursor: disabled ? 'default' : 'pointer',
        outline: 'none', opacity: disabled ? 0.7 : 1,
      }"
    >
      <i v-if="selected?.icon" :class="`fi ${selected.icon}`" :style="{ color: selected.color || 'inherit', flex: 'none' }" aria-hidden="true"></i>
      <span style="flex:1; text-align:left; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
        {{ selected ? selected.label : placeholder }}
      </span>
      <i class="fi fi-sr-angle-small-down" aria-hidden="true" :style="{ flex: 'none', fontSize: '10px', opacity: 0.6, transition: 'transform .18s ease', transform: open ? 'rotate(180deg)' : 'none' }"></i>
    </button>

    <Transition :css="false" @enter="popEnter" @leave="popLeave">
      <div
        v-if="open"
        :id="`${uid}-listbox`"
        class="cs-panel"
        role="listbox"
        :style="{
          position: 'absolute', top: 'calc(100% + 6px)', [align === 'right' ? 'right' : 'left']: 0,
          minWidth: '100%', width: 'max-content', maxWidth: '280px', background: '#14141d',
          border: '1px solid #26263a', borderRadius: '10px', padding: '5px', zIndex: 60,
          boxShadow: '0 14px 40px rgba(0,0,0,.5)', maxHeight: '260px', overflowY: 'auto',
        }"
      >
        <div
          v-for="(opt, i) in options"
          :key="String(opt.value)"
          :ref="setOptionRef(i)"
          :id="`${uid}-opt-${i}`"
          class="cs-option"
          role="option"
          :aria-selected="opt.value === modelValue"
          @click="select(opt)"
          @mouseenter="activeIndex = i"
          :style="{
            display: 'flex', alignItems: 'center', gap: '7px', padding: '8px 10px', borderRadius: '7px',
            fontSize: '12.5px', fontWeight: opt.value === modelValue ? '700' : '500',
            color: opt.disabled ? '#5f5d78' : (opt.value === modelValue ? '#f5f4fb' : '#c7c5dc'),
            background: i === activeIndex ? 'rgba(124,111,255,.16)' : (opt.value === modelValue ? 'rgba(124,111,255,.14)' : 'transparent'),
            cursor: opt.disabled ? 'default' : 'pointer', whiteSpace: 'nowrap',
          }"
        >
          <i v-if="opt.icon" :class="`fi ${opt.icon}`" :style="{ color: opt.color || 'inherit', flex: 'none' }" aria-hidden="true"></i>
          <span v-if="opt.color && !opt.icon" :style="{ width: '7px', height: '7px', borderRadius: '50%', background: opt.color, flex: 'none' }" aria-hidden="true"></span>
          {{ opt.label }}
        </div>
        <div v-if="!options.length" style="padding:10px; font-size:12px; color:#8f8da8;">Nenhuma opção.</div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.cs-trigger:not(:disabled):hover {
  border-color: #34334a;
}
.cs-option:hover {
  background: rgba(124, 111, 255, 0.1);
}
</style>
