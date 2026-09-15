<script setup>
defineProps({
  modelValue: { type: String, default: 'Alta' },
})
defineEmits(['update:modelValue'])

const OPTIONS = [
  { value: 'Baixa', color: '#9a9ab0' },
  { value: 'Média', color: '#e0a23c' },
  { value: 'Alta', color: '#e04f5f' },
]
</script>

<template>
  <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:6px;">
    <button v-for="p in OPTIONS" :key="p.value" type="button" @click="$emit('update:modelValue', p.value)"
      :style="{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '7px', borderRadius: '9px', padding: '9px 0', fontSize: '12px', fontWeight: '700', cursor: 'pointer', border: `1px solid ${modelValue === p.value ? p.color : '#26263a'}`, background: modelValue === p.value ? `color-mix(in oklab, ${p.color} 16%, #14141d)` : '#0e0e14', color: '#c7c5dc' }">
      <span :style="{ width: '7px', height: '7px', borderRadius: '50%', background: p.color }"></span>{{ p.value }}
    </button>
  </div>
</template>
