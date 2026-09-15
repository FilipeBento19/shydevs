<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'
import { vAutogrow } from '../directives/autogrow'
import { playDing } from '../sound'
import { bumpTasks, tasksVersion } from '../taskBus'
import { listEnter, listLeave } from '../motion'
import { roleIcon } from '../utils'
import CustomSelect from '../components/CustomSelect.vue'
import AttachmentsPanel from '../components/AttachmentsPanel.vue'
import CommentsPanel from '../components/CommentsPanel.vue'
import BackButton from '../components/BackButton.vue'
import AssigneeAvatar from '../components/AssigneeAvatar.vue'
import Checkbox from '../components/Checkbox.vue'

const route = useRoute()
const router = useRouter()

const task = ref(null)
const roles = ref([])
const people = ref([])
const subtasks = ref([])
const activities = ref([])
const loading = ref(true)
const notFound = ref(false)

const canEdit = computed(() => !!auth.state.person?.is_admin)
const isOwner = computed(() => !canEdit.value && task.value?.assignee === auth.state.person?.id)
const canEditStatus = computed(() => canEdit.value || isOwner.value)

const form = reactive({
  title: '', description: '', role: '', assignee: null, due_date: '', priority: '', status: '', completion_note: '',
})
const saving = ref(false)
const deleting = ref(false)
const error = ref('')
const confirmDelete = ref(false)
const savedFlash = ref(false)
const noteRequired = computed(() => form.status === 'Concluída' && !form.completion_note.trim())

const newSubtaskTitle = ref('')

