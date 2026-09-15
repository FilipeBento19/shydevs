const MONTHS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

export function initials(name) {
  if (!name) return '--'
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

function startOfDay(d) {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x
}

export function isLate(task) {
  if (!task.due_date || task.status === 'Concluída') return false
  const due = startOfDay(new Date(`${task.due_date}T00:00:00`))
  return due < startOfDay(new Date())
}

export function formatDue(task) {
  if (!task.due_date) return '—'
  const due = startOfDay(new Date(`${task.due_date}T00:00:00`))
  const today = startOfDay(new Date())
  const diffDays = Math.round((due - today) / 86400000)
  const late = isLate(task)

  if (task.status === 'Concluída') return 'Concluída'
  if (diffDays === 0) return 'Hoje'
  if (diffDays === 1) return 'Amanhã'
  if (diffDays === -1) return 'Ontem (Atrasada)'

  const label = `${due.getDate()} de ${MONTHS[due.getMonth()]}`
  return late ? `${label} (Atrasada)` : label
}

export function chipStyle(active, color = '#7c6fff') {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '7px',
    borderRadius: '999px',
    padding: '7px 13px',
    fontSize: '12px',
    fontWeight: '700',
    cursor: 'pointer',
    border: `1px solid ${active ? color : '#26263a'}`,
    background: active ? color : '#14141d',
    color: active ? '#0a0a10' : '#c7c5dc',
  }
}

export function tabStyle(active, color = '#7c6fff') {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    borderRadius: '8px',
    padding: '7px 12px',
    fontSize: '12px',
    fontWeight: '700',
    cursor: 'pointer',
    border: `1px solid ${active ? color : '#26263a'}`,
    background: active ? color : '#14141d',
    color: active ? '#0a0a10' : '#c7c5dc',
  }
}

const PRIO_MAP = {
  Alta: { background: 'rgba(224,79,95,.16)', color: '#ff8f98' },
  Média: { background: 'rgba(224,162,60,.16)', color: '#ffc26b' },
  Baixa: { background: 'rgba(154,154,176,.14)', color: '#b8b6d1' },
}

const STATUS_MAP = {
  'Em andamento': { background: 'rgba(124,111,255,.18)', color: '#b3aaff' },
  Pendente: { background: 'rgba(154,154,176,.12)', color: '#adaac8' },
  Concluída: { background: 'rgba(70,180,120,.16)', color: '#6fe3a4' },
}

export function badgeStyle(map, key) {
  return {
    display: 'inline-flex',
    borderRadius: '6px',
    padding: '4px 9px',
    fontSize: '11px',
    fontWeight: '700',
    ...(map[key] || {}),
  }
}

export const prioBadge = (p) => badgeStyle(PRIO_MAP, p)
export const statusBadge = (s) => badgeStyle(STATUS_MAP, s)

const ROLE_ICONS = {
  Modelador: 'fi-sr-model-cube',
  Scripter: 'fi-sr-code-simple',
  'Vfx Maker': 'fi-sr-sparkles',
  'Ui Maker': 'fi-sr-palette',
  Manager: 'fi-sr-briefcase',
  'SFX Maker': 'fi-sr-music',
}

export function roleIcon(role) {
  return ROLE_ICONS[role] || 'fi-sr-user'
}

const STATUS_ICONS = {
  'Em andamento': 'fi-sr-time-oclock',
  Pendente: 'fi-sr-hourglass-end',
  Concluída: 'fi-sr-check-circle',
}

export function statusIcon(status) {
  return STATUS_ICONS[status] || 'fi-sr-circle'
}
