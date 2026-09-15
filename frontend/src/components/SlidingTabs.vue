<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { gsap, reduceMotion } from '../motion'

const props = defineProps({
  items: { type: Array, required: true }, // { key, label, icon?, count? }
  modelValue: { type: [String, Number], required: true },
  pillColor: { type: String, default: '#7c6fff' },
  activeTextColor: { type: String, default: '#0a0a10' },
  inactiveTextColor: { type: String, default: '#8b899f' },
  trackStyle: { type: Object, default: () => ({}) },
  itemPadding: { type: String, default: '7px 12px' },
  gap: { type: String, default: '2px' },
})
const emit = defineEmits(['update:modelValue'])

const containerEl = ref(null)
const pillEl = ref(null)
const btnEls = {}

function setBtnRef(key) {
  return (el) => {
    if (el) btnEls[key] = el
  }
}

function movePill(animate) {
  const btn = btnEls[props.modelValue]
  if (!btn || !pillEl.value) return
  const vars = { x: btn.offsetLeft, y: btn.offsetTop, width: btn.offsetWidth, height: btn.offsetHeight }
  if (animate && !reduceMotion) {
    gsap.to(pillEl.value, { ...vars, duration: 0.4, ease: 'power3.out' })
  } else {
    gsap.set(pillEl.value, vars)
  }
}

function onClick(item, e) {
  if (!reduceMotion) {
    gsap.fromTo(e.currentTarget, { scale: 0.94 }, { scale: 1, duration: 0.3, ease: 'back.out(4)' })
  }
  emit('update:modelValue', item.key)
}

let ro
onMounted(async () => {
  await nextTick()
  movePill(false)
  if (window.ResizeObserver && containerEl.value) {
    ro = new ResizeObserver(() => movePill(false))
    ro.observe(containerEl.value)
  }
})
onUnmounted(() => ro?.disconnect())

watch(() => props.modelValue, async () => {
  await nextTick()
  movePill(true)
})
watch(
  () => props.items.map((i) => `${i.key}:${i.label}:${i.count}`).join('|'),
  async () => {
    await nextTick()
    movePill(false)
  }
)
</script>

<template>
  <div ref="containerEl" :style="{ position: 'relative', display: 'inline-flex', flexWrap: 'wrap', gap, ...trackStyle }">
    <div ref="pillEl" :style="{ position: 'absolute', top: 0, left: 0, borderRadius: '8px', background: pillColor, zIndex: 0 }"></div>
    <button
      v-for="item in items"
      :key="item.key"
      :ref="setBtnRef(item.key)"
      type="button"
      @click="onClick(item, $event)"
      :style="{
        position: 'relative', zIndex: 1, border: 'none', background: 'transparent', cursor: 'pointer',
        padding: itemPadding, borderRadius: '8px', fontSize: '12.5px', fontWeight: '700',
        display: 'inline-flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap',
        color: modelValue === item.key ? activeTextColor : inactiveTextColor,
        transition: 'color .2s ease',
      }"
    >
      <i v-if="item.icon" :class="`fi ${item.icon}`"></i>{{ item.label }}
      <span v-if="item.count !== undefined" style="opacity:.65;">{{ item.count }}</span>
    </button>
  </div>
</template>
