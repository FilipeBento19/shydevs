<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { api } from '../api'
import { auth } from '../auth'
import { initials } from '../utils'

const props = defineProps({
  taskId: { type: [Number, String], required: true },
})
const emit = defineEmits(['changed'])

const comments = ref([])
const draft = ref('')
const loading = ref(true)
const submitting = ref(false)
const deletingId = ref(null)
const confirmDeleteId = ref(null)
const error = ref('')
const listEl = ref(null)

const canSubmit = computed(() => !!draft.value.trim() && !submitting.value)

async function scrollToLatest() {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    comments.value = await api.getComments(props.taskId)
    await scrollToLatest()
  } catch (e) {
    error.value = 'Não foi possível carregar os comentários.'
  } finally {
    loading.value = false
  }
}

watch(() => props.taskId, load, { immediate: true })

function isMine(comment) {
  return comment.author === auth.state.person?.id
}

function canDelete(comment) {
  return isMine(comment) || !!auth.state.person?.is_admin
}

async function submit() {
  const body = draft.value.trim()
  if (!body || submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    const created = await api.createComment({ task: props.taskId, body })
    comments.value.push(created)
    draft.value = ''
    confirmDeleteId.value = null
    emit('changed')
    await scrollToLatest()
  } catch (e) {
    error.value = 'Não foi possível enviar o comentário.'
  } finally {
    submitting.value = false
  }
}

async function remove(comment) {
  if (!canDelete(comment)) return
  if (confirmDeleteId.value !== comment.id) {
    confirmDeleteId.value = comment.id
    return
  }
  deletingId.value = comment.id
  error.value = ''
  try {
    await api.deleteComment(comment.id)
    comments.value = comments.value.filter((item) => item.id !== comment.id)
    confirmDeleteId.value = null
    emit('changed')
  } catch (e) {
    error.value = 'Não foi possível remover o comentário.'
  } finally {
    deletingId.value = null
  }
}

