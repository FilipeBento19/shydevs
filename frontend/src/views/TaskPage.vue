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
import GroupPicker from '../components/GroupPicker.vue'
import Checkbox from '../components/Checkbox.vue'
import SlidingTabs from '../components/SlidingTabs.vue'
import ReferencesPanel from '../components/ReferencesPanel.vue'

const route = useRoute()
const router = useRouter()

const task = ref(null)
const roles = ref([])
const people = ref([])
const allTasks = ref([])
const subtasks = ref([])
const activities = ref([])
const loading = ref(true)
const notFound = ref(false)

const canEdit = computed(() => !!auth.state.person?.is_admin)
const isOwner = computed(() => {
  const me = auth.state.person?.id
  return !canEdit.value && (task.value?.assignee === me || !!task.value?.participants?.includes(me))
})
const canEditStatus = computed(() => canEdit.value || isOwner.value)
const canToggleChecklist = computed(() => canEdit.value || isOwner.value)

const form = reactive({
  title: '', description: '', role: '', assignee: null, due_date: '', priority: '', status: '', completion_note: '', depends_on: null, kind: 'solo', participants: [],
})
const saving = ref(false)
const deleting = ref(false)
const error = ref('')
const confirmDelete = ref(false)
const savedFlash = ref(false)
const allStepsDone = computed(() => subtasks.value.length > 0 && subtasks.value.every((st) => st.done))
const noteRequired = computed(() => form.status === 'Concluída' && !form.completion_note.trim())

const newSubtaskTitle = ref('')

// "Detalhes" is the form + checklist + side panels; "Referências" swaps them
// for a full-width gallery, since reference media needs room to be looked at.
const activeTab = ref('details')
const referencesTotal = ref(0)
const taskTabs = computed(() => [
  { key: 'details', label: 'Detalhes', icon: 'fi-sr-file' },
  { key: 'references', label: 'Referências', icon: 'fi-sr-picture', count: referencesTotal.value },
])

