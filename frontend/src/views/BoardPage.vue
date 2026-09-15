<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'
import { auth } from '../auth'
import { playDing } from '../sound'
import { tasksVersion, bumpTasks } from '../taskBus'
import { gsap, reduceMotion } from '../motion'
import { isLate } from '../utils'
import CustomSelect from '../components/CustomSelect.vue'
import SlidingTabs from '../components/SlidingTabs.vue'
import RoleChipsBar from '../components/RoleChipsBar.vue'
import TaskTable from '../components/TaskTable.vue'
import KanbanBoard from '../components/KanbanBoard.vue'

const canEdit = computed(() => !!auth.state.person?.is_admin)

const tasks = ref([])
const people = ref([])
const roles = ref([])
const balance = ref(null)
const loading = ref(true)
const error = ref('')

const filters = reactive({ role: 'Todos', status: 'Todas', prio: 'Todas', person: 'Todos', query: '' })
const myTasksOnly = ref(false)
const boardMode = ref('tabela')
const selectedIds = ref([])
const searchInputRef = ref(null)

const roleChipsEl = ref(null)
const filterBarEl = ref(null)
const statusTabsEl = ref(null)
const tableCardEl = ref(null)
const balanceCardEl = ref(null)

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [taskList, peopleList, roleList, balanceData] = await Promise.all([
      api.getTasks(), api.getPeople(), api.getRoles(), api.getBalance(),
    ])
    tasks.value = taskList
    people.value = peopleList
    roles.value = roleList
    balance.value = balanceData
  } catch (e) {
    error.value = e.message || 'Não foi possível carregar os dados do backend.'
  } finally {
    loading.value = false
  }
}

watch(tasksVersion, loadAll)

function safeTargets(...vals) {
  const list = vals.flatMap((v) => (v && v.length !== undefined ? Array.from(v) : v ? [v] : []))
  return list.filter(Boolean)
}
function playEntrance() {
  if (reduceMotion) return
  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
  const step = (targets, vars, pos) => {
    const t = safeTargets(targets)
    if (t.length) tl.from(t, vars, pos)
  }
  step(roleChipsEl.value?.querySelectorAll('button'), { y: 10, autoAlpha: 0, stagger: 0.04, duration: 0.35 })
  step(filterBarEl.value, { y: 10, autoAlpha: 0, duration: 0.4 }, '-=0.2')
  step(statusTabsEl.value?.querySelectorAll('button'), { y: 8, autoAlpha: 0, stagger: 0.04, duration: 0.3 }, '-=0.25')
  step(tableCardEl.value, { y: 14, autoAlpha: 0, duration: 0.5 }, '-=0.2')
}

watch(balance, async (val) => {
  if (!val) return
  await nextTick()
  if (reduceMotion || !balanceCardEl.value) return
  gsap.from(balanceCardEl.value, { y: 14, autoAlpha: 0, duration: 0.5, ease: 'power3.out' })
})

onMounted(async () => {
  await loadAll()
  await nextTick()
  playEntrance()
})

function onKeydown(e) {
  const tag = (e.target.tagName || '').toLowerCase()
  if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return
  if (e.key === '/') {
    e.preventDefault()
    searchInputRef.value?.focus()
  }
}
defineExpose({ focusSearch: () => searchInputRef.value?.focus() })

const filteredTasks = computed(() => {
  const q = filters.query.trim().toLowerCase()
  return tasks.value.filter((t) => {
    if (myTasksOnly.value && auth.state.person && t.assignee_name !== auth.state.person.name) return false
    if (filters.role !== 'Todos' && t.role !== filters.role) return false
    if (filters.person !== 'Todos' && t.assignee_name !== filters.person) return false
    if (filters.prio !== 'Todas' && t.priority !== filters.prio) return false
    if (filters.status === 'Atrasadas' && !isLate(t)) return false
    if (filters.status !== 'Todas' && filters.status !== 'Atrasadas' && t.status !== filters.status) return false
    if (q) {
      const haystack = `${t.title} ${t.description} ${t.assignee_name || ''} ${t.role} ${t.code}`.toLowerCase()
      if (!haystack.includes(q)) return false
    }
    return true
  })
})

const roleCounts = computed(() => {
  const map = {}
  for (const r of roles.value) map[r.name] = tasks.value.filter((t) => t.role === r.name).length
  return map
})

