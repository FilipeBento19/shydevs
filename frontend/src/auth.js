import { reactive } from 'vue'
import { api } from './api'

const state = reactive({
  token: localStorage.getItem('shydevs_token') || null,
  person: JSON.parse(localStorage.getItem('shydevs_person') || 'null'),
})

function persist() {
  if (state.token) localStorage.setItem('shydevs_token', state.token)
  else localStorage.removeItem('shydevs_token')
  if (state.person) localStorage.setItem('shydevs_person', JSON.stringify(state.person))
  else localStorage.removeItem('shydevs_person')
}

export const auth = {
  state,
  get isLoggedIn() {
    return !!state.token
  },
  async login(name, password) {
    const res = await api.login(name, password)
    state.token = res.token
    state.person = res.person
    persist()
    return res.person
  },
  async logout() {
    const logoutRequest = api.logout()
    state.token = null
    state.person = null
    persist()
    try {
      await logoutRequest
    } catch (e) {
      // token might already be invalid; the local session is already clear
    }
  },
  setPerson(person) {
    state.person = person
    persist()
  },
}
