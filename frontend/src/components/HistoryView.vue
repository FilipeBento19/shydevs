<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'
import { initials } from '../utils'

const router = useRouter()
const activities = ref([])
const loading = ref(true)
const error = ref('')
const scope = ref('normal')
const search = ref('')
const category = ref('all')

const isAdmin = computed(() => !!auth.state.person?.is_admin)

const EVENT_META = {
  task_created: { label: 'Criação', icon: 'fi-sr-plus', color: '#7c6fff', category: 'tasks' },
  task_completed: { label: 'Conclusão', icon: 'fi-sr-check-circle', color: '#3fcf8e', category: 'tasks' },
  task_status: { label: 'Status', icon: 'fi-sr-refresh', color: '#6fb3ff', category: 'tasks' },
  task_assigned: { label: 'Atribuição', icon: 'fi-sr-user-add', color: '#b09cff', category: 'tasks' },
  task_updated: { label: 'Edição', icon: 'fi-sr-pencil', color: '#e0a23c', category: 'tasks' },
  checklist: { label: 'Checklist', icon: 'fi-sr-list-check', color: '#62c7b0', category: 'checklist' },
  comment: { label: 'Comentário', icon: 'fi-sr-comment', color: '#a99fff', category: 'conversations' },
  attachment: { label: 'Arquivo', icon: 'fi-sr-clip', color: '#6fb3ff', category: 'files' },
  team: { label: 'Equipe', icon: 'fi-sr-users', color: '#e08dad', category: 'team' },
  settings: { label: 'Configuração', icon: 'fi-sr-settings', color: '#aaa7bc', category: 'system' },
  system: { label: 'Sistema', icon: 'fi-sr-info', color: '#8b899f', category: 'system' },
}

const categories = [
  { value: 'all', label: 'Todos os tipos' },
  { value: 'tasks', label: 'Tarefas' },
  { value: 'checklist', label: 'Checklist' },
  { value: 'conversations', label: 'Comentários' },
  { value: 'files', label: 'Arquivos' },
  { value: 'team', label: 'Equipe' },
  { value: 'system', label: 'Sistema' },
]

function meta(activity) {
  return EVENT_META[activity.event_type] || EVENT_META.system
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    activities.value = await api.getActivities(undefined, scope.value)
  } catch (e) {
    error.value = 'Não foi possível carregar o histórico.'
  } finally {
    loading.value = false
  }
}

defineExpose({ load })
onMounted(load)
watch(scope, load)

const filtered = computed(() => {
  const term = search.value.trim().toLocaleLowerCase('pt-BR')
  return activities.value.filter((activity) => {
    if (category.value !== 'all' && meta(activity).category !== category.value) return false
    if (!term) return true
    return [activity.message, activity.actor_name, activity.task_code, activity.task_title, JSON.stringify(activity.details)]
      .some((value) => String(value || '').toLocaleLowerCase('pt-BR').includes(term))
  })
})

const todayCount = computed(() => {
  const today = new Date().toDateString()
  return activities.value.filter((activity) => new Date(activity.created_at).toDateString() === today).length
})
const actorCount = computed(() => new Set(activities.value.map((activity) => activity.actor_name).filter(Boolean)).size)
const taskCount = computed(() => new Set(activities.value.map((activity) => activity.task).filter(Boolean)).size)

function fmtDate(iso) {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function detailRows(details) {
  if (!details || typeof details !== 'object') return []
  const rows = []
  Object.entries(details).forEach(([key, value]) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      if ('antes' in value || 'depois' in value) {
        rows.push({ label: key, before: value.antes, after: value.depois })
      } else {
        Object.entries(value).forEach(([nestedKey, nestedValue]) => {
          rows.push({
            label: nestedKey,
            before: typeof nestedValue === 'object' ? nestedValue.antes : '',
            after: typeof nestedValue === 'object' ? nestedValue.depois : nestedValue,
          })
        })
      }
    } else {
      rows.push({ label: key, before: '', after: String(value) })
    }
  })
  return rows
}