function formatDate(value) {
  const date = new Date(value)
  const today = new Date()
  const sameDay = date.toDateString() === today.toDateString()
  if (sameDay) {
    return `Hoje, ${date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`
  }
  return date.toLocaleString('pt-BR', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}
</script>

<template>
  <section class="comments-panel">
    <header class="comments-header">
      <div>
        <span class="comments-icon"><i class="fi fi-sr-comments" aria-hidden="true"></i></span>
        <div>
          <strong>Comentários</strong>
          <span>Dúvidas, feedback e pedidos de ajuste</span>
        </div>
      </div>
      <span class="comments-count">{{ comments.length }}</span>
    </header>

    <div v-if="loading" class="comments-state" aria-live="polite">Carregando conversa…</div>
    <div v-else ref="listEl" class="comments-list nice-scroll">
      <div v-if="!comments.length" class="comments-empty">
        <i class="fi fi-sr-comment-alt" aria-hidden="true"></i>
        <strong>Comece a conversa</strong>
        <span>Use este espaço para alinhar detalhes desta tarefa.</span>
      </div>

      <article
        v-for="comment in comments"
        :key="comment.id"
        class="comment"
        :class="{ mine: isMine(comment) }"
      >
        <div class="comment-avatar">
          <img v-if="comment.author_photo" :src="comment.author_photo" alt="" />
          <span v-else>{{ initials(comment.author_name) }}</span>
        </div>
        <div class="comment-content">
          <div class="comment-meta">
            <strong>{{ comment.author_name }}</strong>
            <time :datetime="comment.created_at">{{ formatDate(comment.created_at) }}</time>
          </div>
          <p>{{ comment.body }}</p>
        </div>
        <button
          v-if="canDelete(comment)"
          type="button"
          class="delete-comment"
          :class="{ confirming: confirmDeleteId === comment.id }"
          :disabled="deletingId === comment.id"
          :aria-label="confirmDeleteId === comment.id ? 'Confirmar remoção do comentário' : 'Remover comentário'"
          @click="remove(comment)"
        >
          <span v-if="deletingId === comment.id" class="btn-spinner" aria-hidden="true"></span>
          <template v-else>
            <i class="fi fi-sr-trash" aria-hidden="true"></i>
            <span v-if="confirmDeleteId === comment.id">Confirmar</span>
          </template>
        </button>
      </article>
    </div>

    <p v-if="error" class="comments-error" role="alert">{{ error }}</p>

    <form class="comment-form" @submit.prevent="submit">
      <label for="task-comment" class="sr-only">Escrever comentário</label>
      <textarea
        id="task-comment"
        v-model="draft"
        rows="3"
        maxlength="2000"
        placeholder="Escreva uma dúvida ou feedback…"
        @keydown.ctrl.enter.prevent="submit"
        @keydown.meta.enter.prevent="submit"
      ></textarea>
      <div class="comment-form-footer">
        <span>Ctrl + Enter para enviar</span>
        <button type="submit" :disabled="!canSubmit">
          <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
          <i v-else class="fi fi-sr-paper-plane-top" aria-hidden="true"></i>
          {{ submitting ? 'Enviando…' : 'Comentar' }}
        </button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.comments-panel { color: #f5f4fb; }
.comments-header,
.comments-header > div,
.comment,
.comment-meta,
.comment-form-footer { display: flex; align-items: center; }
.comments-header { justify-content: space-between; gap: 12px; margin-bottom: 13px; }
.comments-header > div { gap: 9px; min-width: 0; }
.comments-icon { display: grid; place-items: center; width: 30px; height: 30px; flex: none; border: 1px solid rgba(124,111,255,.22); border-radius: 9px; background: rgba(124,111,255,.1); color: #aaa1ff; font-size: 12px; }
.comments-header strong,
.comments-header div span { display: block; }
.comments-header strong { font-size: 12px; }
.comments-header div span { margin-top: 2px; overflow: hidden; color: #7f7c92; font-size: 9.5px; text-overflow: ellipsis; white-space: nowrap; }
.comments-count { display: grid; place-items: center; min-width: 23px; height: 23px; border: 1px solid #2b2a39; border-radius: 7px; background: #101017; color: #9894ad; font-size: 9.5px; font-weight: 800; }
.comments-list { display: flex; flex-direction: column; gap: 10px; max-height: 340px; overflow-y: auto; padding-inline-end: 4px; }
.comments-state { padding: 18px 0; color: #77758d; font-size: 11px; }
.comments-empty { display: grid; justify-items: center; padding: 20px 12px; border: 1px dashed #292837; border-radius: 9px; color: #77758d; text-align: center; }
.comments-empty > i { margin-bottom: 8px; color: #8f87dd; font-size: 16px; }
.comments-empty strong { color: #aaa7bc; font-size: 11px; }
.comments-empty span { margin-top: 4px; font-size: 9.5px; }
.comment { position: relative; align-items: flex-start; gap: 9px; padding: 10px; border: 1px solid #242331; border-radius: 10px; background: #101017; }
.comment.mine { border-color: rgba(124,111,255,.2); background: rgba(124,111,255,.055); }
.comment-avatar { display: grid; place-items: center; width: 28px; height: 28px; flex: none; overflow: hidden; border-radius: 50%; background: #302b57; color: #c9c3ff; font-size: 8px; font-weight: 800; }
.comment-avatar img { width: 100%; height: 100%; object-fit: cover; }
.comment-content { min-width: 0; flex: 1; }
.comment-meta { gap: 7px; padding-inline-end: 22px; }
.comment-meta strong { overflow: hidden; font-size: 10.5px; text-overflow: ellipsis; white-space: nowrap; }
.comment-meta time { flex: none; color: #686678; font-size: 8.5px; }
.comment-content p { margin: 6px 0 0; color: #bbb8cb; font-size: 11px; line-height: 1.55; white-space: pre-wrap; overflow-wrap: anywhere; }
.delete-comment { position: absolute; inset-inline-end: 6px; top: 6px; display: inline-flex; align-items: center; gap: 4px; min-width: 25px; height: 25px; justify-content: center; padding-inline: 7px; border: 0; border-radius: 7px; background: transparent; color: #656276; font-size: 8.5px; font-weight: 700; cursor: pointer; transition-property: color, background-color; transition-duration: 150ms; }
.delete-comment:hover,
.delete-comment.confirming { background: rgba(224,79,95,.1); color: #ff8f98; }
.delete-comment:disabled { cursor: wait; opacity: .6; }
.comments-error { margin: 9px 0 0; color: #ff8f98; font-size: 10px; }
.comment-form { margin-top: 12px; overflow: hidden; border: 1px solid #292837; border-radius: 10px; background: #0e0e14; transition-property: border-color; transition-duration: 150ms; }
.comment-form:focus-within { border-color: rgba(124,111,255,.7); }
.comment-form textarea { display: block; width: 100%; min-height: 72px; box-sizing: border-box; padding: 10px 11px; resize: vertical; border: 0; outline: 0; background: transparent; color: #f5f4fb; font: inherit; font-size: 11.5px; line-height: 1.5; }
.comment-form textarea::placeholder { color: #656276; }
.comment-form-footer { justify-content: space-between; gap: 10px; padding: 7px 8px; border-top: 1px solid #20202b; }
.comment-form-footer > span { color: #5f5c70; font-size: 8.5px; }
.comment-form-footer button { display: inline-flex; align-items: center; gap: 5px; min-height: 29px; padding: 0 9px; border: 0; border-radius: 7px; background: #7c6fff; color: #0a0a10; font: inherit; font-size: 9.5px; font-weight: 800; cursor: pointer; }
.comment-form-footer button:disabled { cursor: not-allowed; opacity: .45; }
</style>
