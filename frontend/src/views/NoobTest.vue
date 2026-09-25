<script setup>
// Temporary preview page: drag the slider to fake the number of open tasks.
import NoobSpinner from '../components/NoobSpinner.vue'
import { workload } from '../workload'

function complete() {
  if (workload.count > 0) workload.count--
  workload.completions++
}
</script>

<template>
  <div style="max-width:560px; margin:24px auto; padding:0 16px; text-align:center; color:#f5f4fb;">
    <h2 style="margin:0 0 4px;">Teste do glitch do noob</h2>
    <p style="margin:0 0 20px; font-size:13px; color:#9a97b8;">Arraste o controle e veja o noob mudar. Clique nele para girar.</p>
    <div style="display:flex; justify-content:center;"><NoobSpinner spinnable :size="320" /></div>
    <div style="margin:18px 0 6px; font-size:28px; font-weight:800;">{{ workload.count }} <span style="font-size:14px; font-weight:600; color:#9a97b8;">tarefas em aberto</span></div>
    <input v-model.number="workload.count" type="range" min="0" max="40" step="1" style="width:100%;" aria-label="Número de tarefas" />
    <button type="button" @click="complete" style="margin-top:14px; padding:9px 16px; border-radius:9px; border:1px solid #26263a; background:#7c6fff; color:#0a0a10; font-weight:700; cursor:pointer;">Concluir uma tarefa</button>
    <div style="display:flex; justify-content:space-between; margin-top:14px; font-size:11px; color:#706e82;"><span>0 (limpo)</span><span>10</span><span>25</span><span>40</span></div>
  </div>
</template>
