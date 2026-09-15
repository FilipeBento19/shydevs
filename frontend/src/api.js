const BASE = '/api'

function authHeaders() {
  const token = localStorage.getItem('shydevs_token')
  return token ? { Authorization: `Token ${token}` } : {}
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
  return res.json()
}

function qs(params = {}) {
  const s = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  ).toString()
  return s ? `?${s}` : ''
}

export const api = {
  // auth
  login: (name, password) =>
    request('/auth/login/', { method: 'POST', body: JSON.stringify({ name, password }) }),
  logout: () => request('/auth/logout/', { method: 'POST' }),
  me: () => request('/auth/me/'),

  // roles / balance / dashboard
  getRoles: () => request('/tasks/roles/'),
  getBalance: () => request('/tasks/balance/'),
  getDashboard: () => request('/tasks/dashboard/'),

  // people
  getPeople: () => request('/people/'),
  createPerson: (data) => request('/people/', { method: 'POST', body: JSON.stringify(data) }),
  updatePerson: (id, data) => request(`/people/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
  deletePerson: (id) => request(`/people/${id}/`, { method: 'DELETE' }),
  uploadPersonPhoto: (id, file) => {
    const fd = new FormData()
    fd.append('photo', file)
    return request(`/people/${id}/photo/`, { method: 'POST', body: fd })
  },

  // tasks
  getTasks: (params = {}) => request(`/tasks/${qs(params)}`),
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
  getActivities: (taskId) => request(`/activities/${qs({ task: taskId })}`),

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

  // project settings
  getSettings: () => request('/settings/'),
  updateSettings: (data) => request('/settings/', { method: 'PATCH', body: JSON.stringify(data) }),
}
