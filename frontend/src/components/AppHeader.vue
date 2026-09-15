<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'
import { gsap, popEnter, popLeave, reduceMotion } from '../motion'
import { mascotFaceStyle, personAvatarStyle, mascot } from '../mascotFace'
import SlidingTabs from './SlidingTabs.vue'
import LoginModal from './LoginModal.vue'

const route = useRoute()
const router = useRouter()

function goCreate() {
  router.push({ name: 'new-task' })
}

const canEdit = computed(() => !!auth.state.person?.is_admin)

const BASE_NAV_ITEMS = [
  { key: 'board', label: 'Quadro de Tarefas', icon: 'fi-sr-table-list' },
  { key: 'dashboard', label: 'Dashboard', icon: 'fi-sr-chart-simple' },
  { key: 'history', label: 'Histórico', icon: 'fi-sr-clock' },
]
const navItems = computed(() =>
  canEdit.value ? [...BASE_NAV_ITEMS, { key: 'team', label: 'Equipe', icon: 'fi-sr-users' }] : BASE_NAV_ITEMS
)
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
  } catch (err) {
    // ignore
  }
}

function onDocClick(e) {
  if (accountOpen.value && !e.target.closest('.account-menu')) accountOpen.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))

// ---- confetti easter egg ----
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
  <div style="display:flex; align-items:center; gap:14px; padding:10px 16px; background:#0b0b11; border-bottom:1px solid #1f1f2b; flex-wrap:wrap;">
    <div @click="confettiBurst" style="display:flex; align-items:center; gap:8px; padding-right:4px; flex:none; white-space:nowrap; cursor:pointer;">
      <img :src="mascot" alt="ShyDevs" style="height:32px; width:auto; flex:none; object-fit:contain; display:block;" />
      <span style="font-size:15px; font-weight:800; color:#f5f4fb; letter-spacing:-.01em;">ShyDevs</span>
    </div>

    <div v-if="!editingName" @click="startEditName"
      :style="{ display: 'flex', alignItems: 'center', gap: '6px', background: '#16161f', border: '1px solid #22222f', borderRadius: '8px', padding: '5px 10px', fontSize: '12.5px', fontWeight: '600', color: '#c7c5dc', flex: 'none', whiteSpace: 'nowrap', cursor: canEdit ? 'pointer' : 'default' }"
      :title="canEdit ? 'Clique para renomear o projeto' : ''">
      <span style="width:7px; height:7px; border-radius:50%; background:#7c6fff; flex:none;"></span>{{ projectName }}
      <i v-if="canEdit" class="fi fi-sr-pencil" style="font-size:9px; opacity:.6;"></i>
    </div>
    <div v-else style="display:flex; align-items:center; gap:6px; flex:none;">
      <input v-model="nameDraft" @keyup.enter="saveName" @keyup.esc="editingName = false" @blur="saveName" autofocus
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
      <i class="fi fi-sr-plus-small"></i>Atribuir Tarefa
    </button>

    <button v-if="!auth.isLoggedIn" @click="loginOpen = true" style="border:1px solid #26263a; background:#14141d; color:#c7c5dc; border-radius:9px; padding:9px 12px; font-size:12.5px; font-weight:700; cursor:pointer; flex:none; display:flex; align-items:center; gap:6px;">
      <i class="fi fi-sr-user"></i>Entrar
    </button>
    <div v-else class="account-menu" style="position:relative; flex:none; z-index:100;">
      <button @click="accountOpen = !accountOpen" style="border:none; background:transparent; cursor:pointer; display:flex; align-items:center; gap:7px; padding:2px;">
        <div :style="personAvatarStyle(auth.state.person, 28)" :title="auth.state.person?.name"></div>
      </button>
      <Transition :css="false" @enter="popEnter" @leave="popLeave">
        <div v-if="accountOpen" style="position:absolute; right:0; top:38px; background:#14141d; border:1px solid #26263a; border-radius:10px; padding:8px; width:190px; z-index:500; box-shadow:0 14px 40px rgba(0,0,0,.5);">
          <div style="font-size:12px; font-weight:700; color:#f5f4fb; padding:6px 8px; display:flex; align-items:center; gap:6px;">
            {{ auth.state.person?.name }}
            <span v-if="canEdit" style="font-size:9px; font-weight:700; letter-spacing:.04em; color:#b3aaff; background:rgba(124,111,255,.16); border-radius:999px; padding:2px 6px;">ADMIN</span>
          </div>
          <div style="font-size:11px; color:#8b899f; padding:0 8px 8px;">{{ auth.state.person?.role }}</div>
          <label v-if="canEdit" style="display:flex; align-items:center; gap:8px; font-size:12px; color:#c7c5dc; padding:8px; border-radius:7px; cursor:pointer;">
            <i class="fi fi-sr-user-add"></i>Alterar foto
            <input type="file" accept="image/*" @change="onPhotoChange" style="display:none;" />
          </label>
          <button @click="logout" style="width:100%; text-align:left; display:flex; align-items:center; gap:8px; font-size:12px; color:#ff8f98; padding:8px; border-radius:7px; cursor:pointer; border:none; background:transparent;">
            <i class="fi fi-sr-sign-out-alt"></i>Sair
          </button>
        </div>
      </Transition>
    </div>
  </div>

  <LoginModal :open="loginOpen" @close="loginOpen = false" />
</template>
