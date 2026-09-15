<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../auth'
import { gsap, reduceMotion } from '../motion'

const router = useRouter()
const isAdmin = computed(() => !!auth.state.person?.is_admin)


function go(name) {
  router.push({ name })
}

const SCENES = [
  {
    title: 'Descreva a demanda',
    text: 'Dê um título claro, escreva o que precisa ser entregue e defina o prazo.',
    icon: 'fi-sr-list-check',
  },
  {
    title: 'Escolha cargo e responsável',
    text: 'O cargo filtra as pessoas certas e a carga atual ajuda você a distribuir melhor.',
    icon: 'fi-sr-user-add',
  },
  {
    title: 'Acompanhe no quadro',
    text: 'A tarefa nasce como pendente e avança pelo fluxo até a conclusão.',
    icon: 'fi-sr-table-list',
  },
  {
    title: 'Decida com o dashboard',
    text: 'Veja atrasos, prioridades e sobrecarga antes de atribuir a próxima demanda.',
    icon: 'fi-sr-chart-simple',
  },
]

const ADMIN_STEPS = [
  {
    number: '01',
    route: 'team',
    icon: 'fi-sr-users',
    title: 'Monte a equipe',
    text: 'Cadastre pessoas, seus cargos e senhas. Isso define quem pode receber cada tipo de tarefa.',
    action: 'Gerenciar equipe',
  },
  {
    number: '02',
    route: 'new-task',
    icon: 'fi-sr-plus',
    title: 'Crie uma demanda',
    text: 'Informe escopo, cargo, responsável, prazo e prioridade. O atalho N abre essa tela.',
    action: 'Atribuir tarefa',
    featured: true,
  },
  {
    number: '03',
    route: 'board',
    icon: 'fi-sr-table-list',
    title: 'Acompanhe o fluxo',
    text: 'Use tabela para uma visão completa ou cards para mover tarefas entre os status.',
    action: 'Abrir o quadro',
  },
  {
    number: '04',
    route: 'dashboard',
    icon: 'fi-sr-chart-simple',
    title: 'Cuide da capacidade',
    text: 'Confira atrasos, prioridades e carga por pessoa antes de distribuir mais trabalho.',
    action: 'Ver indicadores',
  },
]

const activeScene = ref(0)
const playing = ref(!reduceMotion)
const heroEl = ref(null)
const stepsEl = ref(null)
let sceneTimer = null

function clearSceneTimer() {
  if (sceneTimer) window.clearTimeout(sceneTimer)
  sceneTimer = null
}

function scheduleScene() {
  clearSceneTimer()
  if (!playing.value) return
  sceneTimer = window.setTimeout(() => {
    if (activeScene.value >= SCENES.length - 1) {
      playing.value = false
      return
    }
    activeScene.value += 1
    scheduleScene()
  }, 4200)
}

function selectScene(index) {
  activeScene.value = index
  scheduleScene()
}

function togglePlayback() {
  if (playing.value) {
    playing.value = false
    clearSceneTimer()
    return
  }
  if (activeScene.value >= SCENES.length - 1) activeScene.value = 0
  playing.value = true
  scheduleScene()
}

function replay() {
  activeScene.value = 0
  playing.value = !reduceMotion
  scheduleScene()
}

function sceneEnter(el, done) {
  if (reduceMotion) return done()
  gsap.fromTo(
    el,
    { autoAlpha: 0, transform: 'translateY(8px) scale(0.98)' },
    { autoAlpha: 1, transform: 'translateY(0px) scale(1)', duration: 0.45, ease: 'power3.out', onComplete: done }
  )
}

function sceneLeave(el, done) {
  if (reduceMotion) return done()
  gsap.to(el, { autoAlpha: 0, transform: 'translateY(-5px) scale(0.99)', duration: 0.2, ease: 'power2.out', onComplete: done })
}

onMounted(async () => {
  scheduleScene()
  await nextTick()
  if (reduceMotion) return
  gsap.fromTo(heroEl.value, { y: 16, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.55, ease: 'power3.out', clearProps: 'transform,opacity,visibility' })
  const cards = stepsEl.value?.querySelectorAll('.admin-step')
  if (cards?.length) {
    gsap.fromTo(cards, { y: 12, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.42, stagger: 0.06, ease: 'power2.out', delay: 0.2, clearProps: 'transform,opacity,visibility' })
  }
})

onUnmounted(clearSceneTimer)
</script>

