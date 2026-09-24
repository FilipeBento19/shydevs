<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'
import { auth } from '../auth'
import { linkThumbnail, hostOf, referenceSource, referenceTitle } from '../mediaUtils'
import MediaViewer from './MediaViewer.vue'

const props = defineProps({
  taskId: { type: [Number, String], required: true },
})
const emit = defineEmits(['count'])

const references = ref([])
const loading = ref(true)
const error = ref('')
const confirmDeleteId = ref(null)
const viewer = ref(null) // { group, index }

const canUpload = computed(() => auth.isLoggedIn)

// ---- data ----
async function load() {
  loading.value = true
  error.value = ''
  try {
    references.value = await api.getReferences(props.taskId)
  } catch (e) {
    error.value = 'Não foi possível carregar as referências.'
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => props.taskId, load)
watch(() => references.value.length, (n) => emit('count', n), { immediate: true })

// Groups in order of first appearance (references arrive oldest-first).
const groups = computed(() => {
  const map = new Map()
  for (const ref_ of references.value) {
    if (!map.has(ref_.group)) map.set(ref_.group, [])
    map.get(ref_.group).push(ref_)
  }
  return [...map.entries()].map(([name, items]) => ({ name, items }))
})
const groupNames = computed(() => groups.value.map((g) => g.name))

// ---- viewer ----
const viewerItems = computed(() => groups.value.find((g) => g.name === viewer.value?.group)?.items || [])
function openViewer(group, index) {
  viewer.value = { group: group.name, index }
}

// ---- add form ----
const form = reactive({ group: '', mode: 'file', url: '', caption: '' })
const fileInput = ref(null)
const selectedFiles = ref([])
const submitting = ref(false)
const progressLabel = ref('')
const groupInput = ref(null)
const dragging = ref(false)

function onFileChange(e) {
  selectedFiles.value = [...(e.target.files || [])]
}
function onDrop(e) {
  dragging.value = false
  const files = [...(e.dataTransfer?.files || [])]
  if (!files.length) return
  form.mode = 'file'
  selectedFiles.value = files
  if (fileInput.value) {
    try { fileInput.value.files = e.dataTransfer.files } catch (err) { /* selectedFiles is the source of truth */ }
  }
}
const selectedLabel = computed(() => {
  const n = selectedFiles.value.length
  if (!n) return 'Imagens, vídeos ou qualquer arquivo'
  return n === 1 ? selectedFiles.value[0].name : `${n} arquivos selecionados`
})

function addToGroup(name) {
  form.group = name
  nextTick(() => groupInput.value?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
}

async function submit() {
  error.value = ''
  const group = form.group.trim() || 'Geral'
  const url = form.url.trim()
  if (form.mode === 'file' && !selectedFiles.value.length) {
    error.value = 'Escolha ao menos um arquivo.'
    return
  }
  if (form.mode === 'link' && !url) {
    error.value = 'Cole o link da referência.'
    return
  }
  submitting.value = true
  try {
    if (form.mode === 'link') {
      const created = await api.createReference({ task: props.taskId, group, url, caption: form.caption.trim() })
      references.value.push(created)
    } else {
      const files = selectedFiles.value
      for (let i = 0; i < files.length; i++) {
        progressLabel.value = files.length > 1 ? `Enviando ${i + 1}/${files.length}…` : 'Enviando…'
        // A caption only makes sense for a single file; with several, each
        // keeps its own file name as its title.
        const created = await api.createReference({
          task: props.taskId, group, file: files[i], caption: files.length === 1 ? form.caption.trim() : '',
        })
        references.value.push(created)
      }
    }
    form.url = ''
    form.caption = ''
    selectedFiles.value = []
    if (fileInput.value) fileInput.value.value = ''
    form.group = group
  } catch (e) {
    error.value = e.message && e.message.length < 200 ? e.message : 'Não foi possível salvar a referência.'
  } finally {
    submitting.value = false
    progressLabel.value = ''
  }
}

// ---- delete ----
function canDelete(r) {
  const person = auth.state.person
  return !!person && (person.is_admin || r.uploaded_by === person.id)
}
async function remove(r) {
  if (confirmDeleteId.value !== r.id) {
    confirmDeleteId.value = r.id
    setTimeout(() => { if (confirmDeleteId.value === r.id) confirmDeleteId.value = null }, 3500)
    return
  }
  try {
    await api.deleteReference(r.id)
    references.value = references.value.filter((x) => x.id !== r.id)
    confirmDeleteId.value = null
    if (viewer.value && !viewerItems.value.length) viewer.value = null
  } catch (e) {
    error.value = 'Não foi possível remover essa referência.'
  }
}

// ---- tiles ----
const KIND_ICON = { image: 'fi-sr-picture', video: 'fi-sr-video-camera', link: 'fi-sr-link', file: 'fi-sr-file' }
const KIND_LABEL = { image: 'Imagem', video: 'Vídeo', link: 'Link', file: 'Arquivo' }
function thumbFor(r) {
  if (r.kind === 'image') return referenceSource(r)
  if (r.kind === 'link') return linkThumbnail(r.url)
  return null
}
function subtitle(r) {
  if (r.kind === 'link') return hostOf(r.url)
  return r.file_name || KIND_LABEL[r.kind]
}
function hideBroken(e) {
  e.target.style.display = 'none'
}
</script>

<template>
  <div class="refs">
    <div class="intro">
      <span class="pill">CONSULTA</span>
      <p>
        Material de apoio para <strong>quem vai executar</strong> a tarefa: quem passa a demanda coloca aqui os
        exemplos, conceitos e links de referência. A <strong>entrega</strong> de quem fez o trabalho não vai aqui —
        vai na aba <em>Detalhes</em>, em “Entrega do responsável”.
      </p>
    </div>

    <!-- add form -->
    <section v-if="canUpload" class="refs-form" :class="{ dragging }" aria-label="Adicionar referência"
      @dragover.prevent="dragging = true" @dragleave.prevent="dragging = false" @drop.prevent="onDrop">
      <div class="refs-form-grid">
        <div class="field">
          <label for="ref-group">Grupo</label>
          <input id="ref-group" ref="groupInput" v-model="form.group" list="ref-group-options" maxlength="80" placeholder="Ex.: Skill 1" autocomplete="off" />
          <datalist id="ref-group-options"><option v-for="g in groupNames" :key="g" :value="g"></option></datalist>
        </div>

        <div class="field">
          <span class="label">Tipo</span>
          <div class="seg" role="radiogroup" aria-label="Tipo de referência">
            <button type="button" role="radio" :aria-checked="form.mode === 'file'" :class="{ on: form.mode === 'file' }" @click="form.mode = 'file'">
              <i class="fi fi-sr-folder-upload" aria-hidden="true"></i>Arquivo
            </button>
            <button type="button" role="radio" :aria-checked="form.mode === 'link'" :class="{ on: form.mode === 'link' }" @click="form.mode = 'link'">
              <i class="fi fi-sr-link" aria-hidden="true"></i>Link
            </button>
          </div>
        </div>

        <div class="field wide">
          <template v-if="form.mode === 'file'">
            <span class="label">Arquivos</span>
            <label class="file-pick" for="ref-file">
              <i class="fi fi-sr-cloud-upload-alt" aria-hidden="true"></i>
              <span>{{ selectedLabel }}</span>
              <em>ou arraste pra cá</em>
            </label>
            <input id="ref-file" ref="fileInput" type="file" multiple class="file-hidden" @change="onFileChange" />
          </template>
          <template v-else>
            <label for="ref-url">Link</label>
            <input id="ref-url" v-model="form.url" type="url" placeholder="https://… (YouTube, Vimeo, imagem, vídeo ou qualquer página)" @keyup.enter="submit" />
          </template>
        </div>

        <div class="field wide">
          <label for="ref-caption">Legenda (opcional)</label>
          <input id="ref-caption" v-model="form.caption" maxlength="200" placeholder="O que essa referência mostra?" @keyup.enter="submit" />
        </div>

        <button type="button" class="submit" :disabled="submitting" @click="submit">
          <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
          <i v-else class="fi fi-sr-plus-small" aria-hidden="true"></i>{{ submitting ? (progressLabel || 'Enviando…') : 'Adicionar' }}
        </button>
      </div>
      <div v-if="error" class="err" role="alert">{{ error }}</div>
    </section>
    <div v-else class="hint">Faça login para adicionar referências.</div>

    <!-- content -->
    <div v-if="loading" class="hint">Carregando referências…</div>
    <div v-else-if="!groups.length" class="empty">
      <i class="fi fi-sr-picture" aria-hidden="true"></i>
      <strong>Nenhuma referência ainda</strong>
      <span>Quem passa a demanda reúne aqui imagens, vídeos e links pra quem vai executar, separados por grupo (por exemplo “Skill 1”).</span>
    </div>

    <section v-for="g in groups" :key="g.name" class="group" :aria-label="`Grupo ${g.name}`">
      <header class="group-head">
        <h3>{{ g.name }}</h3>
        <span class="count">{{ g.items.length }}</span>
        <button v-if="canUpload" type="button" class="link-btn" @click="addToGroup(g.name)"><i class="fi fi-sr-plus-small" aria-hidden="true"></i>Adicionar aqui</button>
      </header>

      <div class="grid">
        <article v-for="(r, i) in g.items" :key="r.id" class="tile">
          <button type="button" class="tile-open" :aria-label="`Abrir ${referenceTitle(r)}`" @click="openViewer(g, i)">
            <span class="thumb">
              <i :class="`fi ${KIND_ICON[r.kind]} thumb-icon`" aria-hidden="true"></i>
              <img v-if="thumbFor(r)" :src="thumbFor(r)" alt="" loading="lazy" @error="hideBroken" />
              <video v-else-if="r.kind === 'video'" :src="`${referenceSource(r)}#t=0.1`" preload="metadata" muted playsinline tabindex="-1"></video>
              <span v-if="r.kind === 'video'" class="badge play"><i class="fi fi-sr-play" aria-hidden="true"></i></span>
              <span v-else-if="r.kind === 'link'" class="badge">{{ hostOf(r.url) }}</span>
            </span>
            <span class="meta">
              <strong>{{ referenceTitle(r) }}</strong>
              <small>{{ subtitle(r) }} · {{ r.uploaded_by_name || 'Alguém' }}</small>
            </span>
          </button>
          <button v-if="canDelete(r)" type="button" class="del" :class="{ confirm: confirmDeleteId === r.id }"
            :aria-label="confirmDeleteId === r.id ? 'Confirmar remoção' : `Remover ${referenceTitle(r)}`" @click="remove(r)">
            <i class="fi fi-sr-trash-can-list" aria-hidden="true"></i><span v-if="confirmDeleteId === r.id">Remover?</span>
          </button>
        </article>
      </div>
    </section>

    <MediaViewer v-if="viewer && viewerItems.length" :items="viewerItems" :index="Math.min(viewer.index, viewerItems.length - 1)"
      @update:index="viewer.index = $event" @close="viewer = null" />
  </div>
</template>

<style scoped>
.refs { display: flex; flex-direction: column; gap: 16px; }
.hint { font-size: 12.5px; color: #8b899f; }
.intro { display: flex; align-items: flex-start; gap: 10px; padding: 11px 14px; background: rgba(124, 111, 255, .08); border: 1px solid rgba(124, 111, 255, .22); border-radius: 12px; }
.intro p { margin: 0; font-size: 12px; line-height: 1.55; color: #b8b5d0; }
.intro strong { color: #f5f4fb; }
.intro em { font-style: normal; color: #b3aaff; font-weight: 700; }
.pill { flex: none; margin-top: 1px; font-size: 9.5px; font-weight: 800; letter-spacing: .05em; color: #b3aaff; background: rgba(124, 111, 255, .18); border-radius: 999px; padding: 3px 9px; }
.err { margin-top: 10px; padding: 9px 12px; background: rgba(224, 79, 95, .14); border: 1px solid rgba(224, 79, 95, .35); border-radius: 9px; color: #ff8f98; font-size: 12px; font-weight: 600; }

.refs-form { background: #14141d; border: 1px solid #22222f; border-radius: 12px; padding: 14px; transition: border-color .15s ease, background-color .15s ease; }
.refs-form.dragging { border-color: #7c6fff; background: rgba(124, 111, 255, .07); }
.refs-form-grid { display: grid; grid-template-columns: 180px 190px minmax(0, 1fr) auto; gap: 12px; align-items: end; }
.field { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.field.wide { grid-column: span 1; }
.field label, .field .label { font-size: 11.5px; font-weight: 700; color: #c7c5dc; }
.field input { width: 100%; box-sizing: border-box; border: 1px solid #26263a; background: #0e0e14; border-radius: 9px; padding: 9px 11px; font-size: 12.5px; color: #f5f4fb; outline: none; height: 38px; }
.field input:focus { border-color: #7c6fff; }
/* visually hidden but still focusable/labelled; must out-rank `.field input` above */
.field input.file-hidden { position: absolute; width: 1px; height: 1px; padding: 0; border: 0; margin: -1px; opacity: 0; overflow: hidden; clip: rect(0 0 0 0); pointer-events: none; }
.file-pick:focus-within { border-color: #7c6fff; }
.seg { display: flex; background: #0e0e14; border: 1px solid #26263a; border-radius: 9px; padding: 3px; gap: 3px; height: 38px; box-sizing: border-box; }
.seg button { flex: 1; border: none; background: transparent; color: #8b899f; font-size: 12px; font-weight: 700; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
.seg button.on { background: rgba(124, 111, 255, .2); color: #d6d0ff; }
.file-pick { display: flex; align-items: center; gap: 9px; height: 38px; box-sizing: border-box; border: 1px dashed #3a3850; background: #0e0e14; border-radius: 9px; padding: 0 11px; font-size: 12.5px; color: #c7c5dc; cursor: pointer; min-width: 0; }
.file-pick:hover { border-color: #7c6fff; }
.file-pick span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-pick em { font-style: normal; font-size: 11px; color: #65637a; white-space: nowrap; }
.file-pick i { color: #9d93ff; }
.submit { height: 38px; border: none; background: #7c6fff; color: #0a0a10; border-radius: 9px; padding: 0 18px; font-size: 12.5px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px; white-space: nowrap; }
.submit:disabled { opacity: .7; cursor: default; }
/* the "Legenda" field sits on its own row, full width */
.refs-form-grid > .field.wide:nth-of-type(4) { grid-column: 1 / -2; }

.empty { display: flex; flex-direction: column; align-items: center; gap: 6px; text-align: center; padding: 38px 20px; background: #14141d; border: 1px dashed #2a2a3a; border-radius: 12px; color: #8b899f; font-size: 12.5px; }
.empty i { font-size: 26px; opacity: .5; }
.empty strong { color: #e4e2f1; font-size: 13.5px; }

.group { display: flex; flex-direction: column; gap: 10px; }
.group-head { display: flex; align-items: center; gap: 10px; }
.group-head h3 { margin: 0; font-size: 14px; font-weight: 800; color: #f5f4fb; letter-spacing: -.01em; }
.count { font-size: 11px; font-weight: 700; color: #8b899f; background: #14141d; border: 1px solid #22222f; border-radius: 999px; padding: 2px 9px; }
.link-btn { margin-left: auto; border: none; background: transparent; color: #9d93ff; font-size: 11.5px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }
.link-btn:hover { color: #c7c1ff; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; }
.tile { position: relative; background: #14141d; border: 1px solid #22222f; border-radius: 12px; overflow: hidden; transition: border-color .15s ease, transform .15s ease; }
.tile:hover, .tile:focus-within { border-color: #4a4670; transform: translateY(-2px); }
.tile-open { display: block; width: 100%; padding: 0; border: none; background: transparent; text-align: left; cursor: pointer; color: inherit; font: inherit; }
.thumb { position: relative; display: flex; align-items: center; justify-content: center; aspect-ratio: 16 / 10; background: #0b0b11; overflow: hidden; }
.thumb-icon { position: absolute; font-size: 26px; color: #4f4d68; }
.thumb img, .thumb video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; pointer-events: none; }
.badge { position: absolute; left: 8px; bottom: 8px; max-width: calc(100% - 16px); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 10px; font-weight: 700; color: #f5f4fb; background: rgba(11, 11, 17, .78); border-radius: 6px; padding: 3px 7px; backdrop-filter: blur(4px); }
.badge.play { left: 50%; bottom: 50%; transform: translate(-50%, 50%); width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-size: 13px; padding: 0 0 0 2px; background: rgba(20, 20, 29, .72); }
.meta { display: flex; flex-direction: column; gap: 2px; padding: 9px 11px 11px; }
.meta strong { font-size: 12.5px; color: #f5f4fb; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meta small { font-size: 10.5px; color: #77758d; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.del { position: absolute; top: 8px; right: 8px; height: 28px; min-width: 28px; padding: 0 8px; border: 1px solid rgba(255, 255, 255, .12); background: rgba(11, 11, 17, .78); color: #c7c5dc; border-radius: 8px; font-size: 11px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 5px; opacity: 0; transition: opacity .15s ease; backdrop-filter: blur(4px); }
.tile:hover .del, .tile:focus-within .del, .del.confirm { opacity: 1; }
.del.confirm { color: #ff8f98; border-color: rgba(224, 79, 95, .5); background: rgba(60, 14, 20, .85); }
@media (hover: none) { .del { opacity: 1; } }

@media (max-width: 900px) {
  .refs-form-grid { grid-template-columns: 1fr 1fr; }
  .field.wide, .refs-form-grid > .field.wide:nth-of-type(4) { grid-column: 1 / -1; }
  .submit { grid-column: 1 / -1; }
}
@media (max-width: 480px) {
  .refs-form-grid { grid-template-columns: 1fr; }
  .grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
}
</style>
