<script setup>
import { useRouter } from 'vue-router'
import { listEnter, listLeave } from '../motion'
import { auth } from '../auth'
import { isLate, formatDue, prioBadge, statusBadge, roleIcon } from '../utils'
import mascot from '../assets/mascot.png'
import AssigneeAvatar from './AssigneeAvatar.vue'
import Checkbox from './Checkbox.vue'

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  roles: { type: Array, default: () => [] },
  canEdit: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  selectedIds: { type: Array, default: () => [] },
  allSelected: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle-select', 'toggle-select-all'])

const router = useRouter()

function roleColor(name) {
  return (props.roles.find((r) => r.name === name) || {}).color || '#9a9ab0'
}
function isSelected(id) {
  return props.selectedIds.includes(id)
}
function canSelect(task) {
  return props.canEdit || task.assignee === auth.state.person?.id
}
function openTask(task) {
  router.push({ name: 'task', params: { id: task.id } })
}
</script>

<template>
  <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; overflow:hidden;">
    <div class="nice-scroll" style="overflow-x:auto;">
      <div style="min-width:940px;">
        <div style="display:grid; grid-template-columns:34px minmax(0,1fr) 128px 158px 150px 96px 126px; gap:10px; padding:11px 14px; background:#101017; border-bottom:1px solid #1f1f2b; font-size:10.5px; font-weight:700; letter-spacing:.06em; color:#8b899f;">
          <div v-if="auth.isLoggedIn">
            <Checkbox :model-value="allSelected" @update:model-value="$emit('toggle-select-all')" aria-label="Selecionar todas as tarefas" />
          </div>
          <div>TAREFA &amp; DESCRIÇÃO</div><div>CARGO</div><div>RESPONSÁVEL</div><div>PRAZO</div><div>PRIORIDADE</div><div>STATUS</div>
        </div>

        <div v-if="loading" style="padding:24px 14px; font-size:12.5px; color:#8b899f; display:flex; align-items:center; gap:8px;"><i class="fi fi-sr-hourglass" aria-hidden="true"></i>Carregando tarefas…</div>
        <div v-else-if="tasks.length === 0" style="padding:28px 14px; font-size:12.5px; color:#8b899f; display:flex; align-items:center; gap:14px;">
          <img :src="mascot" alt="" style="width:44px; height:44px; object-fit:contain; opacity:.85;" />
          <span>Nenhuma tarefa encontrada com estes filtros.</span>
        </div>

        <TransitionGroup v-else tag="div" @enter="listEnter" @leave="listLeave" :css="false">
          <div v-for="(t, i) in tasks" :key="t.id" :data-index="i" @click="openTask(t)"
            role="button" tabindex="0" :aria-label="`Abrir tarefa ${t.code}: ${t.title}`"
            @keydown.enter="openTask(t)" @keydown.space.prevent="openTask(t)"
            :style="{ display: 'grid', gridTemplateColumns: '34px minmax(0,1fr) 128px 158px 150px 96px 126px', gap: '10px', padding: '13px 14px', borderBottom: '1px solid #1a1a25', alignItems: 'center', cursor: 'pointer', background: isSelected(t.id) ? 'rgba(124,111,255,.06)' : 'transparent' }">
            <div v-if="auth.isLoggedIn" @click.stop>
              <Checkbox :model-value="isSelected(t.id)" :disabled="!canSelect(t)" @update:model-value="$emit('toggle-select', t.id)"
                :aria-label="canSelect(t) ? `Selecionar tarefa ${t.code}` : `Tarefa ${t.code} não é sua`" />
            </div>
            <div style="min-width:0;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-family:'JetBrains Mono', monospace; font-size:10.5px; color:#8f8da8;">{{ t.code }}</span>
                <span style="font-size:13px; font-weight:700; color:#f5f4fb; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ t.title }}</span>
                <span v-if="t.subtasks_total" style="font-size:10.5px; color:#8b899f; flex:none;"><i class="fi fi-sr-check-circle" style="opacity:.6;" aria-hidden="true"></i> {{ t.subtasks_done }}/{{ t.subtasks_total }}</span>
                <span v-if="t.attachments_total" style="font-size:10.5px; color:#8b899f; flex:none;"><i class="fi fi-sr-paperclip" style="opacity:.6;" aria-hidden="true"></i> {{ t.attachments_total }}</span>
              </div>
              <div style="font-size:11.5px; color:#8b899f; margin-top:3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ t.description }}</div>
            </div>
            <div>
              <span :style="{ display: 'inline-flex', alignItems: 'center', gap: '5px', borderRadius: '6px', padding: '4px 8px', fontSize: '11px', fontWeight: '700', background: `color-mix(in oklab, ${roleColor(t.role)} 20%, #14141d)`, color: `color-mix(in oklab, ${roleColor(t.role)} 75%, #fff)` }">
                <i :class="`fi ${roleIcon(t.role)}`" aria-hidden="true"></i>{{ t.role }}
              </span>
            </div>
            <div style="display:flex; align-items:center; gap:8px; min-width:0;">
              <AssigneeAvatar :photo="t.assignee_photo" :color="roleColor(t.role)" :size="24" />
              <span style="font-size:12px; font-weight:600; color:#d6d4e6; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ t.assignee_name || 'Sem responsável' }}</span>
            </div>
            <div :style="{ fontSize: '11.5px', fontWeight: '600', color: isLate(t) ? '#ff8f98' : '#9a97b8', display: 'flex', alignItems: 'center', gap: '6px' }">
              <i class="fi fi-sr-calendar" style="font-size:10.5px; opacity:.75;" aria-hidden="true"></i>{{ formatDue(t) }}
            </div>
            <div><span :style="prioBadge(t.priority)">{{ t.priority }}</span></div>
            <div><span :style="statusBadge(t.status)">{{ t.status }}</span></div>
          </div>
        </TransitionGroup>
      </div>
    </div>
  </div>
</template>
