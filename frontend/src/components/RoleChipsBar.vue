<script setup>
import { gsap, reduceMotion } from '../motion'
import { chipStyle, roleIcon } from '../utils'
import { auth } from '../auth'

const props = defineProps({
  roles: { type: Array, default: () => [] },
  role: { type: String, required: true },
  totalCount: { type: Number, default: 0 },
  counts: { type: Object, default: () => ({}) },
  myTasksOnly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:role', 'update:myTasksOnly'])

const ACCENT = '#7c6fff'

function bounce(e) {
  if (reduceMotion) return
  gsap.fromTo(e.currentTarget, { scale: 0.92 }, { scale: 1, duration: 0.35, ease: 'back.out(4)' })
}
</script>

<template>
  <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
    <button @click="(e) => { bounce(e); $emit('update:role', 'Todos') }" :style="chipStyle(role === 'Todos', ACCENT)">
      <i class="fi fi-sr-users" aria-hidden="true"></i>Todos os cargos <span style="opacity:.6;">{{ totalCount }}</span>
    </button>
    <button v-for="r in roles" :key="r.name" @click="(e) => { bounce(e); $emit('update:role', r.name) }" :style="chipStyle(role === r.name, r.color)">
      <i :class="`fi ${roleIcon(r.name)}`" aria-hidden="true"></i>
      {{ r.name }} <span style="opacity:.6;">{{ counts[r.name] || 0 }}</span>
    </button>
    <button v-if="auth.isLoggedIn" @click="(e) => { bounce(e); $emit('update:myTasksOnly', !myTasksOnly) }" :style="chipStyle(myTasksOnly, '#3fcf8e')">
      <i class="fi fi-sr-user" aria-hidden="true"></i>Minhas tarefas
    </button>
  </div>
</template>
