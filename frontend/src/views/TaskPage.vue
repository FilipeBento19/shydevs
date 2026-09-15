<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'
import { playDing } from '../sound'
import { bumpTasks } from '../taskBus'
import { listEnter, listLeave } from '../motion'
import { roleIcon, initials } from '../utils'
import CustomSelect from '../components/CustomSelect.vue'
import AttachmentsPanel from '../components/AttachmentsPanel.vue'
import BackButton from '../components/BackButton.vue'

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

const form = reactive({
  title: '', description: '', role: '', assignee: null, due_date: '', priority: '', status: '',
})
const saving = ref(false)
const deleting = ref(false)
const error = ref('')
const confirmDelete = ref(false)
const savedFlash = ref(false)

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
  } catch (e) {
    if (e.status === 404) notFound.value = true
    else error.value = 'Não foi possível carregar a tarefa.'
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => route.params.id, load)

const formPeople = computed(() => people.value.filter((p) => p.role === form.role))
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
  if (!canEdit.value) return
  error.value = ''
  saving.value = true
  try {
    const updated = await api.updateTask(task.value.id, {
      title: form.title,
      description: form.description,
      role: form.role,
      assignee: form.assignee,
      due_date: form.due_date || null,
      priority: form.priority,
      status: form.status,
    })
    const wasCompleted = task.value.status === 'Concluída'
    task.value = updated
    if (updated.status === 'Concluída' && !wasCompleted) playDing()
    bumpTasks()
    activities.value = await api.getActivities(task.value.id)
    savedFlash.value = true
    setTimeout(() => (savedFlash.value = false), 2000)
  } catch (e) {
    error.value = 'Não foi possível salvar as alterações.'
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
          <div style="font-family:'JetBrains Mono', monospace; font-size:12px; color:#6f6d87;">{{ task.code }}</div>
          <div style="font-size:22px; font-weight:800; color:#f5f4fb; letter-spacing:-.02em; display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            {{ task.title }}
            <span v-if="!canEdit" style="font-size:10px; font-weight:700; letter-spacing:.04em; color:#8b899f; background:#1c1c28; border:1px solid #26263a; border-radius:999px; padding:3px 8px;"><i class="fi fi-sr-eye" style="margin-right:4px;"></i>Somente leitura</span>
          </div>
        </div>
        <div v-if="canEdit" style="display:flex; gap:8px; flex:none;">
          <button @click="remove" :disabled="deleting" :style="{ border: '1px solid rgba(224,79,95,.4)', background: confirmDelete ? 'rgba(224,79,95,.18)' : 'transparent', borderRadius: '9px', padding: '9px 14px', fontSize: '12.5px', fontWeight: '700', color: '#ff8f98', cursor: 'pointer' }">
            <i class="fi fi-sr-trash-can-list"></i> {{ confirmDelete ? 'Confirmar exclusão?' : 'Excluir' }}
          </button>
          <button @click="save" :disabled="saving" style="border:none; background:#7c6fff; color:#0a0a10; border-radius:9px; padding:9px 16px; font-size:12.5px; font-weight:700; cursor:pointer;">
            {{ saving ? 'Salvando…' : savedFlash ? '✓ Salvo' : 'Salvar alterações' }}
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
                <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Título</div>
                <input v-model="form.title" :disabled="!canEdit" :style="{ width: '100%', boxSizing: 'border-box', border: '1px solid #26263a', background: canEdit ? '#0e0e14' : '#131319', borderRadius: '9px', padding: '10px 12px', fontSize: '13px', color: canEdit ? '#f5f4fb' : '#9a97b8', outline: 'none' }" />
              </div>
              <div>
                <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Descrição — o que precisa ser feito</div>
                <textarea v-model="form.description" :disabled="!canEdit" rows="3" :style="{ width: '100%', boxSizing: 'border-box', border: '1px solid #26263a', background: canEdit ? '#0e0e14' : '#131319', borderRadius: '9px', padding: '10px 12px', fontSize: '12.5px', color: canEdit ? '#f5f4fb' : '#9a97b8', outline: 'none', resize: 'vertical' }"></textarea>
              </div>

              <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Cargo</div>
                  <CustomSelect v-model="form.role" :options="roleOptions" :disabled="!canEdit" width="100%" />
                </div>
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Responsável</div>
                  <CustomSelect v-model="form.assignee" :options="assigneeOptions" :disabled="!canEdit" width="100%" />
                </div>
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px; display:flex; align-items:center; justify-content:space-between;">
                    Prazo
                    <button v-if="canEdit" type="button" @click="form.due_date = ''" style="border:none; background:transparent; color:#7c6fff; font-size:10.5px; font-weight:700; cursor:pointer; padding:0;">Sem prazo</button>
                  </div>
                  <input type="date" v-model="form.due_date" :disabled="!canEdit" style="width:100%; box-sizing:border-box; border:1px solid #26263a; background:#0e0e14; border-radius:9px; padding:9px 11px; font-size:12.5px; color:#c7c5dc; outline:none;" />
                  <div v-if="canEdit" style="display:flex; gap:5px; margin-top:6px; flex-wrap:wrap;">
                    <span @click="setQuickDate(0)" style="font-size:10.5px; color:#8b899f; cursor:pointer; border:1px solid #26263a; border-radius:6px; padding:3px 7px;">Hoje</span>
                    <span @click="setQuickDate(1)" style="font-size:10.5px; color:#8b899f; cursor:pointer; border:1px solid #26263a; border-radius:6px; padding:3px 7px;">Amanhã</span>
                    <span @click="setQuickDate(7)" style="font-size:10.5px; color:#8b899f; cursor:pointer; border:1px solid #26263a; border-radius:6px; padding:3px 7px;">+7 dias</span>
                  </div>
                </div>
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Prioridade</div>
                  <CustomSelect v-model="form.priority" :options="priorityOptions" :disabled="!canEdit" width="100%" />
                </div>
              </div>

              <div>
                <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Status</div>
                <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:6px;">
                  <button v-for="s in ['Pendente', 'Em andamento', 'Concluída']" :key="s" type="button" :disabled="!canEdit" @click="form.status = s"
                    :style="{ borderRadius: '9px', padding: '9px 0', fontSize: '12px', fontWeight: '700', cursor: canEdit ? 'pointer' : 'default', border: `1px solid ${form.status === s ? '#7c6fff' : '#26263a'}`, background: form.status === s ? 'rgba(124,111,255,.16)' : '#0e0e14', color: form.status === s ? '#cfc9ff' : '#c7c5dc' }">
                    {{ s }}
                  </button>
                </div>
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
                <input type="checkbox" :checked="st.done" :disabled="!canEdit" @change="toggleSubtask(st)" style="width:14px; height:14px; accent-color:#7c6fff; cursor:pointer;" />
                <span :style="{ flex: 1, fontSize: '12.5px', color: st.done ? '#6f6d87' : '#e4e2f1', textDecoration: st.done ? 'line-through' : 'none' }">{{ st.title }}</span>
                <button v-if="canEdit" type="button" @click="removeSubtask(st)" style="border:none; background:transparent; color:#6f6d87; cursor:pointer; font-size:12px;"><i class="fi fi-sr-cross-small"></i></button>
              </div>
            </TransitionGroup>
            <div v-if="!subtasks.length" style="font-size:12px; color:#6f6d87; margin-bottom:8px;">Nenhuma etapa cadastrada ainda.</div>
            <div v-if="canEdit" style="display:flex; gap:6px;">
              <input v-model="newSubtaskTitle" @keyup.enter="addSubtask" placeholder="Adicionar etapa…" style="flex:1; box-sizing:border-box; border:1px solid #26263a; background:#0e0e14; border-radius:8px; padding:8px 10px; font-size:12px; color:#f5f4fb; outline:none;" />
              <button type="button" @click="addSubtask" style="border:1px solid #26263a; background:#0e0e14; border-radius:8px; padding:8px 12px; font-size:12px; font-weight:700; color:#c7c5dc; cursor:pointer;"><i class="fi fi-sr-plus-small"></i></button>
            </div>
          </div>
        </div>

        <!-- right column: assignee card, attachments, history -->
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px; display:flex; align-items:center; gap:10px;">
            <span :style="{ width: '36px', height: '36px', flex: 'none', borderRadius: '50%', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: '800', color: '#0a0a10', background: roleColor(task.role) }">{{ initials(task.assignee_name) }}</span>
            <div style="min-width:0;">
              <div style="font-size:12.5px; font-weight:700; color:#f5f4fb; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ task.assignee_name || 'Sem responsável' }}</div>
              <div style="font-size:11px; color:#8b899f; display:flex; align-items:center; gap:4px;"><i :class="`fi ${roleIcon(task.role)}`"></i>{{ task.role }}</div>
            </div>
          </div>

          <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
            <AttachmentsPanel :task-id="task.id" @changed="refreshActivities" />
          </div>

          <div v-if="activities.length" style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
            <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:8px;">Histórico</div>
            <TransitionGroup tag="div" @enter="listEnter" :css="false" style="display:flex; flex-direction:column; gap:6px; max-height:220px; overflow-y:auto;">
              <div v-for="(a, i) in activities" :key="a.id" :data-index="i" style="font-size:11.5px; color:#9a97b8; display:flex; gap:8px;">
                <i class="fi fi-sr-clock" style="opacity:.6; margin-top:2px;"></i>
                <span>{{ a.message }} <span style="color:#5f5d78;">· {{ fmtDate(a.created_at) }}</span></span>
              </div>
            </TransitionGroup>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