async function load() {
  loading.value = true
  notFound.value = false
  error.value = ''
  try {
    const [taskData, roleList, peopleList, activityList] = await Promise.all([
      api.getTask(route.params.id),
      api.getRoles(),
      api.getPeople(),
      api.getActivities(route.params.id),
    ])
    task.value = taskData
    roles.value = roleList
    people.value = peopleList
    activities.value = activityList
    subtasks.value = taskData.subtasks || []
    form.title = taskData.title
    form.description = taskData.description
    form.role = taskData.role
    form.assignee = taskData.assignee
    form.due_date = taskData.due_date || ''
    form.priority = taskData.priority
    form.status = taskData.status
    form.completion_note = taskData.completion_note || ''
  } catch (e) {
    if (e.status === 404) notFound.value = true
    else error.value = 'Não foi possível carregar a tarefa.'
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => route.params.id, load)

// Someone's photo (or other shared data) may have changed elsewhere in the
// app — refresh just the display fields, never the in-progress edit form.
watch(tasksVersion, async () => {
  if (!task.value) return
  try {
    const fresh = await api.getTask(task.value.id)
    task.value.assignee_photo = fresh.assignee_photo
    task.value.assignee_name = fresh.assignee_name
  } catch (e) {
    // ignore — keep showing the last known photo
  }
})

const formPeople = computed(() => people.value.filter((p) => (p.roles || []).includes(form.role)))
const roleOptions = computed(() => roles.value.map((r) => ({ value: r.name, label: r.name, icon: roleIcon(r.name), color: r.color })))
const assigneeOptions = computed(() => [
  { value: null, label: 'Sem responsável' },
  ...formPeople.value.map((p) => ({ value: p.id, label: p.name })),
])
const priorityOptions = [
  { value: 'Baixa', label: 'Baixa', color: '#9a9ab0' },
  { value: 'Média', label: 'Média', color: '#e0a23c' },
  { value: 'Alta', label: 'Alta', color: '#e04f5f' },
]

function roleColor(name) {
  return (roles.value.find((r) => r.name === name) || {}).color || '#9a9ab0'
}

function goBack() {
  router.push({ name: 'board' })
}

async function refreshActivities() {
  try {
    activities.value = await api.getActivities(task.value.id)
  } catch (e) {
    // ignore
  }
}

async function save() {
  if (!canEditStatus.value) return
  error.value = ''
  if (noteRequired.value) {
    error.value = 'Deixe uma nota de conclusão antes de marcar como concluída.'
    return
  }
  saving.value = true
  try {
    const payload = canEdit.value
      ? {
          title: form.title,
          description: form.description,
          role: form.role,
          assignee: form.assignee,
          due_date: form.due_date || null,
          priority: form.priority,
          status: form.status,
          completion_note: form.completion_note,
        }
      : { status: form.status, completion_note: form.completion_note }
    const updated = await api.updateTask(task.value.id, payload)
    const wasCompleted = task.value.status === 'Concluída'
    task.value = updated
    if (updated.status === 'Concluída' && !wasCompleted) playDing()
    bumpTasks()
    activities.value = await api.getActivities(task.value.id)
    savedFlash.value = true
    setTimeout(() => (savedFlash.value = false), 2000)
  } catch (e) {
    error.value = e.message || 'Não foi possível salvar as alterações.'
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!canEdit.value) return
  if (!confirmDelete.value) {
    confirmDelete.value = true
    return
  }
  deleting.value = true
  try {
    await api.deleteTask(task.value.id)
    bumpTasks()
    router.push({ name: 'board' })
  } catch (e) {
    error.value = 'Não foi possível excluir a tarefa.'
    deleting.value = false
  }
}

async function addSubtask() {
  if (!canEdit.value) return
  const title = newSubtaskTitle.value.trim()
  if (!title) return
  try {
    const created = await api.createSubtask({ task: task.value.id, title, order: subtasks.value.length })
    subtasks.value.push(created)
    newSubtaskTitle.value = ''
  } catch (e) {
    error.value = 'Não foi possível adicionar a subtarefa.'
  }
}
async function toggleSubtask(st) {
  if (!canEdit.value) return
  const next = !st.done
  st.done = next
  try {
    await api.updateSubtask(st.id, { done: next })
  } catch (e) {
    st.done = !next
  }
}
async function removeSubtask(st) {
  if (!canEdit.value) return
  try {
    await api.deleteSubtask(st.id)
    subtasks.value = subtasks.value.filter((s) => s.id !== st.id)
  } catch (e) {
    error.value = 'Não foi possível remover a subtarefa.'
  }
}

function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
function setQuickDate(offsetDays) {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  form.due_date = d.toISOString().slice(0, 10)
}
</script>

<template>
  <div style="padding:18px 26px 26px;">
    <BackButton @click="goBack" />

    <div v-if="loading" style="padding:24px; font-size:12.5px; color:#8b899f;">Carregando tarefa…</div>
    <div v-else-if="notFound" style="padding:24px; font-size:12.5px; color:#8b899f;">Essa tarefa não existe (ou foi excluída).</div>

    <template v-else-if="task">
      <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px; flex-wrap:wrap; margin-bottom:18px;">
        <div style="min-width:0;">
          <div style="font-family:'JetBrains Mono', monospace; font-size:12px; color:#8f8da8;">{{ task.code }}</div>
          <div style="font-size:22px; font-weight:800; color:#f5f4fb; letter-spacing:-.02em; display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            {{ task.title }}
            <span v-if="!canEdit && !isOwner" style="font-size:10px; font-weight:700; letter-spacing:.04em; color:#8b899f; background:#1c1c28; border:1px solid #26263a; border-radius:999px; padding:3px 8px;"><i class="fi fi-sr-eye" style="margin-right:4px;" aria-hidden="true"></i>Somente leitura</span>
            <span v-else-if="isOwner" style="font-size:10px; font-weight:700; letter-spacing:.04em; color:#b3aaff; background:rgba(124,111,255,.16); border-radius:999px; padding:3px 8px;"><i class="fi fi-sr-user" style="margin-right:4px;" aria-hidden="true"></i>Sua tarefa</span>
          </div>
        </div>
        <div v-if="canEditStatus" style="display:flex; gap:8px; flex:none;">
          <button v-if="canEdit" @click="remove" :disabled="deleting" :style="{ border: '1px solid rgba(224,79,95,.4)', background: confirmDelete ? 'rgba(224,79,95,.18)' : 'transparent', borderRadius: '9px', padding: '9px 14px', fontSize: '12.5px', fontWeight: '700', color: '#ff8f98', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }">
            <span v-if="deleting" class="btn-spinner" aria-hidden="true"></span>
            <i v-else class="fi fi-sr-trash-can-list" aria-hidden="true"></i> {{ deleting ? 'Excluindo…' : confirmDelete ? 'Confirmar exclusão?' : 'Excluir' }}
          </button>
          <button @click="save" :disabled="saving || noteRequired" :style="{ border: 'none', background: '#7c6fff', color: '#0a0a10', borderRadius: '9px', padding: '9px 16px', fontSize: '12.5px', fontWeight: '700', cursor: noteRequired ? 'not-allowed' : 'pointer', opacity: noteRequired ? 0.6 : 1, display: 'flex', alignItems: 'center', gap: '6px' }">
            <span v-if="saving" class="btn-spinner" aria-hidden="true"></span>{{ saving ? 'Salvando…' : savedFlash ? '✓ Salvo' : canEdit ? 'Salvar alterações' : 'Salvar status' }}
          </button>
        </div>
      </div>

      <div v-if="error" style="margin-bottom:14px; padding:10px 12px; background:rgba(224,79,95,.14); border:1px solid rgba(224,79,95,.35); border-radius:9px; color:#ff8f98; font-size:12px; font-weight:600;">
        {{ error }}
      </div>

      <div style="display:grid; grid-template-columns:minmax(0,1fr) 340px; gap:16px; align-items:start;">
        <!-- left column: details + subtasks -->
        <div style="display:flex; flex-direction:column; gap:16px; min-width:0;">
          <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
            <div style="display:flex; flex-direction:column; gap:12px;">
              <div>
                <label for="task-title" style="display:block; font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Título</label>
                <input id="task-title" v-model="form.title" :disabled="!canEdit" :style="{ width: '100%', boxSizing: 'border-box', border: '1px solid #26263a', background: canEdit ? '#0e0e14' : '#131319', borderRadius: '9px', padding: '10px 12px', fontSize: '13px', color: canEdit ? '#f5f4fb' : '#9a97b8', outline: 'none' }" />
              </div>
              <div>
                <label for="task-desc" style="display:block; font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Descrição — o que precisa ser feito</label>
                <textarea id="task-desc" v-autogrow v-model="form.description" :disabled="!canEdit" rows="3" :style="{ width: '100%', boxSizing: 'border-box', border: '1px solid #26263a', background: canEdit ? '#0e0e14' : '#131319', borderRadius: '9px', padding: '10px 12px', fontSize: '12.5px', color: canEdit ? '#f5f4fb' : '#9a97b8', outline: 'none' }"></textarea>
              </div>

              <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Cargo</div>
                  <CustomSelect v-model="form.role" :options="roleOptions" :disabled="!canEdit" width="100%" label="Cargo" />
                </div>
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Responsável</div>
                  <CustomSelect v-model="form.assignee" :options="assigneeOptions" :disabled="!canEdit" width="100%" label="Responsável" />
                </div>
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px; display:flex; align-items:center; justify-content:space-between;">
                    Prazo
                    <button v-if="canEdit" type="button" @click="form.due_date = ''" style="border:none; background:transparent; color:#7c6fff; font-size:10.5px; font-weight:700; cursor:pointer; padding:0;">Sem prazo</button>
                  </div>
                  <div style="position:relative;">
                    <input type="date" aria-label="Prazo" v-model="form.due_date" :disabled="!canEdit"
                      :style="{ width: '100%', boxSizing: 'border-box', border: '1px solid #26263a', background: '#0e0e14', borderRadius: '9px', padding: '9px 11px', fontSize: '12.5px', color: form.due_date ? '#c7c5dc' : 'transparent', outline: 'none' }" />
                    <span v-if="!form.due_date" style="position:absolute; left:11px; top:50%; transform:translateY(-50%); font-size:12.5px; color:#7f7d97; pointer-events:none;">Sem prazo</span>
                  </div>
                  <div v-if="canEdit" style="display:flex; gap:5px; margin-top:6px; flex-wrap:wrap;">
                    <button type="button" @click="setQuickDate(0)" style="font-size:10.5px; color:#8b899f; cursor:pointer; border:1px solid #26263a; background:transparent; border-radius:6px; padding:3px 7px;">Hoje</button>
                    <button type="button" @click="setQuickDate(1)" style="font-size:10.5px; color:#8b899f; cursor:pointer; border:1px solid #26263a; background:transparent; border-radius:6px; padding:3px 7px;">Amanhã</button>
                    <button type="button" @click="setQuickDate(7)" style="font-size:10.5px; color:#8b899f; cursor:pointer; border:1px solid #26263a; background:transparent; border-radius:6px; padding:3px 7px;">+7 dias</button>
                  </div>
                </div>
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Prioridade</div>
                  <CustomSelect v-model="form.priority" :options="priorityOptions" :disabled="!canEdit" width="100%" label="Prioridade" />
                </div>
              </div>

              <div>
                <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Status</div>
                <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:6px;">
                  <button v-for="s in ['Pendente', 'Em andamento', 'Concluída']" :key="s" type="button" :disabled="!canEditStatus" @click="form.status = s"
                    :style="{ borderRadius: '9px', padding: '9px 0', fontSize: '12px', fontWeight: '700', cursor: canEditStatus ? 'pointer' : 'default', border: `1px solid ${form.status === s ? '#7c6fff' : '#26263a'}`, background: form.status === s ? 'rgba(124,111,255,.16)' : '#0e0e14', color: form.status === s ? '#cfc9ff' : '#c7c5dc' }">
                    {{ s }}
                  </button>
                </div>
              </div>

              <div v-if="canEditStatus || form.completion_note">
                <label for="task-completion-note" style="display:block; font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">
                  Nota de conclusão <span v-if="form.status === 'Concluída'" style="color:#ff8f98;">*</span>
                </label>
                <textarea id="task-completion-note" v-autogrow v-model="form.completion_note" :disabled="!canEditStatus" rows="3"
                  placeholder="ta tudo conforme pedido paizao? se sim da um salve"
                  :style="{ width: '100%', boxSizing: 'border-box', border: `1px solid ${noteRequired ? 'rgba(224,79,95,.5)' : '#26263a'}`, background: canEditStatus ? '#0e0e14' : '#131319', borderRadius: '9px', padding: '10px 12px', fontSize: '12.5px', color: canEditStatus ? '#f5f4fb' : '#9a97b8', outline: 'none' }"></textarea>
                <div v-if="noteRequired" style="font-size:11px; color:#ff8f98; margin-top:4px;">Obrigatória para marcar como concluída.</div>
              </div>
            </div>
          </div>

          <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
            <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:8px; display:flex; align-items:center; justify-content:space-between;">
              Checklist do que fazer
              <span style="font-weight:500; color:#8b899f; font-size:11px;">{{ subtasks.filter(s => s.done).length }}/{{ subtasks.length }}</span>
            </div>
            <TransitionGroup tag="div" @enter="listEnter" @leave="listLeave" :css="false" style="display:flex; flex-direction:column; gap:6px; margin-bottom:8px;">
              <div v-for="(st, i) in subtasks" :key="st.id" :data-index="i" style="display:flex; align-items:center; gap:8px; background:#0e0e14; border:1px solid #22222f; border-radius:8px; padding:8px 10px;">
                <Checkbox :model-value="st.done" :disabled="!canEdit" @update:model-value="toggleSubtask(st)" :aria-label="`Marcar etapa: ${st.title}`" />
                <span :style="{ flex: 1, fontSize: '12.5px', color: st.done ? '#8f8da8' : '#e4e2f1', textDecoration: st.done ? 'line-through' : 'none' }">{{ st.title }}</span>
                <button v-if="canEdit" type="button" @click="removeSubtask(st)" :aria-label="`Remover etapa: ${st.title}`" style="border:none; background:transparent; color:#8f8da8; cursor:pointer; font-size:12px;"><i class="fi fi-sr-cross-small" aria-hidden="true"></i></button>
              </div>
            </TransitionGroup>
            <div v-if="!subtasks.length" style="font-size:12px; color:#8f8da8; margin-bottom:8px;">Nenhuma etapa cadastrada ainda.</div>
            <div v-if="canEdit" style="display:flex; gap:6px;">
              <input v-model="newSubtaskTitle" @keyup.enter="addSubtask" placeholder="Adicionar etapa…" style="flex:1; box-sizing:border-box; border:1px solid #26263a; background:#0e0e14; border-radius:8px; padding:8px 10px; font-size:12px; color:#f5f4fb; outline:none;" />
              <button type="button" @click="addSubtask" style="border:1px solid #26263a; background:#0e0e14; border-radius:8px; padding:8px 12px; font-size:12px; font-weight:700; color:#c7c5dc; cursor:pointer;"><i class="fi fi-sr-plus-small" aria-hidden="true"></i></button>
            </div>
          </div>
        </div>

        <!-- right column: assignee card, attachments, history -->
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px; display:flex; align-items:center; gap:10px;">
            <AssigneeAvatar :photo="task.assignee_photo" :color="roleColor(task.role)" :size="36" />
            <div style="min-width:0;">
              <div style="font-size:12.5px; font-weight:700; color:#f5f4fb; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ task.assignee_name || 'Sem responsável' }}</div>
              <div style="font-size:11px; color:#8b899f; display:flex; align-items:center; gap:4px;"><i :class="`fi ${roleIcon(task.role)}`" aria-hidden="true"></i>{{ task.role }}</div>
            </div>
          </div>

          <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
            <AttachmentsPanel :task-id="task.id" @changed="refreshActivities" />
          </div>

          <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
            <CommentsPanel :task-id="task.id" @changed="refreshActivities" />
          </div>

          <div v-if="activities.length" style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
            <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:8px;">Histórico</div>
            <TransitionGroup tag="div" @enter="listEnter" :css="false" class="nice-scroll" style="display:flex; flex-direction:column; gap:6px; max-height:220px; overflow-y:auto; padding-right:4px;">
              <div v-for="(a, i) in activities" :key="a.id" :data-index="i" style="font-size:11.5px; color:#9a97b8; display:flex; gap:8px;">
                <i class="fi fi-sr-clock" style="opacity:.6; margin-top:2px;" aria-hidden="true"></i>
                <span>{{ a.message }} <span style="color:#5f5d78;">· {{ fmtDate(a.created_at) }}</span></span>
              </div>
            </TransitionGroup>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