async function load() {
  loading.value = true
  notFound.value = false
  error.value = ''
  try {
    const [taskData, roleList, peopleList, activityList, taskList] = await Promise.all([
      api.getTask(route.params.id),
      api.getRoles(),
      api.getPeople(),
      api.getActivities(route.params.id),
      api.getTasks(),
    ])
    allTasks.value = taskList
    task.value = taskData
    roles.value = roleList
    people.value = peopleList
    activities.value = activityList
    subtasks.value = taskData.subtasks || []
    referencesTotal.value = taskData.references_total || 0
    form.title = taskData.title
    form.description = taskData.description
    form.role = taskData.role
    form.assignee = taskData.assignee
    form.due_date = taskData.due_date || ''
    form.priority = taskData.priority
    form.status = taskData.status
    form.depends_on = taskData.depends_on
    form.kind = taskData.kind || 'solo'
    form.participants = [...(taskData.participants || [])]
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
const dependencyOptions = computed(() => [
  { value: null, label: 'Nenhuma' },
  ...allTasks.value.filter((t) => t.id !== task.value?.id).map((t) => ({ value: t.id, label: `${t.code} · ${t.title}` })),
])
const blocked = computed(() => !!task.value?.blocked)
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
  if (canEdit.value && form.kind === 'group' && form.participants.length < 2) {
    error.value = 'Uma tarefa em grupo precisa de pelo menos 2 pessoas.'
    return
  }
  // Every checklist step is done: the work is finished, so saving means closing it out.
  if (allStepsDone.value && form.status !== 'Concluída') {
    error.value = 'Todas as etapas do checklist foram feitas. Marque a tarefa como Concluída e preencha a nota de conclusão para salvar.'
    return
  }
  if (noteRequired.value || (allStepsDone.value && !form.completion_note.trim())) {
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
          depends_on: form.depends_on,
          kind: form.kind,
          participants: form.kind === 'group' ? form.participants : [],
          ...(form.kind === 'group' ? { assignee: form.participants.includes(form.assignee) ? form.assignee : form.participants[0] } : {}),
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
// In a group task everyone does the whole checklist: a member ticks for themselves,
// an admin outside the group for everyone. `st.done` then means "everyone finished".
const isGroup = computed(() => task.value?.kind === 'group')
const isMember = computed(() => !!task.value?.participants?.includes(auth.state.person?.id))
function stepChecked(st) {
  return isGroup.value && isMember.value ? st.my_done : st.done
}
const groupProgress = computed(() => (task.value?.participants_info || []).map((p) => ({
  ...p,
  done: subtasks.value.filter((s) => (s.done_by || []).includes(p.id)).length,
  total: subtasks.value.length,
})))
// ---- turn order (group tasks): who has to finish a step before whom ----
const order = computed(() => task.value?.participant_order || [])
const myPos = computed(() => order.value.indexOf(auth.state.person?.id))
const nameOf = (id) => task.value?.participants_info?.find((p) => p.id === id)?.name || '?'
// Why this step can't be ticked (or unticked) by me right now, or ''.
function lockReason(st) {
  if (!isGroup.value || !isMember.value || !order.value.length || myPos.value < 0) return ''
  const by = st.done_by || []
  if (!st.my_done && myPos.value > 0 && !by.includes(order.value[myPos.value - 1])) return `Aguardando ${nameOf(order.value[myPos.value - 1])} concluir esta etapa`
  if (st.my_done && order.value.slice(myPos.value + 1).some((id) => by.includes(id))) return 'Quem vem depois de você já concluiu esta etapa'
  return ''
}

const stepMenuOpen = ref(false)
const orderEditing = ref(false)
const orderDraft = ref([])
const orderSaving = ref(false)
function startOrder() {
  stepMenuOpen.value = false
  orderDraft.value = order.value.length ? [...order.value] : (task.value.participants_info || []).map((p) => p.id)
  orderEditing.value = true
}
function moveDraft(index, delta) {
  const to = index + delta
  if (to < 0 || to >= orderDraft.value.length) return
  const next = [...orderDraft.value]
  ;[next[index], next[to]] = [next[to], next[index]]
  orderDraft.value = next
}
async function saveOrder(ids) {
  orderSaving.value = true
  try {
    const updated = await api.updateTask(task.value.id, { participant_order: ids })
    task.value.participant_order = updated.participant_order
    task.value.participants_info = updated.participants_info
    task.value.participants_progress = updated.participants_progress
    orderEditing.value = false
    stepMenuOpen.value = false
    refreshActivities()
  } catch (e) {
    error.value = e.message || 'Não foi possível salvar a ordem.'
  } finally {
    orderSaving.value = false
  }
}
function clearOrder() {
  saveOrder([])
}

function finishers(st) {
  return (task.value?.participants_info || []).filter((p) => (st.done_by || []).includes(p.id))
}

async function toggleSubtask(st) {
  if (!canToggleChecklist.value || lockReason(st)) return
  const next = !stepChecked(st)
  const snapshot = { done: st.done, my_done: st.my_done, done_by: st.done_by }
  if (isGroup.value) {
    if (isMember.value) st.my_done = next
  } else {
    st.done = next
  }
  try {
    const updated = await api.updateSubtask(st.id, { done: next })
    if (isGroup.value) Object.assign(st, { done: updated.done, my_done: updated.my_done, done_by: updated.done_by })
    // The server moves a pending task to "Em andamento" on the first checked step.
    if (next && task.value.status === 'Pendente') {
      task.value.status = 'Em andamento'
      form.status = 'Em andamento'
    }
  } catch (e) {
    Object.assign(st, snapshot)
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

      <div v-if="blocked" role="status" class="dep-banner dep-blocked">
        <i class="fi fi-sr-lock" aria-hidden="true"></i>
        <div>
          Esta tarefa só poderá ser iniciada depois que
          <router-link :to="{ name: 'task', params: { id: task.depends_on } }">{{ task.depends_on_code }} · {{ task.depends_on_title }}</router-link>
          for concluída.
        </div>
      </div>
      <div v-if="task.blocking?.length" role="status" class="dep-banner dep-blocking">
        <i class="fi fi-sr-link" aria-hidden="true"></i>
        <div>
          Estas tarefas estão esperando a conclusão desta:
          <template v-for="(t, i) in task.blocking" :key="t.id">
            <router-link :to="{ name: 'task', params: { id: t.id } }">{{ t.code }} · {{ t.title }}</router-link><span v-if="i < task.blocking.length - 1">, </span>
          </template>.
        </div>
      </div>

      <div class="task-tabs">
        <SlidingTabs :items="taskTabs" v-model="activeTab" pill-color="rgba(124,111,255,.16)" active-text-color="#b3aaff" inactive-text-color="#8b899f" />
      </div>

      <ReferencesPanel v-if="activeTab === 'references'" :task-id="task.id" @count="referencesTotal = $event" />

      <div v-show="activeTab === 'details'" class="task-grid" style="display:grid; grid-template-columns:minmax(0,1fr) 340px; gap:16px; align-items:start;">
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

              <div v-if="canEdit" class="kind-row" role="radiogroup" aria-label="Tipo de tarefa">
                <button type="button" role="radio" :aria-checked="form.kind === 'solo'" :class="{ active: form.kind === 'solo' }" @click="form.kind = 'solo'"><i class="fi fi-sr-user" aria-hidden="true"></i>Solo</button>
                <button type="button" role="radio" :aria-checked="form.kind === 'group'" :class="{ active: form.kind === 'group' }" @click="form.kind = 'group'"><i class="fi fi-sr-users" aria-hidden="true"></i>Em grupo</button>
              </div>
              <div v-if="form.kind === 'group'">
                <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:8px;">Quem faz essa tarefa</div>
                <GroupPicker v-model="form.participants" :people="people" :roles="roles" :disabled="!canEdit" />
              </div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Cargo</div>
                  <CustomSelect v-model="form.role" :options="roleOptions" :disabled="!canEdit" width="100%" label="Cargo" />
                </div>
                <div v-if="form.kind !== 'group'">
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
                      :style="{ width: '100%', boxSizing: 'border-box', border: '1px solid #26263a', background: canEdit ? '#0e0e14' : '#131319', borderRadius: '9px', padding: '9px 11px', fontSize: '12.5px', color: form.due_date ? (canEdit ? '#c7c5dc' : '#9a97b8') : 'transparent', outline: 'none', cursor: canEdit ? 'default' : 'not-allowed' }" />
                    <span v-if="!form.due_date" style="position:absolute; left:11px; top:50%; transform:translateY(-50%); font-size:12.5px; color:#7f7d97; pointer-events:none;">Sem prazo</span>
                  </div>
                  <div v-if="canEdit" style="display:flex; gap:5px; margin-top:6px; flex-wrap:wrap;">
                    <button type="button" @click="setQuickDate(0)" style="font-size:10.5px; color:#8b899f; cursor:pointer; border:1px solid #26263a; background:transparent; border-radius:6px; padding:3px 7px;">Hoje</button>
                    <button type="button" @click="setQuickDate(1)" style="font-size:10.5px; color:#8b899f; cursor:pointer; border:1px solid #26263a; background:transparent; border-radius:6px; padding:3px 7px;">Amanhã</button>
                    <button type="button" @click="setQuickDate(7)" style="font-size:10.5px; color:#8b899f; cursor:pointer; border:1px solid #26263a; background:transparent; border-radius:6px; padding:3px 7px;">+7 dias</button>
                  </div>
                </div>
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Depende de</div>
                  <CustomSelect v-model="form.depends_on" :options="dependencyOptions" :disabled="!canEdit" width="100%" label="Depende de" />
                </div>
                <div>
                  <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Prioridade</div>
                  <CustomSelect v-model="form.priority" :options="priorityOptions" :disabled="!canEdit" width="100%" label="Prioridade" />
                </div>
              </div>

              <div>
                <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Status</div>
                <div v-if="allStepsDone && canEditStatus && (form.status !== 'Concluída' || !form.completion_note.trim())" role="status"
                  style="margin-bottom:8px; padding:8px 10px; border-radius:9px; background:rgba(124,111,255,.12); border:1px solid rgba(124,111,255,.35); font-size:12px; line-height:1.45; color:#cfc9ff;">
                  Todas as etapas foram feitas. Para salvar, marque <strong>Concluída</strong> e escreva a nota de conclusão.
                </div>
                <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:6px;">
                  <button v-for="s in ['Pendente', 'Em andamento', 'Concluída']" :key="s" type="button" :disabled="!canEditStatus || (blocked && s !== 'Pendente')" @click="form.status = s"
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
            <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:8px; display:flex; align-items:center; justify-content:space-between; gap:8px;">
              Checklist do que fazer
              <span style="display:inline-flex; align-items:center; gap:6px;">
                <span style="font-weight:500; color:#8b899f; font-size:11px;">{{ subtasks.filter(s => s.done).length }}/{{ subtasks.length }}</span>
                <span v-if="canEdit && isGroup" class="dots-wrap">
                  <button type="button" class="dots-btn" aria-haspopup="menu" :aria-expanded="stepMenuOpen" aria-label="Opções do checklist" @click="stepMenuOpen = !stepMenuOpen" @keydown.esc="stepMenuOpen = false" @blur="stepMenuOpen = false">
                    <i class="fi fi-sr-menu-dots-vertical" aria-hidden="true"></i>
                  </button>
                  <div v-if="stepMenuOpen" class="dots-menu" role="menu" @mousedown.prevent>
                    <button type="button" role="menuitem" @click="startOrder"><i class="fi fi-sr-sort-amount-down" aria-hidden="true"></i>Definir quem faz primeiro</button>
                    <button v-if="order.length" type="button" role="menuitem" @click="clearOrder"><i class="fi fi-sr-cross-small" aria-hidden="true"></i>Todos ao mesmo tempo</button>
                  </div>
                </span>
              </span>
            </div>

            <div v-if="orderEditing" class="order-editor">
              <div class="oe-title">Ordem de quem faz</div>
              <div class="oe-hint">Cada um só pode marcar uma etapa depois de quem vem antes. O de cima começa; o próximo recebe um aviso no Discord quando o anterior termina.</div>
              <ol>
                <li v-for="(id, i) in orderDraft" :key="id">
                  <b>{{ i + 1 }}</b><span>{{ nameOf(id) }}</span>
                  <button type="button" :disabled="i === 0" :aria-label="`Subir ${nameOf(id)}`" @click="moveDraft(i, -1)"><i class="fi fi-sr-angle-small-up" aria-hidden="true"></i></button>
                  <button type="button" :disabled="i === orderDraft.length - 1" :aria-label="`Descer ${nameOf(id)}`" @click="moveDraft(i, 1)"><i class="fi fi-sr-angle-small-down" aria-hidden="true"></i></button>
                </li>
              </ol>
              <div class="oe-actions">
                <button type="button" class="oe-save" :disabled="orderSaving" @click="saveOrder(orderDraft)">{{ orderSaving ? 'Salvando…' : 'Salvar ordem' }}</button>
                <button type="button" @click="orderEditing = false">Cancelar</button>
              </div>
            </div>
            <div v-else-if="isGroup && order.length" class="order-strip" aria-label="Ordem de execução">
              <i class="fi fi-sr-sort-amount-down" aria-hidden="true"></i>
              <template v-for="(p, i) in task.participants_info" :key="p.id"><span><b>{{ i + 1 }}</b> {{ p.name }}</span><i v-if="i < task.participants_info.length - 1" class="fi fi-sr-angle-small-right sep" aria-hidden="true"></i></template>
            </div>
            <div v-if="isGroup && subtasks.length" class="group-progress" aria-label="Progresso de cada pessoa no checklist">
              <div class="gp-hint">Todos fazem o mesmo checklist. Cada um marca as etapas que concluiu.</div>
              <div v-for="p in groupProgress" :key="p.id" class="gp-line">
                <AssigneeAvatar :photo="p.photo" :color="roleColor(task.role)" :size="20" />
                <span class="gp-name">{{ p.name }}<em v-if="p.id === auth.state.person?.id"> (você)</em></span>
                <span class="gp-bar"><i :style="{ width: (p.total ? (p.done / p.total) * 100 : 0) + '%' }" :class="{ full: p.total && p.done === p.total }"></i></span>
                <span class="gp-num">{{ p.done }}/{{ p.total }}</span>
              </div>
            </div>
            <TransitionGroup tag="div" @enter="listEnter" @leave="listLeave" :css="false" style="display:flex; flex-direction:column; gap:6px; margin-bottom:8px;">
              <div v-for="(st, i) in subtasks" :key="st.id" :data-index="i" :style="{ display: 'flex', alignItems: 'center', gap: '8px', background: canToggleChecklist ? '#0e0e14' : '#131319', border: '1px solid #22222f', borderRadius: '8px', padding: '8px 10px' }">
                <Checkbox :model-value="stepChecked(st)" :disabled="!canToggleChecklist || !!lockReason(st)" :title="lockReason(st)" @update:model-value="toggleSubtask(st)" :aria-label="`Marcar etapa: ${st.title}`" />
                <i v-if="lockReason(st)" class="fi fi-sr-lock step-lock" :title="lockReason(st)" aria-hidden="true"></i>
                <span :style="{ flex: 1, fontSize: '12.5px', color: st.done || !canToggleChecklist ? '#8f8da8' : '#e4e2f1', textDecoration: st.done ? 'line-through' : 'none' }">{{ st.title }}</span>
                <span v-if="isGroup" class="step-who" :title="finishers(st).length ? 'Concluíram: ' + finishers(st).map((p) => p.name).join(', ') : 'Ninguém concluiu ainda'">
                  <AssigneeAvatar v-for="p in finishers(st).slice(0, 3)" :key="p.id" :photo="p.photo" :color="roleColor(task.role)" :size="18" />
                  <small :class="{ full: st.done }">{{ finishers(st).length }}/{{ task.participants_info.length }}</small>
                </span>
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
            <div v-if="task.kind === 'group'" class="avatar-stack" aria-hidden="true">
              <AssigneeAvatar v-for="p in task.participants_info.slice(0, 4)" :key="p.id" :photo="p.photo" :color="roleColor(task.role)" :size="36" />
            </div>
            <AssigneeAvatar v-else :photo="task.assignee_photo" :color="roleColor(task.role)" :size="36" />
            <div style="min-width:0;">
              <div style="font-size:12.5px; font-weight:700; color:#f5f4fb; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ task.kind === 'group' ? task.participants_info.map((p) => p.name).join(', ') : (task.assignee_name || 'Sem responsável') }}</div>
              <div v-if="task.kind === 'group'" style="font-size:10.5px; font-weight:700; color:#b3aaff;"><i class="fi fi-sr-users" aria-hidden="true"></i> Tarefa em grupo · {{ task.participants_info.length }} pessoas</div>
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

<style scoped>
.dots-wrap { position: relative; display: inline-flex; }
.dots-btn { width: 24px; height: 24px; display: inline-grid; place-items: center; border: none; border-radius: 6px; background: transparent; color: #8b899f; font-size: 13px; cursor: pointer; }
.dots-btn:hover, .dots-btn:focus-visible { background: #1c1c28; color: #fff; outline: none; }
.dots-menu { position: absolute; right: 0; top: 28px; z-index: 20; min-width: 210px; padding: 4px; border-radius: 10px; background: #14141d; border: 1px solid #26263a; box-shadow: 0 12px 30px rgba(0, 0, 0, .5); display: flex; flex-direction: column; }
.dots-menu button { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border: none; border-radius: 7px; background: transparent; color: #c7c5dc; font-size: 12px; font-weight: 600; text-align: left; cursor: pointer; white-space: nowrap; }
.dots-menu button:hover, .dots-menu button:focus-visible { background: #1c1c28; color: #fff; outline: none; }
.order-editor { margin-bottom: 12px; padding: 12px; border-radius: 10px; background: #0e0e14; border: 1px solid #7c6fff55; }
.oe-title { font-size: 12.5px; font-weight: 800; color: #f5f4fb; }
.oe-hint { margin: 3px 0 10px; font-size: 11px; line-height: 1.45; color: #8b899f; }
.order-editor ol { list-style: none; margin: 0 0 10px; padding: 0; display: grid; gap: 5px; }
.order-editor li { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 8px; background: #14141d; border: 1px solid #22222f; font-size: 12.5px; color: #e4e2f1; }
.order-editor li b { width: 20px; height: 20px; display: grid; place-items: center; border-radius: 50%; background: rgba(124, 111, 255, .2); color: #cfc9ff; font-size: 11px; }
.order-editor li span { flex: 1; font-weight: 600; }
.order-editor li button { width: 26px; height: 26px; display: grid; place-items: center; border: 1px solid #26263a; border-radius: 7px; background: #0e0e14; color: #c7c5dc; cursor: pointer; }
.order-editor li button:disabled { opacity: .3; cursor: default; }
.oe-actions { display: flex; gap: 8px; }
.oe-actions button { padding: 7px 12px; border-radius: 8px; border: 1px solid #26263a; background: #14141d; color: #c7c5dc; font-size: 12px; font-weight: 700; cursor: pointer; }
.oe-actions .oe-save { background: #7c6fff; border-color: #7c6fff; color: #0a0a10; }
.order-strip { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; padding: 8px 10px; border-radius: 9px; background: rgba(124, 111, 255, .09); border: 1px solid rgba(124, 111, 255, .25); font-size: 11.5px; color: #cfc9ff; }
.order-strip b { display: inline-grid; place-items: center; width: 16px; height: 16px; margin-right: 2px; border-radius: 50%; background: rgba(124, 111, 255, .3); font-size: 10px; }
.order-strip .sep { color: #65637a; }
.step-lock { flex: none; color: #ffc46b; font-size: 11px; }
.group-progress { display: grid; gap: 6px; margin-bottom: 12px; padding: 10px 12px; border-radius: 10px; background: #0e0e14; border: 1px solid #22222f; }
.gp-hint { font-size: 11px; color: #8b899f; margin-bottom: 2px; }
.gp-line { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #c7c5dc; }
.gp-name { flex: none; width: 96px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.gp-name em { font-style: normal; color: #b3aaff; font-weight: 500; }
.gp-bar { flex: 1; height: 6px; border-radius: 6px; background: #1c1c28; overflow: hidden; }
.gp-bar i { display: block; height: 100%; background: #7c6fff; border-radius: 6px; transition: width .25s ease; }
.gp-bar i.full { background: #3fcf8e; }
.gp-num { flex: none; font-size: 11px; font-weight: 700; color: #8b899f; font-variant-numeric: tabular-nums; }
.step-who { display: inline-flex; align-items: center; flex: none; }
.step-who > :deep(*) + :deep(*) { margin-left: -6px; }
.step-who small { margin-left: 6px; font-size: 10.5px; font-weight: 700; color: #8b899f; }
.step-who small.full { color: #3fcf8e; }
.kind-row { display: inline-flex; gap: 6px; }
.kind-row button { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; border: 1px solid #26263a; background: #0e0e14; color: #9a97b8; font-size: 11.5px; font-weight: 700; cursor: pointer; }
.kind-row button.active { border-color: #7c6fff; background: rgba(124, 111, 255, .16); color: #f5f4fb; }
.kind-row button:focus-visible { outline: 2px solid #7c6fff; outline-offset: 1px; }
.avatar-stack { display: flex; flex: none; }
.avatar-stack > :deep(*) + :deep(*) { margin-left: -12px; box-shadow: -2px 0 0 #14141d; }
.dep-banner { display: flex; gap: 10px; align-items: flex-start; margin-bottom: 14px; padding: 11px 14px; border-radius: 10px; font-size: 12.5px; line-height: 1.5; }
.dep-banner i { margin-top: 2px; flex: none; }
.dep-banner a { font-weight: 700; text-decoration: underline; }
.dep-blocked { background: rgba(255, 196, 107, .1); border: 1px solid rgba(255, 196, 107, .35); color: #ffd9a0; }
.dep-blocked a, .dep-blocked i { color: #ffc46b; }
.dep-blocking { background: rgba(124, 111, 255, .1); border: 1px solid rgba(124, 111, 255, .3); color: #cfc9ff; }
.dep-blocking a, .dep-blocking i { color: #b3aaff; }
</style>
