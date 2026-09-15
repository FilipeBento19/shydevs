<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { gsap, reduceMotion } from '../motion'
import { formatDue, initials, isLate, prioBadge, roleIcon } from '../utils'

const router = useRouter()
const data = ref(null)
const tasks = ref([])
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
const rootEl = ref(null)
const lastUpdated = ref(null)

async function load() {
  const isRefresh = !!data.value
  loading.value = !isRefresh
  refreshing.value = isRefresh
  error.value = ''

  try {
    const [dashboardData, taskData] = await Promise.all([
      api.getDashboard(),
      api.getTasks(),
    ])
    data.value = dashboardData
    tasks.value = Array.isArray(taskData) ? taskData : taskData.results || []
    lastUpdated.value = new Date()
  } catch (e) {
    error.value = 'Não foi possível carregar o dashboard.'
  } finally {
    loading.value = false
    refreshing.value = false
  }

  await nextTick()
  animateIn()
}

defineExpose({ load })
onMounted(load)

function animateIn() {
  if (reduceMotion || !rootEl.value || error.value) return
  const cards = rootEl.value.querySelectorAll('.dashboard-animate')
  const bars = rootEl.value.querySelectorAll('.bar-fill')
  gsap.fromTo(cards, { y: 12, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.4, stagger: 0.045, ease: 'power2.out', clearProps: 'transform,opacity,visibility' })
  bars.forEach((bar) => {
    const target = bar.style.width
    gsap.fromTo(bar, { width: '0%' }, { width: target, duration: 0.7, ease: 'power3.out', delay: 0.12 })
  })
}

const statusColors = {
  Pendente: '#77758d',
  'Em andamento': '#7c6fff',
  Concluída: '#3fcf8e',
}
const priorityColors = { Alta: '#e85d6a', Média: '#e0a23c', Baixa: '#77758d' }
const priorityOrder = ['Alta', 'Média', 'Baixa']

const total = computed(() => data.value?.total || 0)
const completed = computed(() => data.value?.by_status?.['Concluída'] || 0)
const inProgress = computed(() => data.value?.by_status?.['Em andamento'] || 0)
const pending = computed(() => data.value?.by_status?.Pendente || 0)
const openTasks = computed(() => Math.max(0, total.value - completed.value))
const completionRate = computed(() => total.value ? Math.round((completed.value / total.value) * 100) : 0)

function dueDiff(task) {
  if (!task.due_date) return null
  const due = new Date(`${task.due_date}T00:00:00`)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((due - today) / 86400000)
}

const dueSoonTasks = computed(() => tasks.value
  .filter((task) => task.status !== 'Concluída' && dueDiff(task) !== null && dueDiff(task) >= 0 && dueDiff(task) <= 7)
  .sort((a, b) => dueDiff(a) - dueDiff(b)))

const unassignedTasks = computed(() => tasks.value.filter((task) => task.status !== 'Concluída' && !task.assignee))

const attentionTasks = computed(() => tasks.value
  .filter((task) => task.status !== 'Concluída' && (isLate(task) || task.priority === 'Alta' || !task.assignee))
  .sort((a, b) => {
    const score = (task) => (isLate(task) ? 100 : 0) + (task.priority === 'Alta' ? 30 : 0) + (!task.assignee ? 10 : 0) - (dueDiff(task) ?? 20)
    return score(b) - score(a)
  })
  .slice(0, 6))

const statusEntries = computed(() => [
  { label: 'Concluídas', value: completed.value, color: statusColors.Concluída },
  { label: 'Em andamento', value: inProgress.value, color: statusColors['Em andamento'] },
  { label: 'Pendentes', value: pending.value, color: statusColors.Pendente },
])

const priorityEntries = computed(() => priorityOrder.map((label) => ({
  label,
  value: data.value?.by_priority?.[label] || 0,
  color: priorityColors[label],
})))

const roleEntries = computed(() => Object.entries(data.value?.by_role || {})
  .map(([label, value]) => ({ label, value }))
  .filter((item) => item.value > 0)
  .sort((a, b) => b.value - a.value))

const workload = computed(() => [...(data.value?.workload || [])]
  .filter((person) => person.open + person.done > 0)
  .sort((a, b) => b.open - a.open || b.done - a.done))

const maxWorkload = computed(() => Math.max(1, ...workload.value.map((person) => person.open + person.done)))

