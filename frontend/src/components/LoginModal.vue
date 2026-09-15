<script setup>
import { nextTick, reactive, ref, watch } from 'vue'
import { auth } from '../auth'
import { modalEnter, modalLeave } from '../motion'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['close', 'logged-in'])

const form = reactive({ name: '', password: '' })
const error = ref('')
const loading = ref(false)
const nameInputEl = ref(null)

watch(
  () => props.open,
  async (val) => {
    if (val) {
      form.name = ''
      form.password = ''
      error.value = ''
      await nextTick()
      nameInputEl.value?.focus()
    }
  }
)

async function submit() {
  error.value = ''
  if (!form.name.trim() || !form.password) {
    error.value = 'Preencha nome e senha.'
    return
  }
  loading.value = true
  try {
    const person = await auth.login(form.name.trim(), form.password)
    emit('logged-in', person)
    emit('close')
  } catch (e) {
    error.value = e.status === 401 ? 'Nome ou senha incorretos.' : 'Não foi possível entrar. Tente novamente.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
  <Transition :css="false" @enter="modalEnter" @leave="modalLeave">
  <div v-if="open" @click="$emit('close')" style="position:fixed; inset:0; background:rgba(3,3,8,.82); display:flex; align-items:center; justify-content:center; padding:24px; z-index:1000; overflow-y:auto;">
    <div class="modal-panel" @click.stop role="dialog" aria-modal="true" aria-labelledby="login-modal-title" style="width:100%; max-width:360px; background:#14141d; border:1px solid #26263a; border-radius:14px; padding:22px; box-shadow:0 24px 70px rgba(0,0,0,.6); margin:auto;">
      <div style="font-size:10.5px; font-weight:800; letter-spacing:.08em; color:#b3aaff; margin-bottom:6px;">● SHYDEVS</div>
      <div id="login-modal-title" style="font-size:19px; font-weight:800; color:#f5f4fb; letter-spacing:-.02em;">Entrar</div>
      <div style="font-size:12.5px; color:#9a97b8; margin-top:4px; margin-bottom:18px;">Use seu nome da equipe e sua senha.</div>

      <form @submit.prevent="submit" style="display:flex; flex-direction:column; gap:12px;">
        <div>
          <label for="login-name" style="display:block; font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Nome</label>
          <input id="login-name" ref="nameInputEl" v-model="form.name" placeholder="Shy Moreira" style="width:100%; box-sizing:border-box; border:1px solid #26263a; background:#0e0e14; border-radius:9px; padding:10px 12px; font-size:12.5px; color:#f5f4fb; outline:none;" />
        </div>
        <div>
          <label for="login-password" style="display:block; font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Senha</label>
          <input id="login-password" v-model="form.password" type="password" placeholder="••••••••" style="width:100%; box-sizing:border-box; border:1px solid #26263a; background:#0e0e14; border-radius:9px; padding:10px 12px; font-size:12.5px; color:#f5f4fb; outline:none;" />
        </div>

        <div v-if="error" role="alert" style="padding:9px 11px; background:rgba(224,79,95,.14); border:1px solid rgba(224,79,95,.35); border-radius:9px; color:#ff8f98; font-size:12px; font-weight:600;">
          {{ error }}
        </div>

        <button type="submit" :disabled="loading" style="margin-top:6px; border:none; background:#7c6fff; color:#0a0a10; border-radius:9px; padding:10px 16px; font-size:12.5px; font-weight:700; cursor:pointer;">
          {{ loading ? 'Entrando…' : 'Entrar' }}
        </button>
        <button type="button" @click="$emit('close')" style="border:1px solid #26263a; background:#0e0e14; border-radius:9px; padding:10px 16px; font-size:12.5px; font-weight:700; color:#c7c5dc; cursor:pointer;">Cancelar</button>
      </form>
    </div>
  </div>
  </Transition>
  </Teleport>
</template>
