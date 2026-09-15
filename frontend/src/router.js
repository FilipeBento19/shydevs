import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './views/HomePage.vue'
import BoardPage from './views/BoardPage.vue'
import TaskPage from './views/TaskPage.vue'
import NewTaskPage from './views/NewTaskPage.vue'
import DashboardView from './components/DashboardView.vue'
import HistoryView from './components/HistoryView.vue'
import TeamView from './components/TeamView.vue'
import { auth } from './auth'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage,
    meta: { nav: 'home', title: 'ShyDevs' },
  },
  {
    path: '/board',
    name: 'board',
    component: BoardPage,
    meta: { nav: 'board', title: 'Atribuição de Tarefas' },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView,
    meta: { nav: 'dashboard', title: 'Dashboard do Time', subtitle: 'Acompanhe a carga de trabalho e o progresso do time em tempo real.', requiresAuth: true },
  },
  {
    path: '/history',
    name: 'history',
    component: HistoryView,
    meta: { nav: 'history', title: 'Histórico de Atividades', subtitle: 'Tudo que aconteceu nas tarefas do projeto.', requiresAuth: true },
  },
  {
    path: '/team',
    name: 'team',
    component: TeamView,
    meta: { nav: 'team', title: 'Gestão de Equipe', subtitle: 'Adicione ou remova pessoas da equipe.', adminOnly: true },
  },
  {
    path: '/tasks/new',
    name: 'new-task',
    component: NewTaskPage,
    meta: { nav: null, title: 'Atribuir Nova Tarefa', adminOnly: true },
  },
  {
    path: '/tasks/:id',
    name: 'task',
    component: TaskPage,
    props: true,
    meta: { nav: null, title: 'Detalhes da Tarefa', requiresAuth: true },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  if (to.meta.adminOnly && !auth.state.person?.is_admin) {
    return { name: 'board' }
  }
  if (to.meta.requiresAuth && !auth.state.person) {
    return { name: 'board' }
  }
})