const statusRing = computed(() => {
  if (!total.value) return 'conic-gradient(#242430 0 100%)'
  const doneEnd = (completed.value / total.value) * 100
  const progressEnd = doneEnd + (inProgress.value / total.value) * 100
  return `conic-gradient(${statusColors.Concluída} 0 ${doneEnd}%, ${statusColors['Em andamento']} ${doneEnd}% ${progressEnd}%, ${statusColors.Pendente} ${progressEnd}% 100%)`
})

const formattedUpdate = computed(() => lastUpdated.value?.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) || '—')

function percent(value, base = total.value) {
  return base ? Math.round((value / base) * 100) : 0
}

function personCompletion(person) {
  const personTotal = person.open + person.done
  return personTotal ? Math.round((person.done / personTotal) * 100) : 0
}

function deadlineClass(task) {
  if (isLate(task)) return 'danger'
  const diff = dueDiff(task)
  if (diff !== null && diff <= 2) return 'warning'
  return 'neutral'
}

function openTask(task) {
  router.push({ name: 'task', params: { id: task.id } })
}

function openBoard(status) {
  router.push({ name: 'board', query: { status } })
}
</script>

<template>
  <main ref="rootEl" class="dashboard-shell">
    <div v-if="loading" class="dashboard-loading" aria-live="polite">
      <span class="dashboard-loader" aria-hidden="true"></span>
      <div>
        <strong>Preparando os indicadores</strong>
        <span>Consolidando tarefas, prazos e carga da equipe…</span>
      </div>
    </div>

    <div v-else-if="error" class="dashboard-error" role="alert">
      <i class="fi fi-sr-triangle-warning" aria-hidden="true"></i>
      <div>
        <strong>O dashboard não pôde ser carregado</strong>
        <span>{{ error }}</span>
      </div>
      <button type="button" @click="load">Tentar novamente</button>
    </div>

    <template v-else-if="data">
      <section class="dashboard-toolbar dashboard-animate" aria-label="Atualização do dashboard">
        <div>
          <span class="eyebrow"><i class="fi fi-sr-bolt" aria-hidden="true"></i> Panorama operacional</span>
          <p>Uma leitura rápida do fluxo, dos riscos e da capacidade do time.</p>
        </div>
        <button class="refresh-button" type="button" :disabled="refreshing" @click="load">
          <i class="fi fi-sr-refresh" :class="{ spinning: refreshing }" aria-hidden="true"></i>
          {{ refreshing ? 'Atualizando…' : `Atualizado às ${formattedUpdate}` }}
        </button>
      </section>

      <section class="metric-grid" aria-label="Indicadores principais">
        <article class="metric-card dashboard-animate">
          <div class="metric-icon neutral"><i class="fi fi-sr-list-check" aria-hidden="true"></i></div>
          <div class="metric-heading"><span>Total de tarefas</span><strong>{{ total }}</strong></div>
          <p>{{ openTasks }} ainda fazem parte do fluxo ativo</p>
        </article>
        <article class="metric-card dashboard-animate">
          <div class="metric-icon purple"><i class="fi fi-sr-time-oclock" aria-hidden="true"></i></div>
          <div class="metric-heading"><span>Em andamento</span><strong>{{ inProgress }}</strong></div>
          <p>{{ percent(inProgress) }}% de todas as demandas</p>
        </article>
        <article class="metric-card dashboard-animate">
          <div class="metric-icon green"><i class="fi fi-sr-progress-complete" aria-hidden="true"></i></div>
          <div class="metric-heading"><span>Taxa de conclusão</span><strong>{{ completionRate }}%</strong></div>
          <p>{{ completed }} entregas já concluídas</p>
        </article>
        <button
          type="button"
          class="metric-card metric-card--button dashboard-animate"
          :class="{ 'metric-card--alert': data.overdue > 0 }"
          aria-label="Ver tarefas atrasadas no quadro"
          @click="openBoard('Atrasadas')"
        >
          <div class="metric-icon red"><i class="fi fi-sr-triangle-warning" aria-hidden="true"></i></div>
          <div class="metric-heading"><span>Tarefas atrasadas</span><strong>{{ data.overdue }}</strong></div>
          <p>{{ data.overdue ? 'Precisam de atenção imediata' : 'Nenhum prazo vencido agora' }}</p>
          <span class="metric-action">Ver no quadro <i class="fi fi-sr-arrow-up-right" aria-hidden="true"></i></span>
        </button>
      </section>

      <section class="overview-grid">
        <article class="panel progress-panel dashboard-animate">
          <header class="panel-header">
            <div>
              <span class="panel-kicker">Fluxo de trabalho</span>
              <h2>Progresso das entregas</h2>
            </div>
            <span class="panel-badge">{{ openTasks }} abertas</span>
          </header>

          <div class="progress-content">
            <div class="status-ring" :style="{ background: statusRing }" role="img" :aria-label="`${completionRate}% das tarefas concluídas`">
              <div class="status-ring-center">
                <strong>{{ completionRate }}%</strong>
                <span>concluído</span>
              </div>
            </div>

            <div class="status-legend">
              <div v-for="item in statusEntries" :key="item.label" class="legend-row">
                <span class="legend-dot" :style="{ background: item.color }"></span>
                <span class="legend-label">{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <span class="legend-percent">{{ percent(item.value) }}%</span>
              </div>
              <div class="completion-track" aria-hidden="true">
                <span class="bar-fill" :style="{ width: `${completionRate}%` }"></span>
              </div>
              <p>{{ completed }} de {{ total }} tarefas atravessaram todo o fluxo.</p>
            </div>
          </div>
        </article>

        <article class="panel priority-panel dashboard-animate">
          <header class="panel-header">
            <div>
              <span class="panel-kicker">Pressão da sprint</span>
              <h2>Prioridade e prazos</h2>
            </div>
            <i class="fi fi-sr-flag panel-header-icon" aria-hidden="true"></i>
          </header>

          <div class="signal-grid">
            <div class="signal-card">
              <i class="fi fi-sr-calendar-clock" aria-hidden="true"></i>
              <div><strong>{{ dueSoonTasks.length }}</strong><span>vencem em até 7 dias</span></div>
            </div>
            <div class="signal-card">
              <i class="fi fi-sr-user-slash" aria-hidden="true"></i>
              <div><strong>{{ unassignedTasks.length }}</strong><span>sem responsável</span></div>
            </div>
          </div>

          <div class="priority-list">
            <div v-for="item in priorityEntries" :key="item.label" class="priority-row">
              <div class="priority-row-label">
                <span><i class="priority-dot" :style="{ background: item.color }"></i>{{ item.label }}</span>
                <strong>{{ item.value }} <small>· {{ percent(item.value) }}%</small></strong>
              </div>
              <div class="thin-track"><span class="bar-fill" :style="{ width: `${percent(item.value)}%`, background: item.color }"></span></div>
            </div>
          </div>
        </article>
      </section>

      <section class="operations-grid">
        <article class="panel workload-panel dashboard-animate">
          <header class="panel-header">
            <div>
              <span class="panel-kicker">Capacidade do time</span>
              <h2>Carga por pessoa</h2>
            </div>
            <div class="workload-legend" aria-label="Legenda">
              <span><i class="legend-dot purple"></i>Abertas</span>
              <span><i class="legend-dot green"></i>Concluídas</span>
            </div>
          </header>

          <div v-if="workload.length" class="workload-table">
            <div class="workload-table-head" aria-hidden="true">
              <span>Pessoa</span><span>Distribuição</span><span>Progresso</span>
            </div>
            <div v-for="person in workload" :key="person.name" class="workload-row">
              <div class="person-cell">
                <span class="avatar">
                  <img v-if="person.photo" :src="person.photo" :alt="`Foto de ${person.name}`" />
                  <template v-else>{{ initials(person.name) }}</template>
                </span>
                <div><strong>{{ person.name }}</strong><span>{{ person.roles.join(' · ') || 'Sem cargo' }}</span></div>
              </div>
              <div class="workload-bar-cell">
                <div class="workload-numbers"><span>{{ person.open }} abertas</span><span>{{ person.done }} concluídas</span></div>
                <div class="stacked-track" aria-hidden="true">
                  <span class="bar-fill open" :style="{ width: `${(person.open / maxWorkload) * 100}%` }"></span>
                  <span class="bar-fill done" :style="{ width: `${(person.done / maxWorkload) * 100}%` }"></span>
                </div>
              </div>
              <div class="person-progress"><strong>{{ personCompletion(person) }}%</strong><span>concluído</span></div>
            </div>
          </div>
          <div v-else class="panel-empty"><i class="fi fi-sr-users" aria-hidden="true"></i>Nenhuma tarefa atribuída à equipe.</div>
        </article>

        <article class="panel attention-panel dashboard-animate">
          <header class="panel-header">
            <div>
              <span class="panel-kicker">Fila de atenção</span>
              <h2>Demandas críticas</h2>
            </div>
            <span v-if="attentionTasks.length" class="attention-count">{{ attentionTasks.length }}</span>
          </header>

          <div v-if="attentionTasks.length" class="attention-list">
            <button v-for="task in attentionTasks" :key="task.id" type="button" class="attention-item" @click="openTask(task)">
              <span class="attention-accent" :class="deadlineClass(task)"></span>
              <span class="attention-main">
                <span class="attention-title"><small>{{ task.code }}</small>{{ task.title }}</span>
                <span class="attention-meta">
                  <span :class="['deadline', deadlineClass(task)]"><i class="fi fi-sr-calendar-day" aria-hidden="true"></i>{{ formatDue(task) }}</span>
                  <span><i class="fi fi-sr-user" aria-hidden="true"></i>{{ task.assignee_name || 'Sem responsável' }}</span>
                </span>
              </span>
              <span :style="prioBadge(task.priority)">{{ task.priority }}</span>
              <i class="fi fi-sr-arrow-up-right open-icon" aria-hidden="true"></i>
            </button>
          </div>
          <div v-else class="healthy-state">
            <span><i class="fi fi-sr-check-circle" aria-hidden="true"></i></span>
            <strong>Fluxo sob controle</strong>
            <p>Não há tarefas atrasadas, de alta prioridade ou sem responsável.</p>
          </div>
        </article>
      </section>

      <section class="panel role-panel dashboard-animate">
        <header class="panel-header">
          <div>
            <span class="panel-kicker">Composição das demandas</span>
            <h2>Distribuição por cargo</h2>
          </div>
          <span class="panel-badge">{{ roleEntries.length }} especialidades</span>
        </header>

        <div v-if="roleEntries.length" class="role-grid">
          <div v-for="role in roleEntries" :key="role.label" class="role-item">
            <div class="role-icon"><i :class="`fi ${roleIcon(role.label)}`" aria-hidden="true"></i></div>
            <div class="role-info">
              <span><strong>{{ role.label }}</strong><small>{{ role.value }} {{ role.value === 1 ? 'tarefa' : 'tarefas' }}</small></span>
              <div class="thin-track"><span class="bar-fill" :style="{ width: `${percent(role.value)}%` }"></span></div>
            </div>
            <strong class="role-percent">{{ percent(role.value) }}%</strong>
          </div>
        </div>
        <div v-else class="panel-empty"><i class="fi fi-sr-briefcase" aria-hidden="true"></i>Nenhuma demanda por cargo ainda.</div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.dashboard-shell {
  --panel: #14141d;
  --border: #242432;
  --muted: #8f8da8;
  --text: #f5f4fb;
  padding: 22px 26px 32px;
  color: var(--text);
}

.dashboard-toolbar,
.panel-header,
.metric-heading,
.legend-row,
.priority-row-label,
.workload-numbers {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dashboard-toolbar { gap: 20px; margin-bottom: 14px; }
.dashboard-toolbar p { margin: 5px 0 0; color: var(--muted); font-size: 12px; }
.eyebrow,
.panel-kicker { color: #aaa6c5; font-size: 10px; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
.eyebrow { display: inline-flex; align-items: center; gap: 6px; color: #b8b1ff; }

.refresh-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex: none;
  min-height: 34px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: #111118;
  color: #aaa7bf;
  font: inherit;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition-property: border-color, color, background-color;
  transition-duration: 150ms;
}
.refresh-button:hover:not(:disabled) { border-color: #39384b; background: #171720; color: #d8d5e9; }
.refresh-button:disabled { cursor: wait; opacity: .7; }
.spinning { animation: dashboard-spin .8s linear infinite; }

.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 11px; margin-bottom: 14px; }
.metric-card,
.panel { border: 1px solid var(--border); background: linear-gradient(145deg, rgba(255,255,255,.012), transparent 42%), var(--panel); box-shadow: 0 12px 30px rgba(0, 0, 0, .12); }
.metric-card { position: relative; min-width: 0; padding: 14px; border-radius: 12px; overflow: hidden; }
.metric-card--button { color: inherit; font: inherit; text-align: start; cursor: pointer; transition-property: border-color, background-color, transform; transition-duration: 150ms; }
.metric-card--button:focus-visible { outline: 2px solid #b3aaff; outline-offset: 3px; }
.metric-action { display: inline-flex; align-items: center; gap: 5px; margin-top: 10px; color: #a8a1f2; font-size: 9.5px; font-weight: 800; }
.metric-action i { font-size: 8px; }
.metric-card::after { content: ''; position: absolute; inset: auto 0 0; height: 2px; background: linear-gradient(90deg, transparent, rgba(124,111,255,.45), transparent); opacity: 0; }
.metric-card--alert { border-color: rgba(232,93,106,.28); }
.metric-card--alert::after { opacity: 1; background: linear-gradient(90deg, transparent, rgba(232,93,106,.65), transparent); }
.metric-icon { display: grid; place-items: center; width: 30px; height: 30px; margin-bottom: 14px; border: 1px solid transparent; border-radius: 9px; font-size: 13px; }
.metric-icon.neutral { color: #c2bfd5; background: rgba(154,154,176,.1); border-color: rgba(154,154,176,.14); }
.metric-icon.purple { color: #b3aaff; background: rgba(124,111,255,.12); border-color: rgba(124,111,255,.2); }
.metric-icon.green { color: #6fe3a4; background: rgba(63,207,142,.1); border-color: rgba(63,207,142,.18); }
.metric-icon.red { color: #ff8f98; background: rgba(232,93,106,.1); border-color: rgba(232,93,106,.18); }
.metric-heading { align-items: flex-end; gap: 12px; }
.metric-heading span { color: #aaa7bf; font-size: 11.5px; font-weight: 700; }
.metric-heading strong { color: var(--text); font-size: 24px; line-height: 1; letter-spacing: -.035em; }
.metric-card p { margin: 7px 0 0; color: #77758d; font-size: 10.5px; line-height: 1.4; }

@media (hover: hover) and (pointer: fine) {
  .metric-card--button:hover { transform: translateY(-1px); border-color: rgba(232,93,106,.48); background-color: #181720; }
}

.overview-grid,
.operations-grid { display: grid; gap: 14px; margin-bottom: 14px; }
.overview-grid { grid-template-columns: minmax(0, 1.2fr) minmax(300px, .8fr); }
.operations-grid { grid-template-columns: minmax(0, 1.35fr) minmax(330px, .65fr); align-items: start; }
.panel { min-width: 0; border-radius: 13px; padding: 17px; }
.panel-header { gap: 12px; margin-bottom: 17px; }
.panel-header h2 { margin: 4px 0 0; font-size: 14px; line-height: 1.2; letter-spacing: -.01em; }
.panel-badge,
.attention-count { padding: 5px 8px; border: 1px solid #292838; border-radius: 7px; background: #101017; color: #aaa7bf; font-size: 10.5px; font-weight: 800; }
.panel-header-icon { color: #77738e; font-size: 15px; }

.progress-content { display: grid; grid-template-columns: 158px minmax(0, 1fr); gap: 24px; align-items: center; min-height: 190px; }
.status-ring { display: grid; place-items: center; width: 150px; height: 150px; border-radius: 50%; box-shadow: 0 0 34px rgba(124,111,255,.08); }
.status-ring-center { display: grid; place-content: center; width: 112px; height: 112px; border: 1px solid #242432; border-radius: 50%; background: #111118; text-align: center; }
.status-ring-center strong { font-size: 28px; letter-spacing: -.05em; }
.status-ring-center span { margin-top: 2px; color: var(--muted); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
.status-legend { min-width: 0; }
.legend-row { gap: 8px; min-height: 30px; border-bottom: 1px solid rgba(255,255,255,.035); font-size: 11.5px; }
.legend-row:last-of-type { border-bottom: 0; }
.legend-dot { display: inline-block; width: 7px; height: 7px; flex: none; border-radius: 50%; }
.legend-label { flex: 1; color: #c7c5dc; }
.legend-row strong { min-width: 22px; text-align: end; }
.legend-percent { min-width: 34px; color: #77758d; text-align: end; }
.completion-track,
.thin-track,
.stacked-track { overflow: hidden; border-radius: 999px; background: #0d0d13; }
.completion-track { height: 7px; margin-top: 14px; }
.completion-track span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #6659ed, #57d79a); }
.status-legend p { margin: 8px 0 0; color: #77758d; font-size: 10.5px; }

.signal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin-bottom: 18px; }
.signal-card { display: flex; align-items: center; gap: 10px; padding: 11px; border: 1px solid #22222f; border-radius: 10px; background: #101017; }
.signal-card > i { display: grid; place-items: center; width: 28px; height: 28px; flex: none; border-radius: 8px; background: rgba(124,111,255,.1); color: #aaa1ff; font-size: 12px; }
.signal-card div { min-width: 0; }
.signal-card strong { display: block; font-size: 17px; line-height: 1; }
.signal-card span { display: block; margin-top: 4px; color: #858299; font-size: 9.5px; white-space: nowrap; }
.priority-list { display: grid; gap: 12px; }
.priority-row-label { margin-bottom: 6px; font-size: 11px; }
.priority-row-label > span { display: inline-flex; align-items: center; gap: 7px; color: #bbb8ce; }
.priority-dot { width: 6px; height: 6px; border-radius: 50%; }
.priority-row-label strong { font-size: 11px; }
.priority-row-label small { color: #77758d; font-size: 10px; font-weight: 600; }
.thin-track { height: 6px; }
.thin-track span { display: block; height: 100%; border-radius: inherit; }

.workload-legend { display: flex; align-items: center; gap: 12px; color: #858299; font-size: 9.5px; }
.workload-legend span { display: inline-flex; align-items: center; gap: 5px; }
.legend-dot.purple { background: #7c6fff; }
.legend-dot.green { background: #3fcf8e; }
.workload-table { min-width: 0; }
.workload-table-head,
.workload-row { display: grid; grid-template-columns: minmax(145px, .8fr) minmax(160px, 1.15fr) 58px; gap: 15px; align-items: center; }
.workload-table-head { padding: 0 10px 8px; color: #686679; font-size: 9px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.workload-table-head span:last-child { text-align: end; }
.workload-row { min-height: 53px; padding: 7px 10px; border-top: 1px solid rgba(255,255,255,.045); }
.person-cell { display: flex; align-items: center; gap: 9px; min-width: 0; }
.avatar { display: grid; place-items: center; width: 29px; height: 29px; flex: none; border: 1px solid rgba(124,111,255,.22); border-radius: 50%; background: rgba(124,111,255,.12); color: #c3bcff; font-size: 9.5px; font-weight: 800; }
.avatar img { width: 100%; height: 100%; border-radius: inherit; object-fit: cover; display: block; }
.person-cell div { min-width: 0; }
.person-cell strong,
.person-cell span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.person-cell strong { color: #dddbea; font-size: 11px; }
.person-cell div span { margin-top: 3px; color: #77758d; font-size: 9px; }
.workload-bar-cell { min-width: 0; }
.workload-numbers { margin-bottom: 6px; color: #858299; font-size: 9px; }
.stacked-track { display: flex; height: 7px; }
.stacked-track span { display: block; height: 100%; }
.stacked-track .open { background: #7c6fff; }
.stacked-track .done { background: #3fcf8e; }
.person-progress { text-align: end; }
.person-progress strong { display: block; font-size: 12px; }
.person-progress span { display: block; margin-top: 3px; color: #6e6c80; font-size: 8.5px; }

.attention-panel { padding-bottom: 9px; }
.attention-count { border-color: rgba(232,93,106,.25); background: rgba(232,93,106,.09); color: #ff9ba3; }
.attention-list { margin-inline: -8px; }
.attention-item { position: relative; display: grid; grid-template-columns: 3px minmax(0, 1fr) auto 13px; gap: 9px; align-items: center; width: 100%; padding: 9px 8px; border: 0; border-radius: 9px; background: transparent; color: inherit; font: inherit; text-align: start; cursor: pointer; transition-property: background-color; transition-duration: 150ms; }
.attention-item:hover { background: rgba(255,255,255,.035); }
.attention-accent { width: 3px; height: 34px; border-radius: 999px; background: #77758d; }
.attention-accent.danger { background: #e85d6a; }
.attention-accent.warning { background: #e0a23c; }
.attention-main { min-width: 0; }
.attention-title { display: block; overflow: hidden; color: #dcd9e9; font-size: 10.5px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.attention-title small { margin-inline-end: 6px; color: #77758d; font-size: 8.5px; }
.attention-meta { display: flex; gap: 10px; margin-top: 6px; color: #77758d; font-size: 8.5px; }
.attention-meta > span { display: inline-flex; align-items: center; gap: 4px; min-width: 0; }
.deadline.danger { color: #ff8f98; }
.deadline.warning { color: #ffc26b; }
.open-icon { color: #625f75; font-size: 9px; }
.attention-item:hover .open-icon { color: #b3aaff; }
.healthy-state { display: grid; justify-items: center; padding: 24px 12px 28px; text-align: center; }
.healthy-state > span { display: grid; place-items: center; width: 40px; height: 40px; margin-bottom: 12px; border: 1px solid rgba(63,207,142,.2); border-radius: 12px; background: rgba(63,207,142,.09); color: #6fe3a4; }
.healthy-state strong { font-size: 12px; }
.healthy-state p { max-width: 240px; margin: 6px 0 0; color: #77758d; font-size: 10px; line-height: 1.5; }

.role-panel { margin-bottom: 0; }
.role-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; }
.role-item { display: grid; grid-template-columns: 32px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 10px; border: 1px solid #22222f; border-radius: 10px; background: #101017; }
.role-icon { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 9px; background: rgba(124,111,255,.1); color: #aaa1ff; font-size: 12px; }
.role-info { min-width: 0; }
.role-info > span { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 7px; }
.role-info strong { overflow: hidden; color: #ccc9dc; font-size: 10.5px; text-overflow: ellipsis; white-space: nowrap; }
.role-info small { flex: none; color: #6f6c81; font-size: 8.5px; }
.role-info .bar-fill { background: linear-gradient(90deg, #6559e7, #8b80ff); }
.role-percent { color: #928da9; font-size: 10px; }

.panel-empty { display: flex; align-items: center; justify-content: center; gap: 8px; min-height: 100px; color: #77758d; font-size: 11px; }
.dashboard-loading { display: flex; align-items: center; justify-content: center; gap: 13px; min-height: 340px; color: #bdbacf; }
.dashboard-loading strong,
.dashboard-loading span { display: block; }
.dashboard-loading strong { font-size: 12px; }
.dashboard-loading span { margin-top: 4px; color: #77758d; font-size: 10.5px; }
.dashboard-loader { width: 22px; height: 22px; border: 2px solid #2a2938; border-top-color: #7c6fff; border-radius: 50%; animation: dashboard-spin .8s linear infinite; }
.dashboard-error { display: flex; align-items: center; gap: 12px; padding: 15px; border: 1px solid rgba(232,93,106,.32); border-radius: 12px; background: rgba(232,93,106,.09); color: #ff9ca4; }
.dashboard-error > i { font-size: 16px; }
.dashboard-error div { flex: 1; }
.dashboard-error strong,
.dashboard-error span { display: block; }
.dashboard-error strong { font-size: 12px; }
.dashboard-error span { margin-top: 3px; color: #c8868c; font-size: 10.5px; }
.dashboard-error button { min-height: 32px; padding: 0 10px; border: 1px solid rgba(232,93,106,.3); border-radius: 8px; background: rgba(0,0,0,.15); color: #ffadb4; font: inherit; font-size: 10.5px; font-weight: 700; cursor: pointer; }

@keyframes dashboard-spin { to { transform: rotate(360deg); } }

@media (max-width: 920px) {
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .overview-grid,
  .operations-grid { grid-template-columns: 1fr; }
  .role-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 620px) {
  .dashboard-shell { padding-inline: 16px; }
  .dashboard-toolbar { align-items: flex-start; flex-direction: column; gap: 12px; }
  .metric-grid { grid-template-columns: 1fr; }
  .progress-content { grid-template-columns: 1fr; justify-items: center; }
  .status-legend { width: 100%; }
  .signal-grid,
  .role-grid { grid-template-columns: 1fr; }
  .workload-table-head { display: none; }
  .workload-row { grid-template-columns: minmax(0, 1fr) 52px; gap: 12px; padding-block: 11px; }
  .workload-bar-cell { grid-column: 1 / -1; grid-row: 2; }
  .person-progress { grid-column: 2; grid-row: 1; }
  .workload-legend { display: none; }
  .attention-item { grid-template-columns: 3px minmax(0, 1fr) 13px; }
  .attention-item > [style] { display: none !important; }
}

@media (prefers-reduced-motion: reduce) {
  .spinning,
  .dashboard-loader { animation: none; }
}
</style>
