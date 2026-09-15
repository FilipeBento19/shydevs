<script setup>
import { roleIcon } from '../utils'

defineProps({
  roles: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <div style="display:flex; gap:6px; flex-wrap:wrap;">
    <button v-for="r in roles" :key="r.name" type="button" @click="$emit('update:modelValue', r.name)"
      :style="{ display: 'inline-flex', alignItems: 'center', gap: '6px', borderRadius: '999px', padding: '7px 12px', fontSize: '11.5px', fontWeight: '700', cursor: 'pointer', border: `1px solid ${modelValue === r.name ? r.color : '#26263a'}`, background: modelValue === r.name ? `color-mix(in oklab, ${r.color} 18%, #14141d)` : '#0e0e14', color: modelValue === r.name ? '#f5f4fb' : '#9a97b8' }">
      <i :class="`fi ${roleIcon(r.name)}`"></i>{{ r.name }}
    </button>
  </div>
</template>
