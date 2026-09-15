import { reactive } from 'vue'
import { api } from './api'
import { auth } from './auth'

const state = reactive({
  current: JSON.parse(localStorage.getItem('shydevs_project') || 'null'),
  list: [],
  loaded: false,
})

function persist() {
  if (state.current) localStorage.setItem('shydevs_project', JSON.stringify(state.current))
  else localStorage.removeItem('shydevs_project')
}

export const project = {
  state,

  async loadList() {
    try {
      state.list = await api.getProjects()
    } catch (e) {
      // keep whatever we had
    } finally {
      state.loaded = true
    }
  },

  // Called once at boot: makes sure there's always a current project selected
  // when exactly one exists (the common single-studio case), and keeps the
  // header's project in sync with an already-logged-in person's own project
  // (e.g. after a refresh where local storage still has a valid token).
  async ensureSelected() {
    if (!state.loaded) await this.loadList()

    if (auth.isLoggedIn && auth.state.person?.project) {
      const own = state.list.find((p) => p.id === auth.state.person.project)
      if (own && state.current?.id !== own.id) {
        state.current = { id: own.id, name: own.name }
        persist()
      }
      return
    }

    if (state.current && state.list.some((p) => p.id === state.current.id)) return
    if (state.list.length === 1) {
      this.select(state.list[0])
    } else if (state.current && !state.list.some((p) => p.id === state.current.id)) {
      state.current = null
      persist()
    }
  },

  select(proj) {
    if (state.current?.id === proj.id) return
    if (auth.isLoggedIn) auth.logout()
    state.current = { id: proj.id, name: proj.name }
    persist()
  },

  async create(name, adminName, adminPassword) {
    const created = await api.createProject({ name, admin_name: adminName, admin_password: adminPassword })
    await this.loadList()
    this.select(created)
    return created
  },

  async rename(name) {
    if (!state.current) return
    const updated = await api.updateProject(state.current.id, { name })
    state.current = { id: updated.id, name: updated.name }
    persist()
    await this.loadList()
  },
}
