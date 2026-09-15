<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { gsap, reduceMotion, toastEnter, toastLeave } from './motion'
import { mascot } from './mascotFace'
import { auth } from './auth'
import AppHeader from './components/AppHeader.vue'

const route = useRoute()
const router = useRouter()
const heroSubtitle = computed(() => {
  if (route.name === 'board') {
    return auth.state.person?.is_admin
      ? 'Distribua demandas por cargo e mantenha cada especialidade da equipe com um fluxo equilibrado.'
      : 'Acompanhe as demandas da equipe. Somente o administrador pode alterar tarefas.'
  }
  return route.meta.subtitle || ''
})
const showHero = computed(() => !['task', 'new-task', 'home'].includes(route.name))

const headerBarEl = ref(null)
const heroTitleEl = ref(null)
const heroSubtitleEl = ref(null)
const heroMascotEl = ref(null)

const toasts = ref([])
let toastSeq = 0
function pushToast(message) {
  const id = ++toastSeq
  toasts.value.push({ id, message })
  setTimeout(() => dismissToast(id), 5000)
}
function dismissToast(id) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}

function safeTargets(...vals) {
  const list = vals.flatMap((v) => (v && v.length !== undefined ? Array.from(v) : v ? [v] : []))
  return list.filter(Boolean)
}
function playEntrance() {
  if (reduceMotion) return
  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
  const step = (targets, vars, pos) => {
    const t = safeTargets(targets)
    if (t.length) tl.from(t, { clearProps: 'transform', ...vars }, pos)
  }
  step(headerBarEl.value, { y: -16, autoAlpha: 0, duration: 0.5 })
  step([heroTitleEl.value, heroSubtitleEl.value], { y: 18, autoAlpha: 0, duration: 0.5, stagger: 0.08 }, '-=0.25')
  step(heroMascotEl.value, { scale: 0.5, autoAlpha: 0, rotate: -10, duration: 0.6, ease: 'back.out(1.6)' }, '-=0.4')
}
onMounted(async () => {
  await nextTick()
  playEntrance()
})

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

function onKeydown(e) {
  const tag = (e.target.tagName || '').toLowerCase()
  const typing = tag === 'input' || tag === 'textarea' || e.target.isContentEditable
  if (typing) return
  if (e.key.toLowerCase() === 'n' && auth.state.person?.is_admin) {
    router.push({ name: 'new-task' })
  }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
</script>

<template>
  <div style="min-height:100vh;">

    <div ref="headerBarEl" style="position:sticky; top:0; z-index:40; background:#0b0b11; border-bottom:1px solid #1f1f2b;">
      <div style="max-width:1180px; margin:0 auto;">
        <AppHeader />
      </div>
    </div>

    <div style="max-width:1180px; margin:0 auto;">
      <div v-if="showHero" style="padding:22px 26px 0;">
        <div style="display:flex; align-items:center; gap:8px; font-size:11.5px; font-weight:600; color:#8b899f; margin-bottom:9px;">
          <span style="width:6px; height:6px; border-radius:50%; background:#7c6fff;"></span>ShyDevs · Sprint 24.4
        </div>
        <div style="display:flex; align-items:flex-start; gap:20px; flex-wrap:wrap;">
          <div style="flex:1; min-width:260px;">
            <h1 ref="heroTitleEl" style="margin:0 0 7px; font-size:27px; font-weight:800; color:#f5f4fb; letter-spacing:-.025em;">{{ route.meta.title }}</h1>
            <p ref="heroSubtitleEl" style="margin:0; font-size:13px; line-height:1.5; color:#9a97b8; max-width:520px;">{{ heroSubtitle }}</p>
          </div>
          <img ref="heroMascotEl" @click="confettiBurst" :src="mascot" alt="Mascote ShyDevs" style="width:84px; height:84px; flex:none; object-fit:contain; cursor:pointer; filter:drop-shadow(0 10px 24px rgba(124,111,255,.3));" />
        </div>
      </div>

      <router-view />
    </div>

  </div>

  <TransitionGroup tag="div" @enter="toastEnter" @leave="toastLeave" :css="false" style="position:fixed; bottom:20px; left:50%; transform:translateX(-50%); z-index:80; display:flex; flex-direction:column; gap:8px; align-items:center;">
    <div v-for="t in toasts" :key="t.id" style="background:#14141d; border:1px solid #26263a; border-radius:10px; padding:10px 14px; display:flex; align-items:center; gap:12px; color:#e4e2f1; font-size:12.5px; box-shadow:0 10px 30px rgba(0,0,0,.4);">
      {{ t.message }}
    </div>
  </TransitionGroup>
</template>