function openTask(activity) {
  if (activity.task) router.push({ name: 'task', params: { id: activity.task } })
}
</script>

<template>
  <main class="history-page">
    <header class="history-hero">
      <div>
        <span class="eyebrow"><i class="fi fi-sr-clock-three" aria-hidden="true"></i> Linha do tempo</span>
        <h1>{{ scope === 'admin' ? 'Auditoria administrativa' : 'Histórico da equipe' }}</h1>
        <p>{{ scope === 'admin' ? 'Rastreie mudanças, responsáveis e detalhes operacionais do projeto.' : 'Acompanhe as entregas e os principais acontecimentos do time.' }}</p>
      </div>
      <div v-if="isAdmin" class="scope-tabs" aria-label="Tipo de histórico">
        <button type="button" :class="{ active: scope === 'normal' }" @click="scope = 'normal'"><i class="fi fi-sr-users" aria-hidden="true"></i>Equipe</button>
        <button type="button" :class="{ active: scope === 'admin' }" @click="scope = 'admin'"><i class="fi fi-sr-shield-check" aria-hidden="true"></i>Admin</button>
      </div>
    </header>

    <section v-if="scope === 'admin' && isAdmin" class="audit-summary" aria-label="Resumo da auditoria">
      <div><span>Eventos registrados</span><strong>{{ activities.length }}</strong></div>
      <div><span>Ações de hoje</span><strong>{{ todayCount }}</strong></div>
      <div><span>Pessoas ativas</span><strong>{{ actorCount }}</strong></div>
      <div><span>Tarefas afetadas</span><strong>{{ taskCount }}</strong></div>
    </section>

    <section class="history-controls">
      <label class="history-search">
        <i class="fi fi-sr-search" aria-hidden="true"></i>
        <span class="sr-only">Buscar no histórico</span>
        <input v-model="search" placeholder="Buscar pessoa, tarefa ou ação…" />
      </label>
      <select v-if="scope === 'admin'" v-model="category" aria-label="Filtrar tipo de evento">
        <option v-for="item in categories" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <button type="button" :disabled="loading" @click="load"><i class="fi fi-sr-refresh" aria-hidden="true"></i>Atualizar</button>
    </section>

    <div v-if="loading" class="history-state"><span class="btn-spinner" aria-hidden="true"></span>Organizando a linha do tempo…</div>
    <div v-else-if="error" class="history-state error">{{ error }}</div>
    <div v-else-if="!filtered.length" class="history-state"><i class="fi fi-sr-clock" aria-hidden="true"></i>Nenhum evento encontrado.</div>

    <section v-else-if="scope === 'normal'" class="team-timeline">
      <article v-for="activity in filtered" :key="activity.id" class="timeline-event">
        <span class="timeline-icon" :style="{ color: meta(activity).color, background: `${meta(activity).color}18`, borderColor: `${meta(activity).color}35` }"><i :class="`fi ${meta(activity).icon}`" aria-hidden="true"></i></span>
        <span class="timeline-line" aria-hidden="true"></span>
        <div class="timeline-card" :class="{ clickable: activity.task }" @click="openTask(activity)">
          <div class="event-topline"><span :style="{ color: meta(activity).color }">{{ meta(activity).label }}</span><time>{{ fmtDate(activity.created_at) }}</time></div>
          <p>{{ activity.message }}</p>
          <span v-if="activity.task_code" class="task-reference"><i class="fi fi-sr-arrow-up-right" aria-hidden="true"></i>{{ activity.task_code }} · {{ activity.task_title }}</span>
        </div>
      </article>
    </section>

    <section v-else class="audit-log">
      <article v-for="activity in filtered" :key="activity.id" class="audit-event">
        <div class="audit-icon" :style="{ color: meta(activity).color, background: `${meta(activity).color}16` }"><i :class="`fi ${meta(activity).icon}`" aria-hidden="true"></i></div>
        <div class="audit-main">
          <div class="audit-heading">
            <span class="event-tag" :style="{ color: meta(activity).color, borderColor: `${meta(activity).color}40`, background: `${meta(activity).color}10` }">{{ meta(activity).label }}</span>
            <span class="visibility-tag"><i :class="`fi ${activity.visibility === 'admin' ? 'fi-sr-lock' : 'fi-sr-users'}`" aria-hidden="true"></i>{{ activity.visibility === 'admin' ? 'Somente admin' : 'Visível à equipe' }}</span>
            <time>{{ fmtDate(activity.created_at) }}</time>
          </div>
          <p>{{ activity.message }}</p>
          <div class="audit-context">
            <span class="actor-avatar">{{ initials(activity.actor_name || 'Sistema') }}</span>
            <span><small>Executado por</small><strong>{{ activity.actor_name || 'Sistema' }}</strong></span>
            <button v-if="activity.task" type="button" @click="openTask(activity)"><small>Tarefa afetada</small><strong>{{ activity.task_code }} · {{ activity.task_title }}</strong></button>
          </div>
          <div v-if="detailRows(activity.details).length" class="change-grid">
            <div v-for="row in detailRows(activity.details)" :key="row.label" class="change-row">
              <span>{{ row.label }}</span>
              <template v-if="row.before !== '' && row.before !== undefined">
                <del>{{ row.before }}</del><i class="fi fi-sr-arrow-right" aria-hidden="true"></i><strong>{{ row.after }}</strong>
              </template>
              <strong v-else>{{ row.after }}</strong>
            </div>
          </div>
        </div>
      </article>
    </section>
  </main>