const statusTabs = computed(() => [
  { key: 'Todas', label: 'Todas', count: tasks.value.length },
  { key: 'Pendente', label: 'Pendentes', count: tasks.value.filter((t) => t.status === 'Pendente').length },
  { key: 'Em andamento', label: 'Em andamento', count: tasks.value.filter((t) => t.status === 'Em andamento').length },
  { key: 'Concluída', label: 'Concluídas', count: tasks.value.filter((t) => t.status === 'Concluída').length },
  { key: 'Atrasadas', label: 'Atrasadas', count: tasks.value.filter((t) => isLate(t)).length },
])

const personFilterOptions = computed(() => [
  { value: 'Todos', label: 'Todos os responsáveis', icon: 'fi-sr-users' },
  ...people.value.map((p) => ({ value: p.name, label: p.name })),
])
const prioFilterOptions = [
  { value: 'Todas', label: 'Prioridade: Todas' },
  { value: 'Alta', label: 'Prioridade: Alta', color: '#e04f5f' },
  { value: 'Média', label: 'Prioridade: Média', color: '#e0a23c' },
  { value: 'Baixa', label: 'Prioridade: Baixa', color: '#9a9ab0' },
]

// ---- selection & bulk actions ----
function isSelectedAny() {
  return selectedIds.value.length > 0
}
function toggleSelect(id) {
  const i = selectedIds.value.indexOf(id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(id)
}
const allSelected = computed(
  () => filteredTasks.value.length > 0 && filteredTasks.value.every((t) => selectedIds.value.includes(t.id))
)
function toggleSelectAll() {
  if (allSelected.value) {
    const ids = new Set(filteredTasks.value.map((t) => t.id))
    selectedIds.value = selectedIds.value.filter((id) => !ids.has(id))
  } else {
    selectedIds.value = [...new Set([...selectedIds.value, ...filteredTasks.value.map((t) => t.id)])]
  }
}
function clearSelection() {
  selectedIds.value = []
}

async function bulkSetStatus(status) {
  if (!canEdit.value) return
  try {
    await api.bulkUpdateTasks(selectedIds.value, { status })
    tasks.value = tasks.value.map((t) => (selectedIds.value.includes(t.id) ? { ...t, status } : t))
    if (status === 'Concluída') playDing()
    balance.value = await api.getBalance()
    clearSelection()
    bumpTasks()
  } catch (e) {
    error.value = 'Não foi possível atualizar as tarefas selecionadas.'
  }
}
async function bulkDelete() {
  if (!canEdit.value) return
  try {
    await api.bulkDeleteTasks(selectedIds.value)
    tasks.value = tasks.value.filter((t) => !selectedIds.value.includes(t.id))
    clearSelection()
    bumpTasks()
  } catch (e) {
    error.value = 'Não foi possível excluir as tarefas selecionadas.'
  }
}

// ---- kanban ----
async function onKanbanStatusChange(task, status) {
  if (!canEdit.value) return
  const previousStatus = task.status
  task.status = status
  try {
    await api.updateTask(task.id, { status })
    if (status === 'Concluída') playDing()
    balance.value = await api.getBalance()
    bumpTasks()
  } catch (e) {
    task.status = previousStatus
  }
}
</script>

<template>
  <div v-if="error" style="margin:20px 26px 0; padding:12px 14px; background:rgba(224,79,95,.12); border:1px solid rgba(224,79,95,.35); border-radius:10px; color:#ff8f98; font-size:12.5px; font-weight:600; display:flex; align-items:center; gap:8px;">
    <i class="fi fi-sr-cross-circle" aria-hidden="true"></i>{{ error }}
  </div>

  <template v-else>
    <div style="padding:20px 26px 0;">
      <div ref="roleChipsEl">
        <RoleChipsBar
          :roles="roles" :role="filters.role" :total-count="tasks.length" :counts="roleCounts"
          :my-tasks-only="myTasksOnly"
          @update:role="filters.role = $event"
          @update:my-tasks-only="myTasksOnly = $event"
        />
      </div>
    </div>

    <div ref="filterBarEl" style="padding:16px 26px 0;">
      <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:12px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
        <div style="flex:1; min-width:210px; display:flex; align-items:center; gap:8px; background:#0e0e14; border:1px solid #22222f; border-radius:9px; padding:9px 12px;">
          <i class="fi fi-sr-search" aria-hidden="true" style="color:#8f8da8; font-size:12px;"></i>
          <label for="board-search" class="sr-only">Buscar tarefa por título, cargo, descrição ou responsável</label>
          <input id="board-search" ref="searchInputRef" v-model="filters.query" @keydown="onKeydown" placeholder="Buscar tarefa (atalho: /)…" style="border:none; background:transparent; outline:none; font-size:12.5px; color:#f5f4fb; width:100%;" />
        </div>
        <CustomSelect v-model="filters.person" :options="personFilterOptions" label="Filtrar por responsável" />
        <CustomSelect v-model="filters.prio" :options="prioFilterOptions" label="Filtrar por prioridade" />
        <SlidingTabs
          :items="[{ key: 'tabela', label: 'Tabela', icon: 'fi-sr-table-list' }, { key: 'cards', label: 'Cards', icon: 'fi-sr-chart-kanban' }]"
          v-model="boardMode"
          pill-color="rgba(124,111,255,.16)"
          active-text-color="#b3aaff"
          inactive-text-color="#8b899f"
          item-padding="7px 12px"
          :track-style="{ background: '#0e0e14', border: '1px solid #22222f', borderRadius: '9px', padding: '3px' }"
        />
      </div>
    </div>

    <div ref="statusTabsEl" style="padding:14px 26px 0;">
      <SlidingTabs
        :items="statusTabs"
        v-model="filters.status"
        pill-color="#7c6fff"
        active-text-color="#0a0a10"
        inactive-text-color="#c7c5dc"
        gap="7px"
        :track-style="{ background: '#14141d', border: '1px solid #22222f', borderRadius: '10px', padding: '4px' }"
      />
    </div>

    <div style="padding:18px 26px 0; display:flex; align-items:baseline; justify-content:space-between; gap:12px; flex-wrap:wrap;">
      <div style="font-size:13px; font-weight:700; color:#f5f4fb;">
        Demandas Selecionadas
        <span style="font-weight:500; color:#8b899f; font-size:11.5px;">Exibindo {{ filteredTasks.length }} de {{ tasks.length }} tarefas</span>
      </div>
    </div>

    <div v-if="canEdit && isSelectedAny() && boardMode === 'tabela'" style="margin:12px 26px 0; background:rgba(124,111,255,.10); border:1px solid rgba(124,111,255,.3); border-radius:10px; padding:9px 12px; display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
      <span style="font-size:12px; font-weight:700; color:#cfc9ff;">{{ selectedIds.length }} selecionada(s)</span>
      <button @click="bulkSetStatus('Em andamento')" style="border:1px solid #26263a; background:#0e0e14; color:#c7c5dc; border-radius:7px; padding:6px 10px; font-size:11.5px; font-weight:700; cursor:pointer;">Em andamento</button>
      <button @click="bulkSetStatus('Concluída')" style="border:1px solid #26263a; background:#0e0e14; color:#c7c5dc; border-radius:7px; padding:6px 10px; font-size:11.5px; font-weight:700; cursor:pointer;">Concluir</button>
      <button @click="bulkDelete" style="border:1px solid rgba(224,79,95,.4); background:transparent; color:#ff8f98; border-radius:7px; padding:6px 10px; font-size:11.5px; font-weight:700; cursor:pointer;">Excluir</button>
      <button @click="clearSelection" style="margin-left:auto; border:none; background:transparent; color:#8b899f; font-size:11.5px; cursor:pointer;">Limpar seleção</button>
    </div>

    <div ref="tableCardEl" style="padding:10px 26px 0;">
      <KanbanBoard v-if="boardMode === 'cards'" :tasks="filteredTasks" :roles="roles" :can-edit="canEdit" @status-change="onKanbanStatusChange" />
      <TaskTable
        v-else
        :tasks="filteredTasks" :roles="roles" :can-edit="canEdit" :loading="loading"
        :selected-ids="selectedIds" :all-selected="allSelected"
        @toggle-select="toggleSelect" @toggle-select-all="toggleSelectAll"
      />
    </div>

    <div v-if="balance" ref="balanceCardEl" style="padding:18px 26px 26px;">
      <div style="background:rgba(124,111,255,.10); border:1px solid rgba(124,111,255,.3); border-radius:12px; padding:14px 16px; display:flex; gap:13px; align-items:center; flex-wrap:wrap;">
        <div style="width:30px; height:30px; border-radius:9px; background:#14141d; border:1px solid rgba(124,111,255,.3); display:flex; align-items:center; justify-content:center; color:#b3aaff; font-size:14px;"><i class="fi fi-sr-scale-comparison" aria-hidden="true"></i></div>
        <div style="flex:1; min-width:240px;">
          <div style="font-size:12.5px; font-weight:800; color:#cfc9ff;">Equilíbrio Dinâmico — {{ balance.role }}</div>
          <div style="font-size:12px; color:#b0abd6; margin-top:3px; line-height:1.5;">{{ balance.text }}</div>
        </div>
      </div>
      <div style="font-size:11px; color:#8f8da8; margin-top:8px;">A comparação acontece apenas entre pessoas do mesmo cargo.</div>
    </div>
  </template>
</template>
