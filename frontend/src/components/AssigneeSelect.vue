<script setup>
import CustomSelect from './CustomSelect.vue'

defineProps({
  modelValue: { type: [Number, String, null], default: null },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Selecione uma pessoa' },
  disabled: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <div>
    <div style="display:flex; justify-content:space-between; align-items:baseline;">
      <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Pessoa responsável <span style="color:#ff8f98;">*</span></div>
      <div style="font-size:11px; color:#8b899f;">{{ options.length }} disponíveis neste cargo</div>
    </div>
    <CustomSelect
      :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)"
      :options="options" :placeholder="placeholder" :disabled="disabled" width="100%"
      label="Pessoa responsável"
    />
  </div>
</template>
