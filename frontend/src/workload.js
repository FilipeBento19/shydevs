import { reactive } from 'vue'
import { api } from './api'
import { auth } from './auth'

// How many unfinished tasks the logged-in person has; drives the noob's glitch.
export const workload = reactive({ count: 0, completions: 0 })

export async function refreshWorkload() {
  const me = auth.state.person?.id
  if (!me) { workload.count = 0; return }
  try {
    const tasks = await api.getTasks()
    workload.count = tasks.filter((t) => t.assignee === me && t.status !== 'Concluída').length
  } catch (e) {
    // keep the last known count
  }
}

// A task was just completed: recount, and let the noob celebrate with a spin.
window.addEventListener('shydevs:task-completed', () => {
  workload.completions++
  refreshWorkload()
})