<template>
  <main class="home-page">
    <section ref="heroEl" class="home-hero">
      <div class="hero-copy">
        <span class="eyebrow">
          <i class="fi fi-sr-sparkles" aria-hidden="true"></i>
          {{ isAdmin ? 'Central do administrador' : 'Central do projeto' }}
        </span>
        <h1>
          Bem vindo <span>Shydevers</span>
        </h1>
        <p>
          Transforme cada demanda do jogo em um fluxo claro: defina o trabalho, escolha quem faz,
          acompanhe o prazo e enxergue onde o time precisa de atenção.
        </p>

        <div class="hero-actions">
          <button v-if="isAdmin" class="primary-button" type="button" @click="go('new-task')">
            <i class="fi fi-sr-plus" aria-hidden="true"></i>Atribuir uma tarefa
          </button>
          <button v-else class="primary-button" type="button" @click="go('board')">
            <i class="fi fi-sr-table-list" aria-hidden="true"></i>Abrir o quadro
          </button>
          <button v-if="auth.isLoggedIn" class="secondary-button" type="button" @click="go('dashboard')">
            Ver dashboard<i class="fi fi-sr-arrow-right" aria-hidden="true"></i>
          </button>
        </div>

        <div class="hero-features" aria-label="Recursos principais">
          <span><i class="fi fi-sr-check-circle" aria-hidden="true"></i>Cargo e responsável</span>
          <span><i class="fi fi-sr-calendar" aria-hidden="true"></i>Prazo e prioridade</span>
          <span><i class="fi fi-sr-clock" aria-hidden="true"></i>Histórico automático</span>
        </div>
      </div>

      <div class="explainer-card" aria-label="Demonstração animada de como o ShyDevs funciona">
        <header class="explainer-header">
          <div class="explainer-brand">
            <span class="brand-mark"><i class="fi fi-sr-clapperboard-play" aria-hidden="true"></i></span>
            <div><strong>Como funciona</strong><span>Guia visual · 4 passos</span></div>
          </div>
          <div class="player-controls">
            <button type="button" :aria-label="playing ? 'Pausar animação' : 'Reproduzir animação'" @click="togglePlayback">
              <i :class="`fi ${playing ? 'fi-sr-pause' : 'fi-sr-play'}`" aria-hidden="true"></i>
            </button>
            <button type="button" aria-label="Reiniciar animação" @click="replay">
              <i class="fi fi-sr-rotate-right" aria-hidden="true"></i>
            </button>
          </div>
        </header>

        <div class="motion-stage" :class="{ 'is-paused': !playing }">
          <div class="stage-glow" aria-hidden="true"></div>
          <Transition mode="out-in" :css="false" @enter="sceneEnter" @leave="sceneLeave">
            <div :key="activeScene" class="motion-scene">
              <div v-if="activeScene === 0" class="creation-scene">
                <div class="mock-topbar scene-item scene-delay-1">
                  <span class="mock-logo">S</span><span>Quadro de Tarefas</span>
                  <span class="mock-create"><i class="fi fi-sr-plus" aria-hidden="true"></i>Atribuir tarefa</span>
                </div>
                <div class="mock-modal scene-item scene-delay-2">
                  <div class="mock-modal-title"><span>Nova demanda</span><i class="fi fi-sr-list-check" aria-hidden="true"></i></div>
                  <label>Título da tarefa</label>
                  <div class="mock-input typing-field"><span>Finalizar sistema de combate</span><i></i></div>
                  <label>Descrição</label>
                  <div class="mock-textarea"><span>Implementar combos, bloqueio e feedback de dano.</span></div>
                  <div class="mock-form-row">
                    <div><label>Prazo</label><span class="mock-select">18 de Set.</span></div>
                    <div><label>Prioridade</label><span class="priority-high">Alta</span></div>
                  </div>
                </div>
                <span class="motion-caption scene-item scene-delay-3"><i class="fi fi-sr-check" aria-hidden="true"></i>Escopo claro antes de delegar</span>
              </div>

              <div v-else-if="activeScene === 1" class="assignment-scene">
                <div class="assignment-card scene-item scene-delay-1">
                  <div class="assignment-title"><span>Quem deve receber?</span><small>Etapa 2 de 2</small></div>
                  <div class="selection-group">
                    <label>Cargo necessário</label>
                    <div class="role-selection"><i class="fi fi-sr-code-simple" aria-hidden="true"></i><span><strong>Scripter</strong><small>3 pessoas disponíveis</small></span><i class="fi fi-sr-check-circle" aria-hidden="true"></i></div>
                  </div>
                  <div class="selection-group">
                    <label>Responsável</label>
                    <div class="person-options">
                      <div class="person-option selected scene-item scene-delay-2"><span class="mock-avatar">LS</span><span><strong>Lucas Silva</strong><small>2 tarefas abertas</small></span><i class="fi fi-sr-check" aria-hidden="true"></i></div>
                      <div class="person-option scene-item scene-delay-3"><span class="mock-avatar alt">BC</span><span><strong>Beatriz Costa</strong><small>5 tarefas abertas</small></span></div>
                    </div>
                  </div>
                </div>
                <div class="balance-callout scene-item scene-delay-4"><i class="fi fi-sr-bolt" aria-hidden="true"></i><span><strong>Boa distribuição</strong>Lucas está com a menor carga do cargo.</span></div>
              </div>

              <div v-else-if="activeScene === 2" class="board-scene">
                <div class="board-toolbar scene-item scene-delay-1"><span><i class="fi fi-sr-table-list" aria-hidden="true"></i>Visão em cards</span><small>3 tarefas no fluxo</small></div>
                <div class="kanban-columns">
                  <div class="kanban-column"><span>Pendente <small>1</small></span><div class="ghost-card"></div></div>
                  <div class="kanban-column active"><span>Em andamento <small>2</small></span></div>
                  <div class="kanban-column"><span>Concluída <small>0</small></span></div>
                </div>
                <div class="moving-task">
                  <small>SD-128</small>
                  <strong>Sistema de combate</strong>
                  <span><i class="fi fi-sr-code-simple" aria-hidden="true"></i>Scripter</span>
                  <div><i class="fi fi-sr-calendar" aria-hidden="true"></i>18 de Set.<b>Alta</b></div>
                </div>
                <div class="drag-pointer"><i class="fi fi-sr-mouse" aria-hidden="true"></i></div>
                <div class="status-toast"><i class="fi fi-sr-check-circle" aria-hidden="true"></i>Status atualizado</div>
              </div>

              <div v-else class="dashboard-scene">
                <div class="dashboard-scene-heading scene-item scene-delay-1"><span><small>Visão geral</small><strong>Saúde da sprint</strong></span><span class="live-chip"><i></i>Ao vivo</span></div>
                <div class="mini-metrics">
                  <div class="mini-metric scene-item scene-delay-1"><i class="fi fi-sr-list-check"></i><span><small>Total</small><strong>18</strong></span></div>
                  <div class="mini-metric purple scene-item scene-delay-2"><i class="fi fi-sr-time-oclock"></i><span><small>Em andamento</small><strong>8</strong></span></div>
                  <div class="mini-metric red scene-item scene-delay-3"><i class="fi fi-sr-flag"></i><span><small>Atrasadas</small><strong>2</strong></span></div>
                </div>
                <div class="dashboard-bottom scene-item scene-delay-3">
                  <div class="mini-chart">
                    <div class="chart-title"><span>Carga da equipe</span><small>Esta semana</small></div>
                    <div class="chart-bars">
                      <span style="--bar:52%"></span><span style="--bar:76%"></span><span style="--bar:44%"></span><span style="--bar:88%"></span><span style="--bar:64%"></span>
                    </div>
                  </div>
                  <div class="mini-alert"><i class="fi fi-sr-triangle-warning" aria-hidden="true"></i><span><strong>2 itens críticos</strong><small>Confira antes de delegar</small></span></div>
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <footer class="explainer-footer">
          <div class="scene-tabs" role="tablist" aria-label="Etapas da demonstração">
            <button
              v-for="(scene, index) in SCENES"
              :key="scene.title"
              type="button"
              role="tab"
              :aria-selected="activeScene === index"
              :class="{ active: activeScene === index, complete: activeScene > index }"
              @click="selectScene(index)"
            >
              <span>{{ index + 1 }}</span>{{ scene.title }}
            </button>
          </div>
          <div class="scene-copy" aria-live="polite">
            <span><i :class="`fi ${SCENES[activeScene].icon}`" aria-hidden="true"></i>Passo {{ activeScene + 1 }}</span>
            <div><strong>{{ SCENES[activeScene].title }}</strong><p>{{ SCENES[activeScene].text }}</p></div>
          </div>
        </footer>
      </div>
    </section>

    <section v-if="isAdmin" class="admin-guide">
      <header class="section-heading">
        <div>
          <span class="section-kicker">Seu caminho mais curto</span>
          <h2>Comece por aqui, admin</h2>
        </div>
        <p>Quatro ações organizam o projeto inteiro. Siga a ordem na primeira configuração; depois, use cada área quando precisar.</p>
      </header>

      <div ref="stepsEl" class="admin-steps">
        <button
          v-for="step in ADMIN_STEPS"
          :key="step.number"
          type="button"
          class="admin-step"
          :class="{ featured: step.featured }"
          @click="go(step.route)"
        >
          <span class="step-number">{{ step.number }}</span>
          <span class="step-icon"><i :class="`fi ${step.icon}`" aria-hidden="true"></i></span>
          <strong>{{ step.title }}</strong>
          <p>{{ step.text }}</p>
          <span class="step-action">{{ step.action }}<i class="fi fi-sr-arrow-right" aria-hidden="true"></i></span>
        </button>
      </div>

      <aside class="admin-tip">
        <span class="tip-icon"><i class="fi fi-sr-bolt" aria-hidden="true"></i></span>
        <div>
          <span>Dica essencial</span>
          <strong>Escolha o cargo antes do responsável.</strong>
          <p>O sistema usa o cargo para mostrar apenas as pessoas preparadas para aquele trabalho e compara a carga entre elas.</p>
        </div>
        <button type="button" @click="go('new-task')">Testar agora<i class="fi fi-sr-arrow-right" aria-hidden="true"></i></button>
      </aside>
    </section>

    <section v-else class="member-guide">
      <header class="section-heading">
        <div>
          <span class="section-kicker">Sua rotina no projeto</span>
          <h2>Encontre, execute e registre</h2>
        </div>
        <p>Entre com sua conta para filtrar suas tarefas, atualizar o andamento e anexar provas da entrega.</p>
      </header>
      <div class="member-actions">
        <button type="button" @click="go('board')"><i class="fi fi-sr-user" aria-hidden="true"></i><span><strong>Veja suas tarefas</strong><small>Use o filtro “Minhas tarefas” no quadro.</small></span><i class="fi fi-sr-arrow-right" aria-hidden="true"></i></button>
        <button type="button" @click="go('board')"><i class="fi fi-sr-check-circle" aria-hidden="true"></i><span><strong>Atualize o andamento</strong><small>Abra uma tarefa para registrar progresso e entrega.</small></span><i class="fi fi-sr-arrow-right" aria-hidden="true"></i></button>
      </div>
    </section>

    <section class="home-cta">
      <div><span>Pronto para organizar a próxima entrega?</span><strong>{{ isAdmin ? 'Crie uma demanda clara em menos de um minuto.' : 'Veja agora o que está acontecendo no projeto.' }}</strong></div>
      <button type="button" @click="go(isAdmin ? 'new-task' : 'board')">
        {{ isAdmin ? 'Atribuir tarefa' : 'Abrir o quadro' }}<i class="fi fi-sr-arrow-right" aria-hidden="true"></i>
      </button>
    </section>
  </main>
