<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import MediaViewer from './MediaViewer.vue'

const messages = ref([])
const loading = ref(true)
const error = ref('')

const SOURCE_LABELS = {
  admin: 'Mensagem manual',
  pending_reminder: 'Lembrete · parada em Pendente',
  in_progress_reminder: 'Lembrete · presa em Em andamento',
  due_soon_reminder: 'Lembrete · prazo chegando',
  unblocked: 'Aviso · tarefa liberada',
  your_turn: 'Aviso · sua vez na tarefa',
  digest: 'Resumo periódico',
  dm: 'Mensagem recebida',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    messages.value = await api.getDiscordMessages()
  } catch (e) {
    error.value = 'Não foi possível carregar as mensagens do bot.'
  } finally {
    loading.value = false
  }
}
onMounted(load)

const totalOutgoing = computed(() => messages.value.filter((m) => m.direction === 'outgoing').length)
const totalIncoming = computed(() => messages.value.filter((m) => m.direction === 'incoming').length)

function fmtDate(iso) {
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}
// ---- media people sent the bot: tiles in the feed, real viewer on click ----
const viewer = ref(null) // { items, index }
function openMedia(m, index) {
  // MediaViewer speaks the "reference" shape.
  const items = m.attachments.map((a) => ({
    id: a.id, kind: a.kind, file: a.url, caption: a.name, group: 'Mensagem no Discord', uploaded_by_name: who(m),
  }))
  viewer.value = { items, index }
}

function who(m) {
  return m.person_name || (m.discord_id ? `Discord ID ${m.discord_id}` : 'Desconhecido')
}
</script>

<template>
  <div style="padding:20px 26px 26px;">
    <div style="display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap;">
      <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:14px 18px; flex:1; min-width:160px;">
        <div style="font-size:11px; color:#8b899f; margin-bottom:4px;">Enviadas pelo bot</div>
        <div style="font-size:22px; font-weight:800; color:#f5f4fb;">{{ totalOutgoing }}</div>
      </div>
      <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:14px 18px; flex:1; min-width:160px;">
        <div style="font-size:11px; color:#8b899f; margin-bottom:4px;">Recebidas de pessoas</div>
        <div style="font-size:22px; font-weight:800; color:#f5f4fb;">{{ totalIncoming }}</div>
      </div>
      <button type="button" @click="load" :disabled="loading" style="border:1px solid #26263a; background:#14141d; color:#c7c5dc; border-radius:10px; padding:0 16px; font-size:12.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:6px;">
        <span v-if="loading" class="btn-spinner" aria-hidden="true"></span>
        <i v-else class="fi fi-sr-refresh" aria-hidden="true"></i>Atualizar
      </button>
    </div>

    <div v-if="loading" style="padding:30px; text-align:center; font-size:12.5px; color:#8b899f;">Carregando…</div>
    <div v-else-if="error" style="padding:12px 14px; background:rgba(224,79,95,.14); border:1px solid rgba(224,79,95,.35); border-radius:10px; color:#ff8f98; font-size:12.5px; font-weight:600;">{{ error }}</div>
    <div v-else-if="!messages.length" style="padding:30px; text-align:center; font-size:12.5px; color:#8b899f;">
      <i class="fi fi-sr-robot" aria-hidden="true" style="font-size:22px; display:block; margin-bottom:8px; opacity:.5;"></i>
      Nenhuma mensagem do bot ainda.
    </div>

    <div v-else style="display:flex; flex-direction:column; gap:8px;">
      <div v-for="m in messages" :key="m.id"
        style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:12px 16px; display:flex; gap:12px; align-items:flex-start;">
        <span :style="{
          flex: 'none', width: '30px', height: '30px', borderRadius: '50%', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          background: m.direction === 'incoming' ? 'rgba(63,207,142,.14)' : 'rgba(124,111,255,.14)',
          color: m.direction === 'incoming' ? '#3fcf8e' : '#7c6fff',
        }" aria-hidden="true">
          <i :class="`fi ${m.direction === 'incoming' ? 'fi-sr-arrow-small-left' : 'fi-sr-arrow-small-right'}`"></i>
        </span>
        <div style="flex:1; min-width:0;">
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:3px;">
            <strong style="font-size:12.5px; color:#f5f4fb;">{{ who(m) }}</strong>
            <span style="font-size:9.5px; font-weight:700; letter-spacing:.03em; color:#8b899f; background:#0e0e14; border-radius:999px; padding:2px 8px;">{{ SOURCE_LABELS[m.source] || m.source }}</span>
            <time style="margin-left:auto; font-size:10.5px; color:#65637a; white-space:nowrap;">{{ fmtDate(m.created_at) }}</time>
          </div>
          <p v-if="m.content" style="margin:0; font-size:12.5px; color:#c7c5dc; white-space:pre-wrap; line-height:1.5; overflow-wrap:anywhere;">{{ m.content }}</p>
          <div v-if="m.attachments?.length" class="bot-media">
            <button v-for="(a, i) in m.attachments" :key="a.id" type="button" class="bot-tile" :class="{ file: a.kind === 'file' }"
              :aria-label="`Abrir ${a.name || 'anexo'}`" @click="openMedia(m, i)">
              <img v-if="a.kind === 'image'" :src="a.url" :alt="a.name" loading="lazy" />
              <video v-else-if="a.kind === 'video'" :src="a.is_gif ? a.url : `${a.url}#t=0.1`" :autoplay="a.is_gif" :loop="a.is_gif" muted playsinline preload="metadata" tabindex="-1"></video>
              <span v-else class="bot-file"><i class="fi fi-sr-file" aria-hidden="true"></i>{{ a.name || 'Arquivo' }}</span>
              <span v-if="a.kind === 'video' && !a.is_gif" class="bot-play" aria-hidden="true"><i class="fi fi-sr-play"></i></span>
              <span v-if="a.is_gif" class="bot-gif" aria-hidden="true">GIF</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <MediaViewer v-if="viewer" :items="viewer.items" :index="viewer.index" @update:index="viewer.index = $event" @close="viewer = null" />
  </div>
</template>

<style scoped>
.bot-media { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.bot-tile { position: relative; width: 190px; height: 130px; padding: 0; border: 1px solid #26263a; border-radius: 10px; overflow: hidden; background: #0b0b11; cursor: pointer; }
.bot-tile:hover, .bot-tile:focus-visible { border-color: #7c6fff; outline: none; }
.bot-tile img, .bot-tile video { width: 100%; height: 100%; object-fit: cover; display: block; pointer-events: none; }
.bot-tile.file { width: auto; max-width: 260px; height: auto; }
.bot-file { display: flex; align-items: center; gap: 8px; padding: 10px 12px; font-size: 12px; color: #c7c5dc; text-align: left; word-break: break-all; }
.bot-play { position: absolute; inset: 0; margin: auto; width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; background: rgba(20, 20, 29, .75); color: #fff; font-size: 13px; }
.bot-play i { margin-left: 2px; }
.bot-gif { position: absolute; left: 6px; bottom: 6px; font-size: 9.5px; font-weight: 800; letter-spacing: .05em; color: #fff; background: rgba(0, 0, 0, .65); border-radius: 5px; padding: 2px 6px; }
@media (max-width: 760px) { .bot-tile { width: 100%; height: 170px; } }
</style>
