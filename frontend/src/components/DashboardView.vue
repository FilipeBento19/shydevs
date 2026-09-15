<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { api } from '../api'
import { gsap, reduceMotion } from '../motion'
import { roleIcon } from '../utils'

const data = ref(null)
const loading = ref(true)
const error = ref('')
const rootEl = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.getDashboard()
    await nextTick()
    animateIn()
  } catch (e) {
    error.value = 'Não foi possível carregar o dashboard.'
  } finally {
    loading.value = false
  }
}
defineExpose({ load })
onMounted(load)

function animateIn() {
  if (reduceMotion || !rootEl.value) return
  const cards = rootEl.value.querySelectorAll('.stat-card')
  const bars = rootEl.value.querySelectorAll('.bar-fill')
  gsap.from(cards, { y: 12, autoAlpha: 0, duration: 0.4, stagger: 0.05, ease: 'power2.out' })
  bars.forEach((bar) => {
    const target = bar.style.width
    gsap.fromTo(bar, { width: '0%' }, { width: target, duration: 0.7, ease: 'power3.out', delay: 0.15 })
  })
}

const statusColors = {
  Pendente: '#8b899f',
  'Em andamento': '#7c6fff',
  Concluída: '#3fcf8e',
}
const prioColors = { Baixa: '#9a9ab0', Média: '#e0a23c', Alta: '#e04f5f' }

const statusEntries = computed(() => (data.value ? Object.entries(data.value.by_status) : []))
const roleEntries = computed(() => (data.value ? Object.entries(data.value.by_role) : []))
const prioEntries = computed(() => (data.value ? Object.entries(data.value.by_priority) : []))
const maxWorkload = computed(() =>
  data.value ? Math.max(1, ...data.value.workload.map((w) => w.open + w.done)) : 1
)
</script>

<template>
  <div ref="rootEl" style="padding:20px 26px 26px;">
    <div v-if="loading" style="padding:24px; color:#8b899f; font-size:12.5px;">Carregando dashboard…</div>
    <div v-else-if="error" style="padding:16px; background:rgba(224,79,95,.12); border:1px solid rgba(224,79,95,.35); border-radius:10px; color:#ff8f98; font-size:12.5px;">{{ error }}</div>

    <template v-else-if="data">
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:10px; margin-bottom:18px;">
        <div class="stat-card" style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:14px;">
          <div style="font-size:22px; font-weight:800; color:#f5f4fb;">{{ data.total }}</div>
          <div style="font-size:11.5px; color:#8b899f; margin-top:2px;">Tarefas no total</div>
        </div>
        <div class="stat-card" style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:14px;">
          <div style="font-size:22px; font-weight:800; color:#ff8f98;">{{ data.overdue }}</div>
          <div style="font-size:11.5px; color:#8b899f; margin-top:2px;">Atrasadas</div>
        </div>
        <div class="stat-card" style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:14px;">
          <div style="font-size:22px; font-weight:800; color:#6fe3a4;">{{ data.by_status['Concluída'] || 0 }}</div>
          <div style="font-size:11.5px; color:#8b899f; margin-top:2px;">Concluídas</div>
        </div>
        <div class="stat-card" style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:14px;">
          <div style="font-size:22px; font-weight:800; color:#b3aaff;">{{ data.by_status['Em andamento'] || 0 }}</div>
          <div style="font-size:11.5px; color:#8b899f; margin-top:2px;">Em andamento</div>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:14px;">
        <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
          <div style="font-size:12.5px; font-weight:800; color:#f5f4fb; margin-bottom:12px;">Por status</div>
          <div v-for="[k, v] in statusEntries" :key="k" style="margin-bottom:9px;">
            <div style="display:flex; justify-content:space-between; font-size:11.5px; color:#c7c5dc; margin-bottom:4px;">
              <span>{{ k }}</span><span>{{ v }}</span>
            </div>
            <div style="background:#0e0e14; border-radius:6px; height:8px; overflow:hidden;">
              <div class="bar-fill" :style="{ width: (data.total ? (v / data.total) * 100 : 0) + '%', height: '100%', background: statusColors[k] || '#7c6fff', borderRadius: '6px' }"></div>
            </div>
          </div>
        </div>

        <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
          <div style="font-size:12.5px; font-weight:800; color:#f5f4fb; margin-bottom:12px;">Por prioridade</div>
          <div v-for="[k, v] in prioEntries" :key="k" style="margin-bottom:9px;">
            <div style="display:flex; justify-content:space-between; font-size:11.5px; color:#c7c5dc; margin-bottom:4px;">
              <span>{{ k }}</span><span>{{ v }}</span>
            </div>
            <div style="background:#0e0e14; border-radius:6px; height:8px; overflow:hidden;">
              <div class="bar-fill" :style="{ width: (data.total ? (v / data.total) * 100 : 0) + '%', height: '100%', background: prioColors[k] || '#7c6fff', borderRadius: '6px' }"></div>
            </div>
          </div>
        </div>

        <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
          <div style="font-size:12.5px; font-weight:800; color:#f5f4fb; margin-bottom:12px;">Por cargo</div>
          <div v-for="[k, v] in roleEntries" :key="k" style="margin-bottom:9px;">
            <div style="display:flex; align-items:center; gap:6px; justify-content:space-between; font-size:11.5px; color:#c7c5dc; margin-bottom:4px;">
              <span style="display:flex; align-items:center; gap:5px;"><i :class="`fi ${roleIcon(k)}`" style="opacity:.7;" aria-hidden="true"></i>{{ k }}</span><span>{{ v }}</span>
            </div>
            <div style="background:#0e0e14; border-radius:6px; height:8px; overflow:hidden;">
              <div class="bar-fill" :style="{ width: (data.total ? (v / data.total) * 100 : 0) + '%', height: '100%', background: '#7c6fff', borderRadius: '6px' }"></div>
            </div>
          </div>
        </div>

        <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
          <div style="font-size:12.5px; font-weight:800; color:#f5f4fb; margin-bottom:12px;">Carga por pessoa</div>
          <div v-for="w in data.workload" :key="w.name" style="margin-bottom:9px;">
            <div style="display:flex; justify-content:space-between; font-size:11.5px; color:#c7c5dc; margin-bottom:4px;">
              <span>{{ w.name }}</span><span style="color:#8b899f;">{{ w.open }} abertas · {{ w.done }} feitas</span>
            </div>
            <div style="background:#0e0e14; border-radius:6px; height:8px; overflow:hidden; display:flex;">
              <div class="bar-fill" :style="{ width: (w.open / maxWorkload) * 100 + '%', height: '100%', background: '#7c6fff' }"></div>
              <div class="bar-fill" :style="{ width: (w.done / maxWorkload) * 100 + '%', height: '100%', background: '#3fcf8e' }"></div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
