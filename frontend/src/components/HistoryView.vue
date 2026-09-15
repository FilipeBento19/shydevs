<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { listEnter, listLeave } from '../motion'

const activities = ref([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    activities.value = await api.getActivities()
  } catch (e) {
    error.value = 'Não foi possível carregar o histórico.'
  } finally {
    loading.value = false
  }
}
defineExpose({ load })
onMounted(load)

function fmtDate(iso) {
  const d = new Date(iso)
  return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div style="padding:20px 26px 26px;">
    <div style="font-size:13px; font-weight:700; color:#f5f4fb; margin-bottom:12px;">Histórico de Atividades</div>

    <div v-if="loading" style="padding:24px; color:#8b899f; font-size:12.5px;">Carregando…</div>
    <div v-else-if="error" style="padding:16px; background:rgba(224,79,95,.12); border:1px solid rgba(224,79,95,.35); border-radius:10px; color:#ff8f98; font-size:12.5px;">{{ error }}</div>
    <div v-else-if="!activities.length" style="padding:24px; color:#8b899f; font-size:12.5px;">Nenhuma atividade registrada ainda.</div>

    <TransitionGroup v-else tag="div" @enter="listEnter" @leave="listLeave" :css="false" style="background:#14141d; border:1px solid #22222f; border-radius:12px; overflow:hidden;">
      <div v-for="(a, i) in activities" :key="a.id" :data-index="i" style="display:flex; gap:10px; padding:12px 14px; border-bottom:1px solid #1a1a25; align-items:flex-start;">
        <i class="fi fi-sr-clock" style="color:#7c6fff; opacity:.8; margin-top:2px; font-size:12px;"></i>
        <div style="flex:1; min-width:0;">
          <div style="font-size:12.5px; color:#e4e2f1;">
            <span v-if="a.actor_name" style="font-weight:700; color:#f5f4fb;">{{ a.actor_name }}</span>
            <span v-else style="font-weight:700; color:#8b899f;">Sistema</span>
            — {{ a.message }}
          </div>
          <div style="font-size:11px; color:#6f6d87; margin-top:2px;">{{ fmtDate(a.created_at) }}</div>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>
