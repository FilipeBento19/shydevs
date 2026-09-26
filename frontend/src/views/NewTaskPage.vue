<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { vAutogrow } from '../directives/autogrow'
import { bumpTasks } from '../taskBus'
import { mascot } from '../mascotFace'
import RoleSelectButtons from '../components/RoleSelectButtons.vue'
import PrioritySelectButtons from '../components/PrioritySelectButtons.vue'
import DueDateField from '../components/DueDateField.vue'
import AssigneeSelect from '../components/AssigneeSelect.vue'
import GroupPicker from '../components/GroupPicker.vue'
import BackButton from '../components/BackButton.vue'
import CustomSelect from '../components/CustomSelect.vue'

const router = useRouter()

const roles = ref([])
const people = ref([])
const tasks = ref([])
const loadingRefs = ref(true)

async function loadRefs() {
  loadingRefs.value = true
  try {
    const [roleList, peopleList, taskList] = await Promise.all([
      api.getRoles(), api.getPeople(), api.getTasks(),
    ])
    roles.value = roleList
    people.value = peopleList
    tasks.value = taskList
    form.role = roleList[0]?.name || 'Modelador'
  } catch (e) {
    // form still usable
  } finally {
    loadingRefs.value = false
  }
}
onMounted(loadRefs)

const form = reactive({
  title: '', description: '', role: 'Modelador', assignee: null, due_date: '', priority: 'Alta', depends_on: null, kind: 'solo', participants: [],
})
const dependencyOptions = computed(() => [
  { value: null, label: 'Nenhuma' },
  ...tasks.value.map((t) => ({ value: t.id, label: `${t.code} · ${t.title}` })),
])
const submitting = ref(false)
const formError = ref('')
const checklist = ref([''])

const formPeople = computed(() => people.value.filter((p) => (p.roles || []).includes(form.role)))
const assigneeOptions = computed(() => formPeople.value.map((p) => ({
  value: p.id,
  label: `${p.name} — ${(p.roles || []).join(', ')} (${tasks.value.filter((t) => (t.assignee === p.id || t.participants?.includes(p.id)) && t.status !== 'Concluída').length} abertas)`,
})))

const KINDS = [
  { value: 'solo', label: 'Tarefa solo', hint: 'Uma pessoa responsável', icon: 'fi-sr-user' },
  { value: 'group', label: 'Tarefa em grupo', hint: 'Várias pessoas ou cargos', icon: 'fi-sr-users' },
]

// A group task still has one "cargo" (its category/color): the first one the picked people have.
function groupRole() {
  const chosen = people.value.filter((p) => form.participants.includes(p.id))
  const names = roles.value.map((r) => r.name)
  return chosen.flatMap((p) => p.roles || []).find((r) => names.includes(r)) || form.role
}

function onRoleChange(name) {
  form.role = name
  form.assignee = null
}

function goBack() {
  router.push({ name: 'board' })
}

function addChecklistItem() {
  if (!checklist.value.at(-1)?.trim()) return
  checklist.value.push('')
}

function removeChecklistItem(index) {
  if (checklist.value.length === 1) {
    checklist.value[0] = ''
    return
  }
  checklist.value.splice(index, 1)
}

