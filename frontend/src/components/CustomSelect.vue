<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { popEnter, popLeave } from '../motion'

const props = defineProps({
  modelValue: { default: null },
  options: { type: Array, default: () => [] }, // { value, label, icon?, color? }
  placeholder: { type: String, default: 'Selecionar' },
  disabled: { type: Boolean, default: false },
  align: { type: String, default: 'left' }, // left | right
  width: { type: String, default: 'auto' }, // css width for the trigger, e.g. '100%'
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const rootEl = ref(null)

const selected = computed(() => props.options.find((o) => o.value === props.modelValue))

function toggle() {
  if (props.disabled) return
  open.value = !open.value
}
function select(opt) {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  open.value = false
}
function onDocClick(e) {
  if (open.value && rootEl.value && !rootEl.value.contains(e.target)) open.value = false
}
function onKeydown(e) {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  window.addEventListener('keydown', onKeydown)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div ref="rootEl" class="cs-root" :style="{ position: 'relative', width: width === 'auto' ? 'auto' : width, display: 'inline-block' }">
    <button
      type="button"
      class="cs-trigger"
      @click="toggle"
      :disabled="disabled"
      :style="{
        display: 'flex', alignItems: 'center', gap: '8px', width: '100%', boxSizing: 'border-box',
        border: `1px solid ${open ? '#7c6fff' : '#22222f'}`, background: disabled ? '#131319' : '#0e0e14',
        borderRadius: '9px', padding: '9px 11px', fontSize: '12.5px', fontWeight: '600',
        color: disabled ? '#5f5d78' : '#c7c5dc', cursor: disabled ? 'default' : 'pointer',
        outline: 'none', opacity: disabled ? 0.7 : 1,
      }"
    >
      <i v-if="selected?.icon" :class="`fi ${selected.icon}`" :style="{ color: selected.color || 'inherit', flex: 'none' }"></i>
      <span style="flex:1; text-align:left; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
        {{ selected ? selected.label : placeholder }}
      </span>
      <i class="fi fi-sr-angle-small-down" :style="{ flex: 'none', fontSize: '10px', opacity: 0.6, transition: 'transform .18s ease', transform: open ? 'rotate(180deg)' : 'none' }"></i>
    </button>

    <Transition :css="false" @enter="popEnter" @leave="popLeave">
      <div
        v-if="open"
        class="cs-panel"
        :style="{
          position: 'absolute', top: 'calc(100% + 6px)', [align === 'right' ? 'right' : 'left']: 0,
          minWidth: '100%', width: 'max-content', maxWidth: '280px', background: '#14141d',
          border: '1px solid #26263a', borderRadius: '10px', padding: '5px', zIndex: 60,
          boxShadow: '0 14px 40px rgba(0,0,0,.5)', maxHeight: '260px', overflowY: 'auto',
        }"
      >
        <div
          v-for="opt in options"
          :key="String(opt.value)"
          class="cs-option"
          @click="select(opt)"
          :style="{
            display: 'flex', alignItems: 'center', gap: '7px', padding: '8px 10px', borderRadius: '7px',
            fontSize: '12.5px', fontWeight: opt.value === modelValue ? '700' : '500',
            color: opt.disabled ? '#5f5d78' : (opt.value === modelValue ? '#f5f4fb' : '#c7c5dc'),
            background: opt.value === modelValue ? 'rgba(124,111,255,.14)' : 'transparent',
            cursor: opt.disabled ? 'default' : 'pointer', whiteSpace: 'nowrap',
          }"
        >
          <i v-if="opt.icon" :class="`fi ${opt.icon}`" :style="{ color: opt.color || 'inherit', flex: 'none' }"></i>
          <span v-if="opt.color && !opt.icon" :style="{ width: '7px', height: '7px', borderRadius: '50%', background: opt.color, flex: 'none' }"></span>
          {{ opt.label }}
        </div>
        <div v-if="!options.length" style="padding:10px; font-size:12px; color:#6f6d87;">Nenhuma opção.</div>
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
