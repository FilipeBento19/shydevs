<script setup>
// Pick the people for a group task: tap a cargo to add everyone with it, and/or tap people one by one.
import { computed } from 'vue'
import { roleIcon } from '../utils'
import AssigneeAvatar from './AssigneeAvatar.vue'

const props = defineProps({
  people: { type: Array, default: () => [] },
  roles: { type: Array, default: () => [] },
  modelValue: { type: Array, default: () => [] }, // person ids
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const selected = computed(() => new Set(props.modelValue))
const roleRows = computed(() => props.roles
  .map((r) => {
    const ids = props.people.filter((p) => (p.roles || []).includes(r.name)).map((p) => p.id)
    const picked = ids.filter((id) => selected.value.has(id)).length
    return { ...r, ids, state: !ids.length ? 'empty' : picked === ids.length ? 'all' : picked ? 'some' : 'none' }
  })
  .filter((r) => r.ids.length))

function toggleRole(row) {
  if (props.disabled) return
  const next = new Set(props.modelValue)
  if (row.state === 'all') row.ids.forEach((id) => next.delete(id))
  else row.ids.forEach((id) => next.add(id))
  emit('update:modelValue', [...next])
}
function togglePerson(id) {
  if (props.disabled) return
  const next = new Set(props.modelValue)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  emit('update:modelValue', [...next])
}
function personColor(p) {
  return props.roles.find((r) => (p.roles || []).includes(r.name))?.color || '#9a9ab0'
}
</script>

<template>
  <div class="gp">
    <div class="gp-label">Cargos <span>toque para adicionar todos os desse cargo</span></div>
    <div class="gp-row">
      <button v-for="r in roleRows" :key="r.name" type="button" class="gp-chip" :class="r.state" :disabled="disabled"
        :aria-pressed="r.state === 'all'" :style="{ '--c': r.color }" @click="toggleRole(r)">
        <i :class="`fi ${roleIcon(r.name)}`" aria-hidden="true"></i>{{ r.name }}<b>{{ r.ids.length }}</b>
      </button>
    </div>

    <div class="gp-label" style="margin-top:12px;">Pessoas</div>
    <div class="gp-row">
      <button v-for="p in people" :key="p.id" type="button" class="gp-chip person" :class="{ all: selected.has(p.id) }" :disabled="disabled"
        :aria-pressed="selected.has(p.id)" :style="{ '--c': personColor(p) }" @click="togglePerson(p.id)">
        <AssigneeAvatar :photo="p.photo" :color="personColor(p)" :size="20" />{{ p.name }}
        <i v-if="selected.has(p.id)" class="fi fi-sr-check gp-check" aria-hidden="true"></i>
      </button>
      <span v-if="!people.length" class="gp-empty">Nenhuma pessoa cadastrada.</span>
    </div>

    <div class="gp-count" :class="{ warn: modelValue.length < 2 }" role="status">
      {{ modelValue.length }} {{ modelValue.length === 1 ? 'pessoa selecionada' : 'pessoas selecionadas' }}
      <span v-if="modelValue.length < 2"> · escolha pelo menos 2</span>
    </div>
  </div>
</template>

<style scoped>
.gp-label { font-size: 11px; font-weight: 700; color: #9a97b8; margin-bottom: 6px; }
.gp-label span { font-weight: 500; color: #65637a; margin-left: 4px; }
.gp-row { display: flex; flex-wrap: wrap; gap: 6px; }
.gp-chip { --c: #7c6fff; display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border-radius: 999px; border: 1px solid #26263a; background: #0e0e14; color: #9a97b8; font-size: 11.5px; font-weight: 700; cursor: pointer; transition: border-color .12s ease, background-color .12s ease, color .12s ease; }
.gp-chip.person { padding: 4px 12px 4px 5px; }
.gp-chip b { font-size: 10px; font-weight: 800; opacity: .6; }
.gp-chip.some { border-color: color-mix(in oklab, var(--c) 55%, #26263a); color: #c7c5dc; }
.gp-chip.all { border-color: var(--c); background: color-mix(in oklab, var(--c) 18%, #14141d); color: #f5f4fb; }
.gp-chip:hover:not(:disabled) { border-color: var(--c); }
.gp-chip:focus-visible { outline: 2px solid #7c6fff; outline-offset: 1px; }
.gp-chip:disabled { cursor: default; opacity: .7; }
.gp-check { font-size: 9px; color: var(--c); }
.gp-empty { font-size: 12px; color: #65637a; }
.gp-count { margin-top: 10px; font-size: 11.5px; font-weight: 700; color: #b3aaff; }
.gp-count.warn { color: #ffc46b; }
.gp-count span { font-weight: 500; }
</style>
