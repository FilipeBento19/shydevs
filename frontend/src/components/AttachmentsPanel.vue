<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'
import { auth } from '../auth'
import { vAutogrow } from '../directives/autogrow'
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

const form = reactive({ caption: '' })
const fileInput = ref(null)
const selectedFileName = ref('')
const submitting = ref(false)

function onFileChange(e) {
  selectedFileName.value = e.target.files?.[0]?.name || ''
}

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
  if (!file) {
    error.value = 'Escolha um arquivo para enviar.'
    return
  }
  submitting.value = true
  try {
    const created = await api.createAttachment({
      task: props.taskId,
      caption: form.caption.trim(),
      file,
    })
    attachments.value.unshift(created)
    form.caption = ''
    if (fileInput.value) fileInput.value.value = ''
    selectedFileName.value = ''
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

function attachmentHref(attachment) {
  return attachment.file || attachment.url || '#'
}

function attachmentName(attachment) {
  if (attachment.file_name) return attachment.file_name
  const source = attachment.file || attachment.url
  if (!source) return 'Arquivo anexado'
  try {
    return decodeURIComponent(source.split('?')[0].split('/').pop()) || 'Arquivo anexado'
  } catch (e) {
    return 'Arquivo anexado'
  }
}
</script>

<template>
  <div>
    <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:8px; display:flex; align-items:center; justify-content:space-between;">
      Arquivos anexados
      <span style="font-weight:500; color:#8b899f; font-size:11px;">{{ attachments.length }}</span>
    </div>

    <div v-if="loading" style="font-size:12px; color:#8f8da8;">Carregando anexos…</div>

    <TransitionGroup v-else tag="div" @enter="listEnter" @leave="listLeave" :css="false" style="display:flex; flex-direction:column; gap:8px; margin-bottom:10px;">
      <div v-for="(a, i) in attachments" :key="a.id" :data-index="i" style="background:#0e0e14; border:1px solid #22222f; border-radius:10px; padding:10px; display:flex; gap:10px; align-items:flex-start;">
        <a :href="attachmentHref(a)" target="_blank" rel="noopener" :aria-label="`Abrir ${attachmentName(a)}`" style="flex:none; width:48px; height:48px; border-radius:9px; background:rgba(124,111,255,.1); border:1px solid rgba(124,111,255,.2); display:flex; align-items:center; justify-content:center; color:#9d93ff; font-size:17px;">
          <i class="fi fi-sr-file" aria-hidden="true"></i>
        </a>

        <div style="flex:1; min-width:0;">
          <div style="font-size:12.5px; font-weight:700; color:#f5f4fb; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
            {{ a.caption || attachmentName(a) }}
          </div>
          <div style="margin-top:3px; font-size:10.5px; color:#77758d; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ attachmentName(a) }}</div>
          <div style="font-size:10.5px; color:#8b899f; margin-top:3px;">{{ a.uploaded_by_name || 'Alguém' }} · {{ fmtDate(a.created_at) }}</div>
          <a :href="attachmentHref(a)" target="_blank" rel="noopener" style="display:inline-flex; align-items:center; gap:4px; margin-top:6px; color:#9d93ff; font-size:10.5px; font-weight:700; text-decoration:none;"><i class="fi fi-sr-arrow-up-right-from-square" aria-hidden="true"></i>Abrir arquivo</a>
        </div>

        <button v-if="canDelete(a)" @click="removeAttachment(a)"
          :aria-label="confirmDeleteId === a.id ? 'Confirmar remoção do anexo' : 'Remover anexo'"
          :style="{ border: 'none', background: 'transparent', color: confirmDeleteId === a.id ? '#ff8f98' : '#8f8da8', cursor: 'pointer', fontSize: '12px', flex: 'none' }">
          <i class="fi fi-sr-trash-can-list" aria-hidden="true"></i>
        </button>
      </div>
    </TransitionGroup>
    <div v-if="!loading && !attachments.length" style="font-size:12px; color:#8f8da8; margin-bottom:10px;">Nenhum anexo ainda.</div>

    <div v-if="canUpload" style="background:#0e0e14; border:1px solid #22222f; border-radius:10px; padding:10px; display:flex; flex-direction:column; gap:8px;">
      <div style="display:flex; align-items:center; gap:10px;">
        <label for="attachment-file" style="flex:none; display:inline-flex; align-items:center; gap:6px; border:1px solid #353348; background:#1c1c28; border-radius:8px; padding:8px 12px; font-size:11.5px; font-weight:700; color:#d0cde0; cursor:pointer; white-space:nowrap;">
          <i class="fi fi-sr-folder-upload" aria-hidden="true"></i>Escolher arquivo
        </label>
        <input id="attachment-file" ref="fileInput" type="file" @change="onFileChange" style="position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0,0,0,0);" />
        <span style="font-size:11.5px; color:#8f8da8; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ selectedFileName || 'Qualquer formato de arquivo' }}</span>
      </div>

      <label class="sr-only" for="attachment-caption">Legenda</label>
      <textarea id="attachment-caption" v-autogrow v-model="form.caption" rows="1" maxlength="200" placeholder="Legenda do arquivo (opcional)" style="width:100%; min-height:36px; box-sizing:border-box; border:1px solid #26263a; background:#14141d; border-radius:8px; padding:8px 10px; font:inherit; font-size:12px; line-height:1.5; color:#f5f4fb; outline:none;"></textarea>

      <div v-if="error" style="font-size:11.5px; color:#ff8f98;">{{ error }}</div>

      <button @click="submit" :disabled="submitting" type="button" style="border:none; background:#7c6fff; color:#0a0a10; border-radius:8px; padding:8px 12px; font-size:12px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
        <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
        <i v-else class="fi fi-sr-cloud-upload-alt" aria-hidden="true"></i>{{ submitting ? 'Enviando…' : 'Enviar anexo' }}
      </button>
    </div>
    <div v-else style="font-size:11.5px; color:#8f8da8;">Faça login para anexar arquivos.</div>
  </div>
</template>
