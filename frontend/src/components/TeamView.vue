<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import { listEnter, listLeave } from '../motion'
import { initials, roleIcon } from '../utils'
import CustomSelect from './CustomSelect.vue'

const emit = defineEmits(['changed'])

const roles = ref([])
const roleOptions = computed(() => roles.value.map((r) => ({ value: r.name, label: r.name, icon: roleIcon(r.name), color: r.color })))

const people = ref([])
const loading = ref(true)
const error = ref('')
const submitting = ref(false)
const confirmDeleteId = ref(null)

const form = reactive({ name: '', role: 'Modelador', password: '', is_admin: false })

const adminCount = computed(() => people.value.filter((p) => p.is_admin).length)

function roleColor(name) {
  return (roles.value.find((r) => r.name === name) || {}).color || '#9a9ab0'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [peopleList, roleList] = await Promise.all([api.getPeople(), api.getRoles()])
    people.value = peopleList
    roles.value = roleList
  } catch (e) {
    error.value = 'Não foi possível carregar a equipe.'
  } finally {
    loading.value = false
  }
}
defineExpose({ load })
onMounted(load)

async function addPerson() {
  error.value = ''
  if (!form.name.trim()) {
    error.value = 'Informe o nome.'
    return
  }
  submitting.value = true
  try {
    const created = await api.createPerson({
      name: form.name.trim(),
      role: form.role,
      password: form.password || undefined,
      is_admin: form.is_admin,
    })
    people.value.push(created)
    form.name = ''
    form.password = ''
    form.is_admin = false
    emit('changed')
  } catch (e) {
    error.value = 'Não foi possível adicionar essa pessoa.'
  } finally {
    submitting.value = false
  }
}

async function toggleAdmin(person) {
  error.value = ''
  if (person.is_admin && adminCount.value <= 1) {
    error.value = 'Precisa existir pelo menos um administrador.'
    return
  }
  try {
    const updated = await api.updatePerson(person.id, { is_admin: !person.is_admin })
    people.value = people.value.map((p) => (p.id === updated.id ? updated : p))
    emit('changed')
  } catch (e) {
    error.value = 'Não foi possível alterar o nível dessa pessoa.'
  }
}

async function removePerson(person) {
  if (confirmDeleteId.value !== person.id) {
    confirmDeleteId.value = person.id
    return
  }
  try {
    await api.deletePerson(person.id)
    people.value = people.value.filter((p) => p.id !== person.id)
    confirmDeleteId.value = null
    emit('changed')
  } catch (e) {
    error.value = 'Não foi possível remover essa pessoa.'
  }
}
</script>

