<script setup>
defineProps({
  label: { type: String, default: 'Voltar ao quadro' },
})
defineEmits(['click'])
</script>

<template>
  <button type="button" class="back-btn" @click="$emit('click')"
    style="border:1px solid #26263a; background:#14141d; color:#c7c5dc; font-size:12px; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:7px; padding:8px 14px; border-radius:9px; margin-bottom:16px;">
    <i class="fi fi-sr-arrow-left" aria-hidden="true"></i>{{ label }}
  </button>
</template>

<style scoped>
.back-btn:hover {
  border-color: #7c6fff;
  color: #cfc9ff;
}
</style>