</template>

<style scoped>
.home-page {
  --panel: #14141d;
  --panel-soft: #101017;
  --border: #242432;
  --muted: #918eaa;
  --text: #f5f4fb;
  --purple: #7c6fff;
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
  padding: 30px 26px 42px;
  color: var(--text);
}

button { font: inherit; }
.home-hero { display: grid; grid-template-columns: minmax(0, 1fr); gap: 32px; padding-block: 18px 36px; }
.hero-copy { min-width: 0; }
.eyebrow,
.section-kicker { display: inline-flex; align-items: center; gap: 7px; color: #aaa2ff; font-size: 10px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.eyebrow { padding: 6px 9px; border: 1px solid rgba(124,111,255,.24); border-radius: 999px; background: rgba(124,111,255,.09); }
.hero-copy h1 { max-width: 560px; margin: 20px 0 16px; color: var(--text); font-size: clamp(36px, 4.2vw, 58px); font-weight: 850; line-height: .98; letter-spacing: -.055em; text-wrap: balance; }
.hero-copy h1 span { display: block; color: #918cae; }
.hero-copy > p { max-width: 540px; margin: 0; color: #aaa7bd; font-size: 14px; line-height: 1.7; }
.hero-actions { display: flex; gap: 10px; margin-top: 24px; flex-wrap: wrap; }
.primary-button,
.secondary-button,
.home-cta button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 42px; padding: 0 16px; border-radius: 10px; font-size: 12.5px; font-weight: 800; cursor: pointer; transition-property: transform, background-color, border-color, color; transition-duration: 150ms; }
.primary-button { border: 1px solid var(--purple); background: var(--purple); color: #0a0a10; box-shadow: 0 10px 28px rgba(124,111,255,.18); }
.secondary-button { border: 1px solid #2a2938; background: #14141d; color: #c9c6dc; }
.hero-features { display: flex; gap: 15px; margin-top: 24px; flex-wrap: wrap; color: #7f7c92; font-size: 10px; }
.hero-features span { display: inline-flex; align-items: center; gap: 5px; }
.hero-features i { color: #56d79a; font-size: 9px; }

.explainer-card { min-width: 0; overflow: hidden; border: 1px solid #29283a; border-radius: 16px; background: #121219; box-shadow: 0 28px 70px rgba(0,0,0,.3), 0 0 60px rgba(124,111,255,.055); }
.explainer-header { display: flex; align-items: center; justify-content: space-between; min-height: 58px; padding-inline: 15px; border-bottom: 1px solid #232330; background: rgba(255,255,255,.012); }
.explainer-brand { display: flex; align-items: center; gap: 9px; }
.brand-mark { display: grid; place-items: center; width: 30px; height: 30px; border: 1px solid rgba(124,111,255,.25); border-radius: 8px; background: rgba(124,111,255,.12); color: #b8b1ff; font-size: 12px; }
.brand-mark i { display: block; line-height: 1; transform: translateY(1px); }
.explainer-brand strong,
.explainer-brand div > span { display: block; }
.explainer-brand strong { font-size: 11.5px; }
.explainer-brand div span { margin-top: 2px; color: #706e82; font-size: 8.5px; }
.player-controls { display: flex; gap: 5px; }
.player-controls button { display: grid; place-items: center; width: 29px; height: 29px; border: 1px solid #292837; border-radius: 8px; background: #0e0e14; color: #89869e; font-size: 9px; cursor: pointer; transition-property: border-color, color, background-color; transition-duration: 150ms; }
.player-controls button:hover { border-color: #413e5b; background: #171620; color: #c3bcff; }

.motion-stage { position: relative; height: 322px; overflow: hidden; background-color: #0b0b10; background-image: linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px); background-size: 24px 24px; }
.motion-stage.is-paused .scene-item,
.motion-stage.is-paused .typing-field i,
.motion-stage.is-paused .moving-task,
.motion-stage.is-paused .drag-pointer,
.motion-stage.is-paused .status-toast,
.motion-stage.is-paused .chart-bars span { animation-play-state: paused; }
.stage-glow { position: absolute; inset: -35% 5% auto; height: 210px; border-radius: 50%; background: rgba(124,111,255,.11); filter: blur(70px); pointer-events: none; }
.motion-scene { position: absolute; inset: 0; padding: 20px; }
.scene-item { animation: scene-item-in .6s var(--ease-out) both; }
.scene-delay-1 { animation-delay: .1s; }
.scene-delay-2 { animation-delay: .45s; }
.scene-delay-3 { animation-delay: .85s; }
.scene-delay-4 { animation-delay: 1.25s; }

.mock-topbar { display: flex; align-items: center; gap: 7px; height: 35px; padding: 0 9px; border: 1px solid #242330; border-radius: 9px; background: #121219; color: #aaa7bd; font-size: 8.5px; }
.mock-logo { display: grid; place-items: center; width: 17px; height: 17px; border-radius: 5px; background: #7c6fff; color: #0a0a10; font-size: 8px; font-weight: 900; }
.mock-create { display: inline-flex; align-items: center; gap: 4px; margin-inline-start: auto; padding: 5px 7px; border-radius: 6px; background: #7c6fff; color: #0a0a10; font-size: 7.5px; font-weight: 800; }
.mock-modal { position: relative; width: 72%; margin: 13px auto 0; padding: 13px; border: 1px solid #2b2a3b; border-radius: 11px; background: #15151e; box-shadow: 0 18px 34px rgba(0,0,0,.28); }
.mock-modal-title { display: flex; justify-content: space-between; margin-bottom: 11px; color: #eeecf6; font-size: 10px; font-weight: 800; }
.mock-modal-title i { color: #8b80ff; }
.mock-modal label,
.selection-group > label { display: block; margin-bottom: 4px; color: #747187; font-size: 6.5px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }
.mock-input,
.mock-textarea,
.mock-select { border: 1px solid #292837; border-radius: 6px; background: #0f0f15; color: #c8c5d8; font-size: 8px; }
.mock-input { display: flex; align-items: center; min-height: 26px; padding: 0 8px; }
.typing-field span { overflow: hidden; white-space: nowrap; animation: type-text 1.25s steps(27) .75s both; }
.typing-field i { width: 1px; height: 11px; margin-inline-start: 2px; background: #a79fff; animation: caret-blink .65s linear .75s infinite; }
.mock-textarea { min-height: 34px; margin-bottom: 9px; padding: 7px 8px; line-height: 1.45; }
.mock-form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.mock-select,
.priority-high { display: flex; align-items: center; min-height: 24px; padding-inline: 7px; }
.priority-high { border: 1px solid rgba(232,93,106,.2); border-radius: 6px; background: rgba(232,93,106,.1); color: #ff929b; font-size: 7.5px; font-weight: 800; }
.motion-caption { position: absolute; inset-inline-end: 20px; bottom: 17px; display: inline-flex; align-items: center; gap: 5px; padding: 6px 8px; border: 1px solid rgba(63,207,142,.2); border-radius: 7px; background: rgba(63,207,142,.08); color: #73dda7; font-size: 7.5px; font-weight: 700; }

.assignment-card { width: 78%; margin: 4px auto 0; padding: 15px; border: 1px solid #292837; border-radius: 12px; background: #14141d; box-shadow: 0 18px 38px rgba(0,0,0,.24); }
.assignment-title { display: flex; justify-content: space-between; margin-bottom: 14px; }
.assignment-title span { font-size: 11px; font-weight: 800; }
.assignment-title small { color: #77748c; font-size: 7.5px; }
.selection-group + .selection-group { margin-top: 11px; }
.role-selection,
.person-option { display: flex; align-items: center; gap: 8px; border: 1px solid #292837; border-radius: 8px; background: #0f0f15; }
.role-selection { min-height: 42px; padding: 0 10px; color: #a9a1ff; }
.role-selection > i:last-child { margin-inline-start: auto; color: #63dda0; }
.role-selection span,
.person-option > span:nth-child(2) { flex: 1; }
.role-selection strong,
.role-selection small,
.person-option strong,
.person-option small { display: block; }
.role-selection strong,
.person-option strong { color: #d9d6e8; font-size: 8.5px; }
.role-selection small,
.person-option small { margin-top: 2px; color: #716e83; font-size: 7px; }
.person-options { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
.person-option { min-height: 48px; padding: 0 8px; }
.person-option.selected { border-color: rgba(124,111,255,.55); background: rgba(124,111,255,.08); }
.person-option > i { color: #a99fff; font-size: 8px; }
.mock-avatar { display: grid; place-items: center; width: 25px; height: 25px; flex: none; border-radius: 50%; background: #786cf0; color: #0b0b10; font-size: 7px; font-weight: 900; }
.mock-avatar.alt { background: #cb9a54; }
.balance-callout { display: flex; align-items: center; gap: 8px; width: 66%; margin: 10px auto 0; padding: 8px 10px; border: 1px solid rgba(63,207,142,.18); border-radius: 8px; background: rgba(63,207,142,.07); color: #67d89f; }
.balance-callout > i { font-size: 9px; }
.balance-callout span { color: #89869d; font-size: 7.5px; }
.balance-callout strong { margin-inline-end: 4px; color: #6fdfa5; }

.board-toolbar { display: flex; justify-content: space-between; align-items: center; height: 34px; padding-inline: 10px; border: 1px solid #242330; border-radius: 8px; background: #121219; color: #c4c1d4; font-size: 8px; font-weight: 800; }
.board-toolbar span { display: inline-flex; align-items: center; gap: 5px; }
.board-toolbar i { color: #9d94ff; }
.board-toolbar small { color: #6e6b7e; font-size: 7px; font-weight: 600; }
.kanban-columns { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; height: 232px; margin-top: 9px; }
.kanban-column { position: relative; padding: 10px; border: 1px solid #22212e; border-radius: 9px; background: rgba(18,18,25,.82); }
.kanban-column.active { border-color: rgba(124,111,255,.28); background: rgba(124,111,255,.035); }
.kanban-column > span { color: #9a97aa; font-size: 7.5px; font-weight: 800; }
.kanban-column > span small { color: #656275; }
.ghost-card { height: 88px; margin-top: 10px; border: 1px dashed #2c2b3a; border-radius: 8px; }
.moving-task { position: absolute; inset-inline-start: 30px; top: 84px; z-index: 2; width: calc((100% - 76px) / 3); padding: 10px; border: 1px solid rgba(124,111,255,.48); border-radius: 8px; background: #181721; box-shadow: 0 14px 26px rgba(0,0,0,.32); animation: move-task 2.2s var(--ease-out) .65s both; }
.moving-task small,
.moving-task strong,
.moving-task > span { display: block; }
.moving-task small { color: #716d86; font-size: 6.5px; }
.moving-task strong { margin: 4px 0 9px; color: #e5e2ee; font-size: 8.5px; }
.moving-task > span { color: #a49bf8; font-size: 7px; }
.moving-task > span i { margin-inline-end: 4px; }
.moving-task div { display: flex; align-items: center; gap: 4px; margin-top: 9px; color: #7f7c91; font-size: 6.5px; }
.moving-task b { margin-inline-start: auto; color: #ff8f98; font-size: 6.5px; }
.drag-pointer { position: absolute; inset-inline-start: 31%; top: 168px; z-index: 3; color: #f5f4fb; filter: drop-shadow(0 3px 5px #000); animation: move-pointer 2.2s var(--ease-out) .65s both; }
.status-toast { position: absolute; inset-inline-end: 24px; bottom: 15px; display: flex; align-items: center; gap: 5px; padding: 7px 9px; border: 1px solid rgba(63,207,142,.22); border-radius: 7px; background: #13231c; color: #70dfa5; font-size: 7.5px; font-weight: 800; animation: toast-in .5s var(--ease-out) 2.55s both; }

.dashboard-scene-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.dashboard-scene-heading small,
.dashboard-scene-heading strong { display: block; }
.dashboard-scene-heading small { color: #77748b; font-size: 7px; text-transform: uppercase; letter-spacing: .08em; }
.dashboard-scene-heading strong { margin-top: 4px; font-size: 12px; }
.live-chip { display: inline-flex; align-items: center; gap: 5px; padding: 5px 7px; border: 1px solid rgba(63,207,142,.18); border-radius: 999px; color: #73dca7; font-size: 7px; }
.live-chip i { width: 5px; height: 5px; border-radius: 50%; background: #3fcf8e; box-shadow: 0 0 8px #3fcf8e; }
.mini-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.mini-metric { display: flex; align-items: center; gap: 9px; min-height: 55px; padding: 0 10px; border: 1px solid #242330; border-radius: 9px; background: #121219; }
.mini-metric > i { display: grid; place-items: center; width: 27px; height: 27px; border-radius: 8px; background: rgba(154,154,176,.09); color: #aaa7bb; font-size: 9px; }
.mini-metric.purple > i { background: rgba(124,111,255,.11); color: #aaa1ff; }
.mini-metric.red > i { background: rgba(232,93,106,.1); color: #ff8f98; }
.mini-metric small,
.mini-metric strong { display: block; }
.mini-metric small { color: #767386; font-size: 6.5px; }
.mini-metric strong { margin-top: 3px; font-size: 13px; }
.dashboard-bottom { display: grid; grid-template-columns: 1.3fr .7fr; gap: 8px; margin-top: 9px; }
.mini-chart,
.mini-alert { min-height: 135px; border: 1px solid #242330; border-radius: 9px; background: #121219; }
.mini-chart { padding: 11px; }
.chart-title { display: flex; justify-content: space-between; color: #b9b6ca; font-size: 8px; font-weight: 800; }
.chart-title small { color: #6f6c80; font-size: 6.5px; font-weight: 600; }
.chart-bars { display: flex; align-items: flex-end; gap: 8px; height: 86px; padding: 10px 5px 0; border-bottom: 1px solid #272633; }
.chart-bars span { flex: 1; height: var(--bar); border-radius: 4px 4px 1px 1px; background: linear-gradient(#8d83ff, #5d52d1); transform-origin: bottom; animation: grow-bar .8s var(--ease-out) 1s both; }
.mini-alert { display: grid; place-content: center; justify-items: center; padding: 12px; text-align: center; }
.mini-alert > i { display: grid; place-items: center; width: 32px; height: 32px; margin-bottom: 8px; border-radius: 9px; background: rgba(232,93,106,.1); color: #ff8f98; }
.mini-alert strong,
.mini-alert small { display: block; }
.mini-alert strong { font-size: 8.5px; }
.mini-alert small { margin-top: 4px; color: #777487; font-size: 6.5px; }

.explainer-footer { padding: 22px 24px 24px; border-top: 1px solid #232330; }
.scene-tabs { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.scene-tabs button { display: flex; align-items: center; gap: 10px; min-width: 0; min-height: 48px; padding: 10px 12px; border: 1px solid #302d40; border-radius: 9px; background: #17161f; color: #c5bfd6; font-size: 14px; line-height: 1.4; font-weight: 700; text-align: start; cursor: pointer; transition-property: color, background-color, border-color; transition-duration: 150ms; }
.scene-tabs button span { display: grid; place-items: center; width: 26px; height: 26px; flex: none; border: 1px solid #484258; border-radius: 7px; color: #d4cde3; font-size: 12px; }
.scene-tabs button.active { border-color: #786bb9; background: rgba(124,111,255,.16); color: #ece8ff; }
.scene-tabs button:focus-visible { outline: 2px solid #c4baff; outline-offset: 3px; }
.scene-tabs button.active span { border-color: #7c6fff; background: #7c6fff; color: #0a0a10; }
.scene-tabs button.complete span { border-color: rgba(63,207,142,.24); color: #5bdc9b; }
.scene-copy { display: grid; grid-template-columns: 90px minmax(0, 1fr); gap: 18px; align-items: start; min-height: 76px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #302d40; }
.scene-copy > span { display: inline-flex; align-items: center; gap: 6px; padding-top: 4px; color: #bcb1ff; font-size: 12px; font-weight: 800; text-transform: uppercase; }
.scene-copy strong { display: block; color: #f0edf8; font-size: 18px; line-height: 1.4; }
.scene-copy p { margin: 6px 0 0; color: #bfb8d0; font-size: 15px; line-height: 1.65; }

.admin-guide,
.member-guide { padding-block: 52px; }
.section-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 30px; margin-bottom: 22px; }
.section-heading h2 { margin: 7px 0 0; font-size: clamp(24px, 3vw, 34px); line-height: 1; letter-spacing: -.035em; }
.section-heading > p { max-width: 480px; margin: 0; color: #8e8ba2; font-size: 12px; line-height: 1.6; }
.section-heading.compact { margin-bottom: 20px; }
.admin-steps { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.admin-step { position: relative; display: flex; flex-direction: column; align-items: flex-start; min-width: 0; min-height: 245px; padding: 15px; overflow: hidden; border: 1px solid #242432; border-radius: 13px; background: #14141d; color: inherit; text-align: start; cursor: pointer; transition-property: transform, border-color, background-color; transition-duration: 150ms; }
.admin-step.featured { border-color: rgba(124,111,255,.38); background: linear-gradient(145deg, rgba(124,111,255,.11), rgba(20,20,29,.96) 55%); }
.step-number { position: absolute; inset-inline-end: 13px; top: 12px; color: #343244; font-size: 24px; font-weight: 900; letter-spacing: -.05em; }
.admin-step.featured .step-number { color: rgba(124,111,255,.28); }
.step-icon { display: grid; place-items: center; width: 35px; height: 35px; margin-bottom: 24px; border: 1px solid #2d2c3c; border-radius: 10px; background: #101017; color: #aaa1ff; font-size: 13px; }
.admin-step.featured .step-icon { border-color: rgba(124,111,255,.3); background: rgba(124,111,255,.13); }
.admin-step > strong { font-size: 13px; }
.admin-step > p { margin: 8px 0 18px; color: #858297; font-size: 10.5px; line-height: 1.55; }
.step-action { display: inline-flex; align-items: center; gap: 6px; margin-top: auto; color: #9e96fa; font-size: 10px; font-weight: 800; }
.step-action i { font-size: 8px; }
.admin-tip { display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; gap: 13px; align-items: center; margin-top: 12px; padding: 14px; border: 1px solid rgba(124,111,255,.27); border-radius: 12px; background: rgba(124,111,255,.07); }
.tip-icon { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 10px; background: rgba(124,111,255,.13); color: #b1a8ff; }
.admin-tip div > span { display: block; margin-bottom: 3px; color: #948bea; font-size: 8px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.admin-tip strong { font-size: 11.5px; }
.admin-tip p { margin: 3px 0 0; color: #89859e; font-size: 9.5px; line-height: 1.45; }
.admin-tip button { display: inline-flex; align-items: center; gap: 6px; min-height: 34px; padding: 0 10px; border: 1px solid rgba(124,111,255,.27); border-radius: 8px; background: #111018; color: #aaa2ff; font-size: 9.5px; font-weight: 800; cursor: pointer; }

.member-actions { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; }
.member-actions button { display: grid; grid-template-columns: 36px 1fr auto; gap: 12px; align-items: center; padding: 15px; border: 1px solid #242432; border-radius: 12px; background: #14141d; color: #aaa1ff; text-align: start; cursor: pointer; }
.member-actions button > i:first-child { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px; background: rgba(124,111,255,.11); }
.member-actions strong,
.member-actions small { display: block; }
.member-actions strong { color: #dedbea; font-size: 12px; }
.member-actions small { margin-top: 4px; color: #807d92; font-size: 10px; }

.home-cta { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 22px; border: 1px solid rgba(124,111,255,.26); border-radius: 14px; background: radial-gradient(circle at 18% 0, rgba(124,111,255,.16), transparent 40%), #14141d; }
.home-cta span,
.home-cta strong { display: block; }
.home-cta span { color: #928cae; font-size: 9px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.home-cta strong { margin-top: 5px; font-size: 16px; }
.home-cta button { flex: none; border: 1px solid var(--purple); background: var(--purple); color: #0a0a10; }

@media (hover: hover) and (pointer: fine) {
  .primary-button:hover,
  .home-cta button:hover { transform: translateY(-1px); background: #8b80ff; }
  .secondary-button:hover { transform: translateY(-1px); border-color: #414052; background: #191922; color: #e0ddec; }
  .admin-step:hover { transform: translateY(-2px); border-color: #3a384d; background-color: #171720; }
  .admin-step.featured:hover { border-color: rgba(124,111,255,.55); }
}


@keyframes scene-item-in {
  from { opacity: 0; transform: translateY(8px) scale(.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes type-text {
  from { opacity: .4; clip-path: inset(0 100% 0 0); }
  to { opacity: 1; clip-path: inset(0 0 0 0); }
}
@keyframes caret-blink { 50% { opacity: 0; } }
@keyframes move-task {
  0%, 24% { transform: translateX(0) rotate(0); }
  48% { transform: translateX(54%) translateY(-7px) rotate(1deg); }
  100% { transform: translateX(calc(100% + 8px)) translateY(0) rotate(0); }
}
@keyframes move-pointer {
  0%, 24% { transform: translateX(0) translateY(0); }
  100% { transform: translateX(122px) translateY(-4px); }
}
@keyframes toast-in {
  from { opacity: 0; transform: translateY(8px) scale(.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes grow-bar {
  from { opacity: .4; transform: scaleY(.08); }
  to { opacity: 1; transform: scaleY(1); }
}


@media (max-width: 700px) {
  .home-page { padding-inline: 16px; }
  .hero-copy h1 { font-size: 38px; }
  .motion-stage { height: 322px; }
  .motion-scene { padding: 14px; }
  .mock-modal, .assignment-card { width: 95%; }
  .person-options { grid-template-columns: 1fr; }
  .person-option:last-child, .drag-pointer { display: none; }
  .moving-task { inset-inline-start: 24px; top: 78px; width: calc((100% - 62px) / 3); padding: 7px; }
  .dashboard-bottom { grid-template-columns: 1fr; }
  .mini-alert { display: none; }
  .explainer-footer { padding: 18px; }
  .scene-tabs { grid-template-columns: 1fr 1fr; }
  .scene-tabs button { font-size: 14px; min-height: 64px; }
  .scene-copy { grid-template-columns: 1fr; gap: 10px; }
  .section-heading { align-items: flex-start; flex-direction: column; gap: 10px; }
  .admin-steps, .member-actions { grid-template-columns: 1fr; }
  .admin-tip { grid-template-columns: 38px minmax(0, 1fr); }
  .admin-tip button { grid-column: 1 / -1; justify-content: center; }
  .home-cta { align-items: flex-start; flex-direction: column; }
  .home-cta button { width: 100%; }
}
@media (prefers-reduced-motion: reduce) {
  .scene-item,
  .typing-field span,
  .typing-field i,
  .moving-task,
  .status-toast,
  .chart-bars span { animation: none; }
  .drag-pointer { display: none; }
}

</style>