<template>
  <div style="padding:20px 26px 26px;">
    <div style="display:grid; grid-template-columns:minmax(0,1fr) 300px; gap:16px; align-items:start;">
      <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; overflow:hidden;">
        <div style="padding:14px 16px; border-bottom:1px solid #1f1f2b; font-size:12.5px; font-weight:800; color:#f5f4fb;">Equipe</div>
        <div v-if="loading" style="padding:20px; font-size:12.5px; color:#8b899f;">Carregando…</div>
        <div v-else-if="!people.length" style="padding:20px; font-size:12.5px; color:#8b899f;">Ninguém cadastrado ainda. Adicione a primeira pessoa ao lado.</div>
        <TransitionGroup v-else tag="div" @enter="listEnter" @leave="listLeave" :css="false">
          <div v-for="(p, i) in people" :key="p.id" :data-index="i" style="display:flex; align-items:center; gap:10px; padding:11px 16px; border-bottom:1px solid #1a1a25;">
            <span :style="{ width: '30px', height: '30px', flex: 'none', borderRadius: '50%', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontWeight: '800', color: '#0a0a10', background: roleColor(p.role), backgroundImage: p.photo ? `url(${p.photo})` : 'none', backgroundSize: 'cover', backgroundPosition: 'center' }">{{ p.photo ? '' : initials(p.name) }}</span>
            <div style="flex:1; min-width:0;">
              <div style="font-size:12.5px; font-weight:700; color:#f5f4fb; display:flex; align-items:center; gap:6px;">
                {{ p.name }}
                <span v-if="p.is_admin" style="font-size:9.5px; font-weight:700; letter-spacing:.04em; color:#b3aaff; background:rgba(124,111,255,.16); border-radius:999px; padding:2px 7px;">ADMIN</span>
              </div>
              <div style="font-size:11px; color:#8b899f; display:flex; align-items:center; gap:4px; margin-top:1px;"><i :class="`fi ${roleIcon(p.role)}`" style="opacity:.7;"></i>{{ p.role }}</div>
            </div>
            <div style="display:flex; gap:6px; flex:none;">
              <button @click="toggleAdmin(p)"
                :style="{ border: '1px solid #26263a', background: 'transparent', color: p.is_admin ? '#8b899f' : '#b3aaff', borderRadius: '7px', padding: '6px 10px', fontSize: '11px', fontWeight: '700', cursor: 'pointer', whiteSpace: 'nowrap' }">
                <i :class="`fi ${p.is_admin ? 'fi-sr-user-minus' : 'fi-sr-user-shield'}`"></i> {{ p.is_admin ? 'Tirar admin' : 'Tornar admin' }}
              </button>
              <button v-if="!p.is_admin" @click="removePerson(p)"
                :style="{ border: '1px solid rgba(224,79,95,.4)', background: confirmDeleteId === p.id ? 'rgba(224,79,95,.18)' : 'transparent', color: '#ff8f98', borderRadius: '7px', padding: '6px 10px', fontSize: '11px', fontWeight: '700', cursor: 'pointer', whiteSpace: 'nowrap' }">
                <i class="fi fi-sr-trash-can-list"></i> {{ confirmDeleteId === p.id ? 'Confirmar?' : 'Remover' }}
              </button>
            </div>
          </div>
        </TransitionGroup>
      </div>

      <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
        <div style="font-size:12.5px; font-weight:800; color:#f5f4fb; margin-bottom:12px;">Adicionar pessoa</div>
        <div style="display:flex; flex-direction:column; gap:10px;">
          <div>
            <div style="font-size:11.5px; font-weight:700; color:#c7c5dc; margin-bottom:5px;">Nome</div>
            <input v-model="form.name" @keyup.enter="addPerson" placeholder="Nome da pessoa" style="width:100%; box-sizing:border-box; border:1px solid #26263a; background:#0e0e14; border-radius:8px; padding:9px 10px; font-size:12.5px; color:#f5f4fb; outline:none;" />
          </div>
          <div>
            <div style="font-size:11.5px; font-weight:700; color:#c7c5dc; margin-bottom:5px;">Cargo</div>
            <CustomSelect v-model="form.role" :options="roleOptions" width="100%" />
          </div>
          <div>
            <div style="font-size:11.5px; font-weight:700; color:#c7c5dc; margin-bottom:5px;">Senha (opcional)</div>
            <input v-model="form.password" type="password" placeholder="Para essa pessoa poder entrar" style="width:100%; box-sizing:border-box; border:1px solid #26263a; background:#0e0e14; border-radius:8px; padding:9px 10px; font-size:12.5px; color:#f5f4fb; outline:none;" />
          </div>
          <label style="display:flex; align-items:center; gap:8px; font-size:12px; color:#c7c5dc; cursor:pointer;">
            <input type="checkbox" v-model="form.is_admin" style="width:14px; height:14px; accent-color:#7c6fff; cursor:pointer;" />
            Tornar administrador (pode alterar tarefas e a equipe)
          </label>
          <div v-if="error" style="padding:8px 10px; background:rgba(224,79,95,.14); border:1px solid rgba(224,79,95,.35); border-radius:8px; color:#ff8f98; font-size:11.5px; font-weight:600;">{{ error }}</div>
          <button @click="addPerson" :disabled="submitting" style="border:none; background:#7c6fff; color:#0a0a10; border-radius:8px; padding:9px 12px; font-size:12.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
            <i class="fi fi-sr-plus-small"></i>{{ submitting ? 'Adicionando…' : 'Adicionar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
