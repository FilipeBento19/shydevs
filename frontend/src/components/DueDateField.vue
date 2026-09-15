<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Data de entrega' },
})
const emit = defineEmits(['update:modelValue'])

function setQuickDate(offsetDays) {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  emit('update:modelValue', d.toISOString().slice(0, 10))
}

const quickBtnStyle = 'border:1px solid #26263a; background:transparent; border-radius:9px; padding:9px 12px; font-size:12px; font-weight:600; color:#c7c5dc; cursor:pointer;'
</script>

<template>
  <div style="display:flex; gap:7px; flex-wrap:wrap;">
    <input type="date" :aria-label="label" :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" style="flex:1; min-width:150px; border:1px solid #26263a; background:#0e0e14; border-radius:9px; padding:9px 11px; font-size:12.5px; color:#c7c5dc; outline:none;" />
    <button type="button" @click="setQuickDate(0)" :style="quickBtnStyle">Hoje</button>
    <button type="button" @click="setQuickDate(1)" :style="quickBtnStyle">Amanhã</button>
    <button type="button" @click="setQuickDate(7)" :style="quickBtnStyle">Próxima semana</button>
    <button type="button" @click="$emit('update:modelValue', '')" :style="`${quickBtnStyle} border-color:${!modelValue ? '#7c6fff' : '#26263a'}; color:${!modelValue ? '#b3aaff' : '#c7c5dc'};`">Sem prazo definido</button>
  </div>
</template>
