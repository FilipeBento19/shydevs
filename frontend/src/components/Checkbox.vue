<script setup>
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  ariaLabel: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

function toggle() {
  if (props.disabled) return
  emit('update:modelValue', !props.modelValue)
}
</script>

<template>
  <button type="button" role="checkbox" :aria-checked="modelValue" :aria-label="ariaLabel" :disabled="disabled" @click="toggle"
    :style="{
      width: '17px', height: '17px', flex: 'none', borderRadius: '5px', padding: 0,
      border: `1.5px solid ${modelValue ? '#7c6fff' : '#33313f'}`,
      background: modelValue ? '#7c6fff' : 'transparent',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.35 : 1,
      transition: 'background-color .12s ease, border-color .12s ease',
    }">
    <i v-if="modelValue" class="fi fi-sr-check" style="font-size:9px; color:#0a0a10;" aria-hidden="true"></i>
  </button>
</template>
