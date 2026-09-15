<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'
import { gsap, popEnter, popLeave, reduceMotion } from '../motion'
import { mascotFaceStyle, personAvatarStyle, mascot } from '../mascotFace'
import { bumpTasks } from '../taskBus'
import SlidingTabs from './SlidingTabs.vue'
import LoginModal from './LoginModal.vue'

const route = useRoute()
const router = useRouter()

function goCreate() {
  router.push({ name: 'new-task' })
}

const canEdit = computed(() => !!auth.state.person?.is_admin)

const BASE_NAV_ITEMS = [
  { key: 'home', label: 'Home', icon: 'fi-sr-home' },
  { key: 'board', label: 'Quadro de Tarefas', icon: 'fi-sr-table-list' },
]
const navItems = computed(() => {
  const items = auth.isLoggedIn
    ? [...BASE_NAV_ITEMS, { key: 'dashboard', label: 'Dashboard', icon: 'fi-sr-chart-simple' }, { key: 'history', label: 'Histórico', icon: 'fi-sr-clock' }]
    : BASE_NAV_ITEMS
  return canEdit.value ? [...items, { key: 'team', label: 'Equipe', icon: 'fi-sr-users' }] : items
})
const activeNav = computed(() => route.meta.nav || 'board')

function goNav(key) {
  router.push({ name: key })
}

// ---- project name ----
const projectName = ref('Slayer Reborn')
const editingName = ref(false)
const nameDraft = ref('')
const savingName = ref(false)

async function loadSettings() {
  try {
    const s = await api.getSettings()
    projectName.value = s.name
  } catch (e) {
    // keep default
  }
}
onMounted(loadSettings)

function startEditName() {
  if (!canEdit.value) return
  nameDraft.value = projectName.value
  editingName.value = true
}
async function saveName() {
  const name = nameDraft.value.trim()
  if (!name || name === projectName.value) {
    editingName.value = false
    return
  }
  savingName.value = true
  try {
    const s = await api.updateSettings({ name })
    projectName.value = s.name
  } catch (e) {
    // ignore, keep previous
  } finally {
    savingName.value = false
    editingName.value = false
  }
}

// ---- login/account ----
const loginOpen = ref(false)
const accountOpen = ref(false)

function logout() {
  auth.logout()
  accountOpen.value = false
}
async function onPhotoChange(e) {
  const file = e.target.files[0]
  if (!file || !auth.state.person) return
  try {
    const updated = await api.uploadPersonPhoto(auth.state.person.id, file)
    auth.setPerson(updated)
    bumpTasks()
  } catch (err) {
    // ignore
  }
}

// ---- change password ----
const changingPassword = ref(false)
const newPasswordDraft = ref('')
const savingPassword = ref(false)
const passwordSaved = ref(false)

function startChangePassword() {
  newPasswordDraft.value = ''
  passwordSaved.value = false
  changingPassword.value = true
}
async function savePassword() {
  const password = newPasswordDraft.value
  if (!password || !auth.state.person) return
  savingPassword.value = true
  try {
    await api.changePassword(auth.state.person.id, password)
    passwordSaved.value = true
    newPasswordDraft.value = ''
    setTimeout(() => {
      changingPassword.value = false
      passwordSaved.value = false
    }, 1200)
  } catch (err) {
    // ignore
  } finally {
    savingPassword.value = false
  }
}

watch(accountOpen, (open) => {
  if (!open) changingPassword.value = false
})

function onDocClick(e) {
  if (accountOpen.value && !e.target.closest('.account-menu')) accountOpen.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))

