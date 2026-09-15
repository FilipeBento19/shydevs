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

  // Called once at boot: keeps the header's project in sync with an
  // already-logged-in person's own project (e.g. after a refresh where
  // local storage still has a valid token), and otherwise defaults anyone
  // who hasn't picked one yet to the oldest project — "the first one".
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
    if (state.list.length > 0) {
      const oldest = [...state.list].sort((a, b) => a.id - b.id)[0]
      state.current = { id: oldest.id, name: oldest.name }
      persist()
    } else if (state.current) {
      state.current = null
      persist()
    }
  },

  // The other projects a person could switch to — used to decide whether
  // the switcher has anything to show someone who isn't an admin.
  get otherProjects() {
    return state.list.filter((p) => p.id !== state.current?.id)
  },

  select(proj) {
    if (state.current?.id === proj.id) return
    if (auth.isLoggedIn) auth.logout()
    state.current = { id: proj.id, name: proj.name }
    persist()
  },

  // Admin-only: spins up a new project and, since the creator doesn't have
  // an account there yet, the backend clones their own (same name/password
  // hash) as that project's first admin and hands back a ready session.
  async create(name) {
    const res = await api.createProject({ name })
    await this.loadList()
    state.current = { id: res.project.id, name: res.project.name }
    persist()
    auth.setSession(res.token, res.person)
    return res.project
  },

  async rename(name) {
    if (!state.current) return
    const updated = await api.updateProject(state.current.id, { name })
    state.current = { id: updated.id, name: updated.name }
    persist()
    await this.loadList()
  },
}
