<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

function setQuickDate(offsetDays) {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  emit('update:modelValue', d.toISOString().slice(0, 10))
}
</script>

<template>
  <div style="display:flex; gap:7px; flex-wrap:wrap;">
    <input type="date" :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" style="flex:1; min-width:150px; border:1px solid #26263a; background:#0e0e14; border-radius:9px; padding:9px 11px; font-size:12.5px; color:#c7c5dc; outline:none;" />
    <div @click="setQuickDate(0)" style="border:1px solid #26263a; border-radius:9px; padding:9px 12px; font-size:12px; font-weight:600; color:#c7c5dc; cursor:pointer;">Hoje</div>
    <div @click="setQuickDate(1)" style="border:1px solid #26263a; border-radius:9px; padding:9px 12px; font-size:12px; font-weight:600; color:#c7c5dc; cursor:pointer;">Amanhã</div>
    <div @click="setQuickDate(7)" style="border:1px solid #26263a; border-radius:9px; padding:9px 12px; font-size:12px; font-weight:600; color:#c7c5dc; cursor:pointer;">Próxima semana</div>
    <div @click="$emit('update:modelValue', '')" :style="{ border: `1px solid ${!modelValue ? '#7c6fff' : '#26263a'}`, borderRadius: '9px', padding: '9px 12px', fontSize: '12px', fontWeight: '600', color: !modelValue ? '#b3aaff' : '#c7c5dc', cursor: 'pointer' }">Sem prazo definido</div>
  </div>
</template>