// ---- confetti easter egg ----
function goHome(e) {
  confettiBurst(e)
  if (route.name !== 'home') router.push({ name: 'home' })
}
function confettiBurst(e) {
  if (reduceMotion) return
  const originX = e.clientX
  const originY = e.clientY
  const colors = ['#7c6fff', '#3fcf8e', '#ffc26b', '#ff8f98', '#6fb3ff']
  const count = 18
  for (let i = 0; i < count; i++) {
    const d = document.createElement('div')
    d.style.cssText = `position:fixed; left:${originX}px; top:${originY}px; width:6px; height:6px; border-radius:50%; background:${colors[i % colors.length]}; pointer-events:none; z-index:200;`
    document.body.appendChild(d)
    const angle = (i / count) * Math.PI * 2
    const dist = 55 + Math.random() * 55
    gsap.to(d, {
      x: Math.cos(angle) * dist, y: Math.sin(angle) * dist - 16, opacity: 0,
      duration: 0.7 + Math.random() * 0.4, ease: 'power2.out',
      onComplete: () => d.remove(),
    })
  }
}
function bounce(e) {
  if (reduceMotion) return
  gsap.fromTo(e.currentTarget, { scale: 0.92 }, { scale: 1, duration: 0.35, ease: 'back.out(4)' })
}

defineExpose({ mascot })
</script>

