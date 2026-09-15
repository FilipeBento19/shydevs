<script setup>
import { computed } from 'vue'

const props = defineProps({
  photo: { type: String, default: null },
  color: { type: String, default: '#9a9ab0' },
  size: { type: Number, default: 24 },
})

const wrapperStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  flex: 'none',
  borderRadius: '50%',
  overflow: 'hidden',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: props.photo ? '#1c1c28' : props.color,
}))

const iconStyle = computed(() => ({
  fontSize: `${Math.round(props.size * 0.5)}px`,
  color: '#0a0a10',
}))
</script>

<template>
  <div :style="wrapperStyle">
    <img v-if="photo" :src="photo" alt="" style="width:100%; height:100%; object-fit:cover; display:block;" />
    <i v-else class="fi fi-sr-user" :style="iconStyle" aria-hidden="true"></i>
  </div>
</template>
