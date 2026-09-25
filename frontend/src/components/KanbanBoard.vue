<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../auth'
import { isLate, formatDue, prioBadge, roleIcon } from '../utils'
import { cardEnter, cardLeave } from '../motion'
import AssigneeAvatar from './AssigneeAvatar.vue'

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  roles: { type: Array, default: () => [] },
  canEdit: { type: Boolean, default: false },
})
const emit = defineEmits(['status-change'])

const router = useRouter()
function openTask(task) {
  if (!auth.isLoggedIn) return
  router.push({ name: 'task', params: { id: task.id } })
}

const COLUMNS = [
  { status: 'Pendente', label: 'Pendente' },
  { status: 'Em andamento', label: 'Em andamento' },
  { status: 'Concluída', label: 'Concluída' },
]

const dragTaskId = ref(null)
const dragOverCol = ref(null)

function roleColor(name) {
  return (props.roles.find((r) => r.name === name) || {}).color || '#9a9ab0'
}

function tasksFor(status) {
  return props.tasks.filter((t) => t.status === status)
}

function onDragStart(task) {
  if (!props.canEdit) return
  dragTaskId.value = task.id
}
function onDragOverCol(status) {
  if (!props.canEdit) return
  dragOverCol.value = status
}
function onDropCol(status) {
  if (!props.canEdit) return
  dragOverCol.value = null
  if (dragTaskId.value == null) return
  const task = props.tasks.find((t) => t.id === dragTaskId.value)
  if (task && task.status !== status) {
    emit('status-change', task, status)
  }
  dragTaskId.value = null
}
</script>

<template>
  <div class="nice-scroll" style="display:grid; grid-template-columns:repeat(3, minmax(220px, 1fr)); gap:12px; overflow-x:auto;">
    <div v-for="col in COLUMNS" :key="col.status"
      @dragover.prevent="onDragOverCol(col.status)"
      @drop="onDropCol(col.status)"
      :style="{ background: dragOverCol === col.status ? 'rgba(124,111,255,.08)' : '#14141d', border: dragOverCol === col.status ? '1px dashed #7c6fff' : '1px solid #22222f', borderRadius: '12px', padding: '10px', minHeight: '160px', transition: 'background .15s, border-color .15s' }">
      <div style="display:flex; align-items:center; justify-content:space-between; padding:4px 4px 10px; font-size:11.5px; font-weight:700; color:#c7c5dc;">
        {{ col.label }}
        <span style="opacity:.6;">{{ tasksFor(col.status).length }}</span>
      </div>

      <TransitionGroup tag="div" @enter="cardEnter" @leave="cardLeave" :css="false" style="display:flex; flex-direction:column; gap:8px;">
        <div v-for="t in tasksFor(col.status)" :key="t.id"
          :draggable="canEdit"
          @dragstart="onDragStart(t)"
          @click="openTask(t)"
          :role="auth.isLoggedIn ? 'button' : undefined" :tabindex="auth.isLoggedIn ? 0 : undefined"
          :aria-label="auth.isLoggedIn ? `Abrir tarefa ${t.code}: ${t.title}, status ${t.status}` : `Tarefa ${t.code}: ${t.title}, status ${t.status} (entre para ver os detalhes)`"
          @keydown.enter="openTask(t)" @keydown.space.prevent="openTask(t)"
          :style="{ background: '#0e0e14', border: '1px solid #22222f', borderRadius: '10px', padding: '10px', cursor: canEdit ? 'grab' : (auth.isLoggedIn ? 'pointer' : 'default') }">
          <div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">
            <span style="font-family:'JetBrains Mono', monospace; font-size:10px; color:#8f8da8;">{{ t.code }}</span>
            <span :style="{ marginLeft: 'auto', ...prioBadge(t.priority), padding: '2px 6px', fontSize: '10px' }">{{ t.priority }}</span>
          </div>
          <div style="font-size:12.5px; font-weight:700; color:#f5f4fb; margin-bottom:6px; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;">{{ t.title }}</div>
          <div style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
            <span :style="{ display: 'inline-flex', alignItems: 'center', gap: '4px', borderRadius: '6px', padding: '3px 7px', fontSize: '10px', fontWeight: '700', background: `color-mix(in oklab, ${roleColor(t.role)} 20%, #14141d)`, color: `color-mix(in oklab, ${roleColor(t.role)} 75%, #fff)` }">
              <i :class="`fi ${roleIcon(t.role)}`" aria-hidden="true"></i>{{ t.role }}
            </span>
            <AssigneeAvatar :photo="t.assignee_photo" :color="roleColor(t.role)" :size="20" :title="t.assignee_name" />
          </div>
          <div :style="{ marginTop: '6px', fontSize: '10.5px', fontWeight: '600', color: isLate(t) ? '#ff8f98' : '#8b899f' }">
            <i class="fi fi-sr-calendar" style="opacity:.7; margin-right:4px;" aria-hidden="true"></i>{{ formatDue(t) }}
          </div>
          <div v-if="t.blocked" :title="`Aguardando ${t.depends_on_code} · ${t.depends_on_title}`" style="margin-top:6px; font-size:10.5px; font-weight:700; color:#ffc46b;"><i class="fi fi-sr-lock" aria-hidden="true"></i> Aguardando {{ t.depends_on_code }}</div>
          <div v-if="t.subtasks_total || t.attachments_total" style="margin-top:6px; font-size:10.5px; color:#8b899f; display:flex; align-items:center; gap:10px;">
            <span v-if="t.subtasks_total"><i class="fi fi-sr-check-circle" style="opacity:.6;" aria-hidden="true"></i> {{ t.subtasks_done }}/{{ t.subtasks_total }}</span>
            <span v-if="t.attachments_total"><i class="fi fi-sr-paperclip" style="opacity:.6;" aria-hidden="true"></i> {{ t.attachments_total }}</span>
          </div>
        </div>
      </TransitionGroup>
      <div v-if="!tasksFor(col.status).length" style="font-size:11.5px; color:#5f5d78; padding:8px 4px;">Nenhuma tarefa.</div>
    </div>
  </div>
</template>