async function submit() {
  formError.value = ''
  if (!form.title.trim()) {
    formError.value = 'Informe o título da tarefa.'
    return
  }
  const group = form.kind === 'group'
  if (group && form.participants.length < 2) {
    formError.value = 'Escolha pelo menos 2 pessoas para uma tarefa em grupo.'
    return
  }
  if (!group && !form.assignee) {
    formError.value = 'Selecione a pessoa responsável.'
    return
  }
  submitting.value = true
  try {
    const created = await api.createTask({
      title: form.title,
      description: form.description,
      role: group ? groupRole() : form.role,
      kind: form.kind,
      assignee: group ? form.participants[0] : form.assignee,
      participants: group ? form.participants : [],
      due_date: form.due_date || null,
      priority: form.priority,
      depends_on: form.depends_on,
      status: 'Pendente',
    })
    const steps = checklist.value.map((item) => item.trim()).filter(Boolean)
    await Promise.all(steps.map((title, order) => api.createSubtask({
      task: created.id,
      title,
      order,
    })))
    bumpTasks()
    router.push({ name: 'task', params: { id: created.id } })
  } catch (e) {
    formError.value = 'Não foi possível criar a tarefa. Tente novamente.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div style="padding:18px 26px 26px; display:flex; flex-direction:column; align-items:center;">
    <div style="width:100%; max-width:560px;">
      <BackButton @click="goBack" />

      <div style="display:flex; align-items:center; justify-content:center; gap:6px; font-size:10.5px; font-weight:800; letter-spacing:.08em; color:#b3aaff; margin-bottom:8px;">
        <img :src="mascot" alt="" style="width:18px; height:18px; object-fit:contain;" />SHYDEVS
      </div>
      <div style="font-size:22px; font-weight:800; color:#f5f4fb; letter-spacing:-.02em; margin-bottom:4px; text-align:center;">Atribuir Nova Tarefa</div>
      <div style="font-size:12.5px; color:#9a97b8; margin-bottom:20px; text-align:center;">
        {{ form.kind === 'group' ? 'Escolha as pessoas (ou cargos inteiros) que vão fazer essa demanda juntas' : 'Escolha o cargo e delegue a demanda a um especialista' }}
      </div>

      <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:18px;">
        <div role="radiogroup" aria-label="Tipo de tarefa" class="kind-toggle">
          <button v-for="k in KINDS" :key="k.value" type="button" role="radio" :aria-checked="form.kind === k.value"
            :class="{ active: form.kind === k.value }" @click="form.kind = k.value">
            <i :class="`fi ${k.icon}`" aria-hidden="true"></i>
            <span><strong>{{ k.label }}</strong><small>{{ k.hint }}</small></span>
          </button>
        </div>
        <div style="display:flex; flex-direction:column; gap:14px;">
          <div>
            <label for="new-task-title" style="display:block; font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Título da tarefa <span style="color:#ff8f98;">*</span></label>
            <input id="new-task-title" v-model="form.title" placeholder="Modelar conjunto de props do lobby v2" style="width:100%; box-sizing:border-box; border:1px solid #26263a; background:#0e0e14; border-radius:9px; padding:10px 12px; font-size:12.5px; color:#f5f4fb; outline:none;" />
          </div>
          <div>
            <label for="new-task-desc" style="display:block; font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Descrição curta</label>
            <textarea id="new-task-desc" v-autogrow v-model="form.description" rows="2" placeholder="Definir escopo, referências e limite de polycount" style="width:100%; box-sizing:border-box; border:1px solid #26263a; background:#0e0e14; border-radius:9px; padding:10px 12px; font-size:12.5px; color:#f5f4fb; outline:none;"></textarea>
          </div>
          <div>
            <div style="display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:7px;">
              <div>
                <div style="font-size:12px; font-weight:700; color:#c7c5dc;">Checklist do que fazer</div>
                <div style="margin-top:2px; font-size:10px; color:#77758d;">Deixe as etapas prontas para quem receber a tarefa.</div>
              </div>
              <span style="font-size:9.5px; color:#8b899f;">{{ checklist.filter(item => item.trim()).length }} etapas</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:7px;">
              <div v-for="(item, index) in checklist" :key="index" style="display:flex; align-items:center; gap:7px;">
                <span style="display:grid; place-items:center; width:24px; height:24px; flex:none; border:1px solid #292837; border-radius:7px; background:#101017; color:#8f87dd; font-size:9px; font-weight:800;">{{ index + 1 }}</span>
                <input
                  v-model="checklist[index]"
                  :aria-label="`Etapa ${index + 1} do checklist`"
                  placeholder="Ex.: Enviar primeira versão para revisão"
                  style="flex:1; min-width:0; box-sizing:border-box; border:1px solid #26263a; background:#0e0e14; border-radius:8px; padding:9px 10px; font-size:12px; color:#f5f4fb; outline:none;"
                  @keydown.enter.prevent="addChecklistItem"
                />
                <button type="button" :aria-label="`Remover etapa ${index + 1}`" @click="removeChecklistItem(index)" style="display:grid; place-items:center; width:30px; height:30px; flex:none; border:1px solid #26263a; border-radius:8px; background:#0e0e14; color:#77758d; cursor:pointer;">
                  <i class="fi fi-sr-cross-small" aria-hidden="true"></i>
                </button>
              </div>
            </div>
            <button type="button" @click="addChecklistItem" style="display:inline-flex; align-items:center; gap:5px; margin-top:8px; padding:6px 9px; border:1px solid #292837; border-radius:7px; background:#101017; color:#aaa7bc; font-size:10.5px; font-weight:700; cursor:pointer;">
              <i class="fi fi-sr-plus-small" aria-hidden="true"></i>Adicionar etapa
            </button>
          </div>
          <div v-if="form.kind === 'group'">
            <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:8px;">Quem vai fazer <span style="color:#ff8f98;">*</span></div>
            <GroupPicker v-model="form.participants" :people="people" :roles="roles" />
          </div>
          <div v-else>
            <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Cargo <span style="color:#ff8f98;">*</span></div>
            <RoleSelectButtons :roles="roles" :model-value="form.role" @update:model-value="onRoleChange" />
          </div>

          <AssigneeSelect v-if="form.kind === 'solo'" v-model="form.assignee" :options="assigneeOptions" />

          <div>
            <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Data de entrega (Prazo)</div>
            <DueDateField v-model="form.due_date" />
          </div>

          <div>
            <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Prioridade</div>
            <PrioritySelectButtons v-model="form.priority" />
          </div>

          <div>
            <div style="font-size:12px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Depende de <span style="font-weight:500; color:#77758d;">(opcional)</span></div>
            <CustomSelect v-model="form.depends_on" :options="dependencyOptions" width="100%" label="Depende de" />
            <div style="margin-top:5px; font-size:11px; color:#77758d;">A tarefa só poderá ser iniciada depois que essa for concluída.</div>
          </div>
        </div>

        <div v-if="formError" style="margin-top:14px; padding:10px 12px; background:rgba(224,79,95,.14); border:1px solid rgba(224,79,95,.35); border-radius:9px; color:#ff8f98; font-size:12px; font-weight:600;">
          {{ formError }}
        </div>

        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:22px;">
          <button @click="goBack" style="border:1px solid #26263a; background:#0e0e14; border-radius:9px; padding:10px 16px; font-size:12.5px; font-weight:700; color:#c7c5dc; cursor:pointer;">Cancelar</button>
          <button @click="submit" :disabled="submitting" style="border:none; background:#7c6fff; color:#0a0a10; border-radius:9px; padding:10px 18px; font-size:12.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:6px;">
            <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
            <i v-else class="fi fi-sr-plus-small" aria-hidden="true"></i>{{ submitting ? 'Atribuindo…' : 'Atribuir Tarefa' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kind-toggle { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; }
.kind-toggle button { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px; border: 1px solid #26263a; background: #0e0e14; color: #9a97b8; text-align: left; cursor: pointer; transition: border-color .12s ease, background-color .12s ease; }
.kind-toggle button i { font-size: 15px; }
.kind-toggle button span { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.kind-toggle strong { font-size: 12.5px; color: #c7c5dc; }
.kind-toggle small { font-size: 10.5px; color: #706e82; }
.kind-toggle button:hover { border-color: #3a3a55; }
.kind-toggle button:focus-visible { outline: 2px solid #7c6fff; outline-offset: 1px; }
.kind-toggle button.active { border-color: #7c6fff; background: rgba(124, 111, 255, .14); }
.kind-toggle button.active strong { color: #f5f4fb; }
.kind-toggle button.active i { color: #b3aaff; }
@media (max-width: 480px) { .kind-toggle { grid-template-columns: 1fr; } }
</style>
