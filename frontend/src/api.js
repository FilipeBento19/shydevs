// In dev, Vite proxies '/api' to the local Django server (see vite.config.js).
// In production (Vercel), set VITE_API_BASE_URL to the deployed backend, e.g.
// https://shydevs-backend.onrender.com/api
const BASE = import.meta.env.VITE_API_BASE_URL || '/api'

function authHeaders() {
  const token = localStorage.getItem('shydevs_token')
  return token ? { Authorization: `Token ${token}` } : {}
}

// Read directly from storage (not the project store module) to avoid a
// circular import — the project store itself calls into this file.
function currentProjectId() {
  try {
    const raw = JSON.parse(localStorage.getItem('shydevs_project') || 'null')
    return raw?.id ?? null
  } catch (e) {
    return null
  }
}

async function request(path, options = {}) {
  const isForm = options.body instanceof FormData
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      ...(isForm ? {} : { 'Content-Type': 'application/json' }),
      ...authHeaders(),
      ...(options.headers || {}),
    },
    ...options,
  })
  if (!res.ok) {
    let detail = ''
    try {
      const data = await res.json()
      detail = data.detail || JSON.stringify(data)
    } catch (e) {
      detail = await res.text()
    }
    const err = new Error(detail || `API error ${res.status}`)
    err.status = res.status
    throw err
  }
  if (res.status === 204) return null
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    // Most likely VITE_API_BASE_URL is missing/wrong and this request landed on
    // the frontend's own domain (e.g. Vercel's SPA fallback returning index.html).
    console.error(
      `[api] Esperava JSON de ${BASE}${path} mas recebi "${contentType || 'sem content-type'}". ` +
      'Verifique se VITE_API_BASE_URL aponta para o backend correto.'
    )
    const err = new Error('Resposta inesperada do servidor (não é JSON). Confira a configuração de VITE_API_BASE_URL.')
    err.status = res.status
    throw err
  }
  return res.json()
}

function qs(params = {}) {
  const s = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  ).toString()
  return s ? `?${s}` : ''
}

export const api = {
  // projects
  getProjects: () => request('/projects/'),
  createProject: (data) => request('/projects/', { method: 'POST', body: JSON.stringify(data) }),
  updateProject: (id, data) => request(`/projects/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),

  // auth
  login: (name, password, projectId) =>
    request('/auth/login/', { method: 'POST', body: JSON.stringify({ name, password, project: projectId }) }),
  logout: () => request('/auth/logout/', { method: 'POST' }),
  me: () => request('/auth/me/'),

  // roles / balance / dashboard
  getRoles: () => request(`/roles/${qs({ project: currentProjectId() })}`),
  createRole: (data) => request('/roles/', { method: 'POST', body: JSON.stringify(data) }),
  updateRole: (id, data) => request(`/roles/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteRole: (id) => request(`/roles/${id}/`, { method: 'DELETE' }),
  getBalance: () => request(`/tasks/balance/${qs({ project: currentProjectId() })}`),
  getDashboard: () => request('/tasks/dashboard/'),

  // people
  getPeople: () => request(`/people/${qs({ project: currentProjectId() })}`),
  createPerson: (data) => request('/people/', { method: 'POST', body: JSON.stringify(data) }),
  updatePerson: (id, data) => request(`/people/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deletePerson: (id) => request(`/people/${id}/`, { method: 'DELETE' }),
  uploadPersonPhoto: (id, file) => {
    const fd = new FormData()
    fd.append('photo', file)
    return request(`/people/${id}/photo/`, { method: 'POST', body: fd })
  },
  changePassword: (id, password) =>
    request(`/people/${id}/change-password/`, { method: 'POST', body: JSON.stringify({ password }) }),
  startDiscordVerification: (id) =>
    request(`/people/${id}/discord-verification/`, { method: 'POST' }),
  getDiscordVerification: (id) => request(`/people/${id}/discord-verification/`),
  sendDiscordMessage: (personIds, message) =>
    request('/people/send-discord-message/', { method: 'POST', body: JSON.stringify({ person_ids: personIds, message }) }),
  getDiscordMessages: () => request('/discord-messages/'),

  // tasks
  getTasks: (params = {}) => request(`/tasks/${qs({ project: currentProjectId(), ...params })}`),
  getTask: (id) => request(`/tasks/${id}/`),
  createTask: (data) => request('/tasks/', { method: 'POST', body: JSON.stringify(data) }),
  updateTask: (id, data) =>
    request(`/tasks/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteTask: (id) => request(`/tasks/${id}/`, { method: 'DELETE' }),
  bulkUpdateTasks: (ids, fields) =>
    request('/tasks/bulk_update/', { method: 'POST', body: JSON.stringify({ ids, fields }) }),
  bulkDeleteTasks: (ids) =>
    request('/tasks/bulk-delete/', { method: 'DELETE', body: JSON.stringify({ ids }) }),

  // subtasks
  getSubtasks: (taskId) => request(`/subtasks/${qs({ task: taskId })}`),
  createSubtask: (data) => request('/subtasks/', { method: 'POST', body: JSON.stringify(data) }),
  updateSubtask: (id, data) =>
    request(`/subtasks/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSubtask: (id) => request(`/subtasks/${id}/`, { method: 'DELETE' }),

  // activities
  getActivities: (taskId, scope = 'normal') => request(`/activities/${qs({ task: taskId, scope })}`),

  // comments
  getComments: (taskId) => request(`/comments/${qs({ task: taskId })}`),
  createComment: (data) => request('/comments/', { method: 'POST', body: JSON.stringify(data) }),
  deleteComment: (id) => request(`/comments/${id}/`, { method: 'DELETE' }),

  // attachments
  getAttachments: (taskId) => request(`/attachments/${qs({ task: taskId })}`),
  createAttachment: (data) => {
    if (data.file) {
      const fd = new FormData()
      Object.entries(data).forEach(([k, v]) => {
        if (v !== null && v !== undefined && v !== '') fd.append(k, v)
      })
      return request('/attachments/', { method: 'POST', body: fd })
    }
    return request('/attachments/', { method: 'POST', body: JSON.stringify(data) })
  },
  deleteAttachment: (id) => request(`/attachments/${id}/`, { method: 'DELETE' }),

  // references (grouped links + files for a task)
  getReferences: (taskId) => request(`/references/${qs({ task: taskId, project: currentProjectId() })}`),
  createReference: (data) => {
    const fd = new FormData()
    Object.entries(data).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '') fd.append(k, v)
    })
    return request('/references/', { method: 'POST', body: fd })
  },
  deleteReference: (id) => request(`/references/${id}/`, { method: 'DELETE' }),
}
