import { ref } from 'vue'

// Bumped whenever a task is created/edited/deleted anywhere in the app so
// independent pages (board, task page) know to refetch without being
// forced into the same component tree.
export const tasksVersion = ref(0)

export function bumpTasks() {
  tasksVersion.value++
}
