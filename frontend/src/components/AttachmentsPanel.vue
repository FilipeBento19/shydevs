<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'
import { auth } from '../auth'
import { listEnter, listLeave } from '../motion'

const props = defineProps({
  taskId: { type: [Number, String], required: true },
})
const emit = defineEmits(['changed'])

const attachments = ref([])
const loading = ref(true)
const error = ref('')
const confirmDeleteId = ref(null)

const canUpload = computed(() => auth.isLoggedIn)

const KIND_OPTIONS = [
  { value: 'image', label: 'Imagem', icon: 'fi-sr-picture' },
  { value: 'video', label: 'Vídeo', icon: 'fi-sr-video-camera' },
  { value: 'link', label: 'Link', icon: 'fi-sr-link' },
]
const form = reactive({ kind: 'image', url: '', caption: '' })
const fileInput = ref(null)
const submitting = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    attachments.value = await api.getAttachments(props.taskId)
  } catch (e) {
    error.value = 'Não foi possível carregar os anexos.'
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => props.taskId, load)

async function submit() {
  error.value = ''
  const file = fileInput.value?.files?.[0]
  if (form.kind === 'link' && !form.url.trim()) {
    error.value = 'Informe a URL do link.'
    return
  }
  if (form.kind !== 'link' && !file) {
    error.value = 'Escolha um arquivo para enviar.'
    return
  }
  submitting.value = true
  try {
    const created = await api.createAttachment({
      task: props.taskId,
      kind: form.kind,
      url: form.kind === 'link' ? form.url.trim() : '',
      caption: form.caption.trim(),
      file: form.kind !== 'link' ? file : null,
    })
    attachments.value.unshift(created)
    form.url = ''
    form.caption = ''
    if (fileInput.value) fileInput.value.value = ''
    emit('changed')
  } catch (e) {
    error.value = 'Não foi possível enviar o anexo.'
  } finally {
    submitting.value = false
  }
}

async function removeAttachment(a) {
  if (confirmDeleteId.value !== a.id) {
    confirmDeleteId.value = a.id
    return
  }
  try {
    await api.deleteAttachment(a.id)
    attachments.value = attachments.value.filter((x) => x.id !== a.id)
    confirmDeleteId.value = null
    emit('changed')
  } catch (e) {
    error.value = 'Não foi possível remover esse anexo.'
  }
}

function canDelete(a) {
  const person = auth.state.person
  if (!person) return false
  return person.is_admin || a.uploaded_by === person.id
}

function fmtDate(iso) {
  const d = new Date(iso)
  return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div>
    <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:8px; display:flex; align-items:center; justify-content:space-between;">
      Anexos (imagens, vídeos, links)
      <span style="font-weight:500; color:#8b899f; font-size:11px;">{{ attachments.length }}</span>
    </div>

    <div v-if="loading" style="font-size:12px; color:#6f6d87;">Carregando anexos…</div>

    <TransitionGroup v-else tag="div" @enter="listEnter" @leave="listLeave" :css="false" style="display:flex; flex-direction:column; gap:8px; margin-bottom:10px;">
      <div v-for="(a, i) in attachments" :key="a.id" :data-index="i" style="background:#0e0e14; border:1px solid #22222f; border-radius:10px; padding:10px; display:flex; gap:10px; align-items:flex-start;">
        <a v-if="a.kind === 'image' && a.file" :href="a.file" target="_blank" rel="noopener" style="flex:none;">
          <img :src="a.file" alt="" style="width:56px; height:56px; object-fit:cover; border-radius:8px; display:block;" />
        </a>
        <a v-else-if="a.kind === 'video' && a.file" :href="a.file" target="_blank" rel="noopener" style="flex:none; width:56px; height:56px; border-radius:8px; background:#1c1c28; display:flex; align-items:center; justify-content:center; color:#7c6fff; font-size:18px;">
          <i class="fi fi-sr-play"></i>
        </a>
        <a v-else :href="a.url || a.file" target="_blank" rel="noopener" style="flex:none; width:56px; height:56px; border-radius:8px; background:#1c1c28; display:flex; align-items:center; justify-content:center; color:#7c6fff; font-size:18px;">
          <i :class="`fi ${a.kind === 'link' ? 'fi-sr-link' : 'fi-sr-file'}`"></i>
        </a>

        <div style="flex:1; min-width:0;">
          <div style="font-size:12.5px; font-weight:700; color:#f5f4fb; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
            {{ a.caption || (a.kind === 'link' ? a.url : 'Sem legenda') }}
          </div>
          <a v-if="a.kind === 'link'" :href="a.url" target="_blank" rel="noopener" style="font-size:11px; color:#7c6fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; display:block;">{{ a.url }}</a>
          <div style="font-size:11px; color:#8b899f; margin-top:2px;">{{ a.uploaded_by_name || 'Alguém' }} · {{ fmtDate(a.created_at) }}</div>
        </div>

        <button v-if="canDelete(a)" @click="removeAttachment(a)"
          :style="{ border: 'none', background: 'transparent', color: confirmDeleteId === a.id ? '#ff8f98' : '#6f6d87', cursor: 'pointer', fontSize: '12px', flex: 'none' }">
          <i class="fi fi-sr-trash-can-list"></i>
        </button>
      </div>
    </TransitionGroup>
    <div v-if="!loading && !attachments.length" style="font-size:12px; color:#6f6d87; margin-bottom:10px;">Nenhum anexo ainda.</div>

    <div v-if="canUpload" style="background:#0e0e14; border:1px solid #22222f; border-radius:10px; padding:10px; display:flex; flex-direction:column; gap:8px;">
      <div style="display:flex; gap:6px;">
        <button v-for="k in KIND_OPTIONS" :key="k.value" type="button" @click="form.kind = k.value"
          :style="{ flex: 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px', borderRadius: '8px', padding: '7px 0', fontSize: '11.5px', fontWeight: '700', cursor: 'pointer', border: `1px solid ${form.kind === k.value ? '#7c6fff' : '#26263a'}`, background: form.kind === k.value ? 'rgba(124,111,255,.14)' : '#14141d', color: form.kind === k.value ? '#cfc9ff' : '#c7c5dc' }">
          <i :class="`fi ${k.icon}`"></i>{{ k.label }}
        </button>
      </div>

      <input v-if="form.kind === 'link'" v-model="form.url" placeholder="https://…" style="width:100%; box-sizing:border-box; border:1px solid #26263a; background:#14141d; border-radius:8px; padding:8px 10px; font-size:12px; color:#f5f4fb; outline:none;" />
      <input v-else ref="fileInput" type="file" :accept="form.kind === 'image' ? 'image/*' : form.kind === 'video' ? 'video/*' : undefined" style="width:100%; font-size:11.5px; color:#c7c5dc;" />

      <input v-model="form.caption" placeholder="Legenda (opcional)" style="width:100%; box-sizing:border-box; border:1px solid #26263a; background:#14141d; border-radius:8px; padding:8px 10px; font-size:12px; color:#f5f4fb; outline:none;" />

      <div v-if="error" style="font-size:11.5px; color:#ff8f98;">{{ error }}</div>

      <button @click="submit" :disabled="submitting" type="button" style="border:none; background:#7c6fff; color:#0a0a10; border-radius:8px; padding:8px 12px; font-size:12px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
        <i class="fi fi-sr-cloud-upload-alt"></i>{{ submitting ? 'Enviando…' : 'Enviar anexo' }}
      </button>
    </div>
    <div v-else style="font-size:11.5px; color:#6f6d87;">Faça login para anexar imagens, vídeos ou links de referência.</div>
  </div>
</template>