<template>
  <div style="display:flex; align-items:center; gap:14px; padding:10px 16px; background:#0b0b11; flex-wrap:wrap;">
    <button type="button" @click="goHome" aria-label="ShyDevs — ir para o início" style="display:flex; align-items:center; gap:8px; padding:0 4px 0 0; flex:none; white-space:nowrap; cursor:pointer; border:none; background:transparent;">
      <img :src="mascot" alt="" width="32" height="32" style="width:32px; height:32px; flex:none; object-fit:contain; display:block;" />
      <span style="font-size:15px; font-weight:800; color:#f5f4fb; letter-spacing:-.01em;">ShyDevs</span>
    </button>

    <button v-if="!editingName" type="button" @click="startEditName" :disabled="!canEdit"
      :aria-label="canEdit ? `Renomear projeto (nome atual: ${projectName})` : `Projeto: ${projectName}`"
      :style="{ display: 'flex', alignItems: 'center', gap: '6px', background: '#16161f', border: '1px solid #22222f', borderRadius: '8px', padding: '5px 10px', fontSize: '12.5px', fontWeight: '600', color: '#c7c5dc', flex: 'none', whiteSpace: 'nowrap', cursor: canEdit ? 'pointer' : 'default' }">
      <span style="width:7px; height:7px; border-radius:50%; background:#7c6fff; flex:none;" aria-hidden="true"></span>{{ projectName }}
      <i v-if="canEdit" class="fi fi-sr-pencil" aria-hidden="true" style="font-size:9px; opacity:.6;"></i>
    </button>
    <div v-else style="display:flex; align-items:center; gap:6px; flex:none;">
      <label for="project-name-input" class="sr-only">Nome do projeto</label>
      <input id="project-name-input" v-model="nameDraft" @keyup.enter="saveName" @keyup.esc="editingName = false" @blur="saveName" autofocus
        style="border:1px solid #7c6fff; background:#0e0e14; border-radius:8px; padding:5px 10px; font-size:12.5px; font-weight:600; color:#f5f4fb; outline:none; width:160px;" />
    </div>

    <div style="margin-left:4px; flex:none;">
      <SlidingTabs
        :items="navItems"
        :model-value="activeNav"
        @update:model-value="goNav"
        pill-color="rgba(124,111,255,.16)"
        active-text-color="#b3aaff"
        inactive-text-color="#8b899f"
      />
    </div>
    <div style="flex:1; min-width:0;"></div>
    <button v-if="canEdit" @click="(e) => { bounce(e); goCreate() }" style="display:flex; align-items:center; gap:7px; background:#7c6fff; color:#0a0a10; border:none; border-radius:9px; padding:9px 14px; font-size:12.5px; font-weight:700; cursor:pointer; flex:none; white-space:nowrap;">
      <i class="fi fi-sr-plus-small" aria-hidden="true"></i>Atribuir Tarefa
    </button>

    <button v-if="!auth.isLoggedIn" @click="loginOpen = true" style="border:1px solid #26263a; background:#14141d; color:#c7c5dc; border-radius:9px; padding:9px 12px; font-size:12.5px; font-weight:700; cursor:pointer; flex:none; display:flex; align-items:center; gap:6px;">
      <i class="fi fi-sr-user" aria-hidden="true"></i>Entrar
    </button>
    <div v-else class="account-menu" style="position:relative; flex:none; z-index:100;">
      <button
        @click="accountOpen = !accountOpen"
        :aria-label="`Menu da conta — ${auth.state.person?.name}`"
        aria-haspopup="menu"
        :aria-expanded="accountOpen"
        style="border:none; background:transparent; cursor:pointer; display:flex; align-items:center; gap:7px; padding:2px;">
        <div :key="auth.state.person?.id" :style="personAvatarStyle(auth.state.person, 28)" aria-hidden="true"></div>
      </button>
      <Transition :css="false" @enter="popEnter" @leave="popLeave">
        <div v-if="accountOpen" role="menu" @click.stop style="position:absolute; right:0; top:38px; background:#14141d; border:1px solid #26263a; border-radius:10px; padding:8px; width:190px; z-index:500; box-shadow:0 14px 40px rgba(0,0,0,.5);">
          <div style="font-size:12px; font-weight:700; color:#f5f4fb; padding:6px 8px; display:flex; align-items:center; gap:6px;">
            {{ auth.state.person?.name }}
            <span v-if="canEdit" style="font-size:9px; font-weight:700; letter-spacing:.04em; color:#b3aaff; background:rgba(124,111,255,.16); border-radius:999px; padding:2px 6px;">ADMIN</span>
          </div>
          <div style="font-size:11px; color:#8b899f; padding:0 8px 8px;">{{ (auth.state.person?.roles || []).join(', ') || 'Sem cargo' }}</div>
          <label for="account-photo-input" style="display:flex; align-items:center; gap:8px; font-size:12px; color:#c7c5dc; padding:8px; border-radius:7px; cursor:pointer;">
            <i class="fi fi-sr-user-add" aria-hidden="true"></i>Alterar foto
            <input id="account-photo-input" type="file" accept="image/*" @change="onPhotoChange" style="position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0,0,0,0);" />
          </label>

          <button v-if="!changingPassword" role="menuitem" type="button" @click="startChangePassword" style="width:100%; text-align:left; display:flex; align-items:center; gap:8px; font-size:12px; color:#c7c5dc; padding:8px; border-radius:7px; cursor:pointer; border:none; background:transparent;">
            <i class="fi fi-sr-lock" aria-hidden="true"></i>Trocar senha
          </button>
          <form v-else @submit.prevent="savePassword" style="padding:6px 8px 8px; display:flex; flex-direction:column; gap:6px;">
            <label for="new-password-input" class="sr-only">Nova senha</label>
            <input id="new-password-input" v-model="newPasswordDraft" type="password" autofocus placeholder="Nova senha"
              style="width:100%; box-sizing:border-box; border:1px solid #7c6fff; background:#0e0e14; border-radius:7px; padding:7px 9px; font-size:12px; color:#f5f4fb; outline:none;" />
            <div style="display:flex; gap:6px;">
              <button type="submit" :disabled="!newPasswordDraft || savingPassword" style="flex:1; border:none; background:#7c6fff; color:#0a0a10; border-radius:7px; padding:7px 0; font-size:11.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
                <span v-if="savingPassword" class="btn-spinner" aria-hidden="true"></span>{{ savingPassword ? 'Salvando…' : passwordSaved ? '✓ Trocada' : 'Salvar' }}
              </button>
              <button type="button" @click="changingPassword = false" style="border:1px solid #26263a; background:transparent; color:#8b899f; border-radius:7px; padding:7px 10px; font-size:11.5px; cursor:pointer;">Cancelar</button>
            </div>
          </form>

          <button role="menuitem" @click="logout" style="width:100%; text-align:left; display:flex; align-items:center; gap:8px; font-size:12px; color:#ff8f98; padding:8px; border-radius:7px; cursor:pointer; border:none; background:transparent;">
            <i class="fi fi-sr-sign-out-alt" aria-hidden="true"></i>Sair
          </button>
        </div>
      </Transition>
    </div>
  </div>

  <LoginModal :open="loginOpen" @close="loginOpen = false" />
</template>