</template>

<style scoped>
.history-page { min-height: 100%; padding: 24px 26px 34px; color: #f5f4fb; }
.history-hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; max-width: 1100px; margin: 0 auto 18px; }
.eyebrow { display: inline-flex; align-items: center; gap: 6px; color: #988eff; font-size: 9.5px; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
.history-hero h1 { margin: 7px 0 4px; font-size: 24px; letter-spacing: -.03em; }
.history-hero p { margin: 0; color: #858297; font-size: 11.5px; }
.scope-tabs { display: flex; gap: 4px; padding: 4px; border: 1px solid #272635; border-radius: 10px; background: #111118; }
.scope-tabs button { display: inline-flex; align-items: center; gap: 6px; min-height: 32px; padding: 0 11px; border: 0; border-radius: 7px; background: transparent; color: #858297; font: inherit; font-size: 10.5px; font-weight: 700; cursor: pointer; }
.scope-tabs button.active { background: rgba(124,111,255,.17); color: #c9c3ff; }
.audit-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 9px; max-width: 1100px; margin: 0 auto 12px; }
.audit-summary div { padding: 13px 14px; border: 1px solid #242331; border-radius: 10px; background: #13131b; }
.audit-summary span, .audit-summary strong { display: block; }
.audit-summary span { color: #77758d; font-size: 9px; text-transform: uppercase; letter-spacing: .06em; }
.audit-summary strong { margin-top: 6px; font-size: 19px; }
.history-controls { display: flex; gap: 8px; max-width: 1100px; margin: 0 auto 13px; }
.history-search { display: flex; align-items: center; gap: 8px; min-height: 36px; flex: 1; padding: 0 11px; border: 1px solid #272635; border-radius: 9px; background: #101017; color: #696678; }
.history-search input { width: 100%; border: 0; outline: 0; background: transparent; color: #e6e3f0; font: inherit; font-size: 11.5px; }
.history-controls select, .history-controls > button { min-height: 36px; padding: 0 11px; border: 1px solid #272635; border-radius: 9px; background: #13131b; color: #aaa7bc; font: inherit; font-size: 10.5px; font-weight: 700; }
.history-controls > button { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
.history-state { display: flex; align-items: center; justify-content: center; gap: 9px; min-height: 220px; max-width: 1100px; margin: auto; border: 1px dashed #292837; border-radius: 12px; color: #77758d; font-size: 12px; }
.history-state.error { color: #ff8f98; border-color: rgba(224,79,95,.3); }
.team-timeline, .audit-log { max-width: 1100px; margin: auto; }
.timeline-event { position: relative; display: grid; grid-template-columns: 36px 1fr; gap: 11px; padding-bottom: 11px; }
.timeline-icon { z-index: 1; display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid; border-radius: 10px; font-size: 12px; }
.timeline-line { position: absolute; top: 34px; bottom: -1px; left: 16px; width: 1px; background: #282735; }
.timeline-card { padding: 12px 14px; border: 1px solid #242331; border-radius: 11px; background: #13131b; }
.timeline-card.clickable { cursor: pointer; transition: border-color 150ms ease, transform 150ms ease; }
.timeline-card.clickable:hover { transform: translateY(-1px); border-color: rgba(124,111,255,.38); }
.event-topline { display: flex; justify-content: space-between; gap: 12px; }
.event-topline span { font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; }
.event-topline time, .audit-heading time { color: #666376; font-size: 9.5px; }
.timeline-card p, .audit-main > p { margin: 7px 0 0; color: #d6d3e2; font-size: 12px; line-height: 1.5; }
.task-reference { display: inline-flex; align-items: center; gap: 5px; margin-top: 8px; color: #8e86dd; font-size: 10px; }
.audit-log { display: flex; flex-direction: column; gap: 8px; }
.audit-event { display: grid; grid-template-columns: 34px 1fr; gap: 11px; padding: 13px; border: 1px solid #242331; border-radius: 11px; background: #121219; }
.audit-icon { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 9px; font-size: 11px; }
.audit-main { min-width: 0; }
.audit-heading { display: flex; align-items: center; gap: 7px; }
.audit-heading time { margin-left: auto; }
.event-tag, .visibility-tag { display: inline-flex; align-items: center; gap: 4px; padding: 3px 6px; border: 1px solid; border-radius: 6px; font-size: 8px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; }
.visibility-tag { border-color: #292735; color: #666376; }
.audit-context { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
.actor-avatar { display: grid; place-items: center; width: 25px; height: 25px; border-radius: 50%; background: #2b2751; color: #c9c3ff; font-size: 7.5px; font-weight: 800; }
.audit-context > span small, .audit-context > span strong, .audit-context button small, .audit-context button strong { display: block; }
.audit-context small { color: #666376; font-size: 8px; font-weight: 500; }
.audit-context strong { margin-top: 2px; color: #aaa7bc; font-size: 9.5px; }
.audit-context button { margin-left: auto; padding: 0; border: 0; background: transparent; text-align: right; cursor: pointer; }
.audit-context button strong { color: #958ce6; }
.change-grid { display: grid; gap: 5px; margin-top: 11px; padding: 9px; border: 1px solid #20202b; border-radius: 8px; background: #0e0e14; }
.change-row { display: grid; grid-template-columns: minmax(90px,.7fr) minmax(0,1fr) 14px minmax(0,1fr); align-items: center; gap: 7px; min-width: 0; font-size: 9.5px; }
.change-row > span { color: #77758d; text-transform: capitalize; }
.change-row del, .change-row strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.change-row del { color: #9a6670; }
.change-row strong { color: #aaa7bc; }
.change-row > i { color: #555264; font-size: 8px; }
.change-row > span + strong { grid-column: 2 / -1; }
@media (max-width: 720px) {
  .history-page { padding-inline: 15px; }
  .history-hero { align-items: flex-start; flex-direction: column; }
  .audit-summary { grid-template-columns: 1fr 1fr; }
  .history-controls { flex-wrap: wrap; }
  .history-search { flex-basis: 100%; }
  .change-row { grid-template-columns: 78px minmax(0,1fr); }
  .change-row > i { display: none; }
}
</style>
