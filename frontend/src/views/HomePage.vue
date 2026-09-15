<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { gsap, reduceMotion } from '../motion'
import { mascot } from '../mascotFace'

const router = useRouter()

function go(name) {
  router.push({ name })
}

// ---- shortcuts ----
const SHORTCUTS = [
  { name: 'board', icon: 'fi-sr-table-list', color: '#b3aaff', bg: 'rgba(124,111,255,.16)', title: 'Quadro de Tarefas', desc: 'Todas as demandas, filtros por cargo e status.' },
  { name: 'dashboard', icon: 'fi-sr-chart-simple', color: '#b3aaff', bg: 'rgba(124,111,255,.16)', title: 'Dashboard', desc: 'Status, prioridade, cargo e carga por pessoa.' },
  { name: 'history', icon: 'fi-sr-clock', color: '#b3aaff', bg: 'rgba(124,111,255,.16)', title: 'Histórico', desc: 'Log de tudo que mudou nas tarefas. Precisa estar logado.' },
  { name: 'new-task', icon: 'fi-sr-plus-small', color: '#0a0a10', bg: '#7c6fff', title: 'Atribuir Tarefa', desc: 'Criar e delegar uma demanda. Só admin.', highlight: true },
  { name: 'board', icon: 'fi-sr-user', color: '#6fe3a4', bg: 'rgba(63,207,142,.16)', title: 'Minhas tarefas', desc: 'Chip no quadro que filtra só o que é seu.' },
]

// ---- interactive tab preview ----
const TABS = [
  { key: 'board', label: 'Quadro', icon: 'fi-sr-table-list' },
  { key: 'dashboard', label: 'Dashboard', icon: 'fi-sr-chart-simple' },
  { key: 'history', label: 'Histórico', icon: 'fi-sr-clock' },
  { key: 'team', label: 'Equipe', icon: 'fi-sr-users' },
]
const activeTab = ref('board')

// ---- how-to steps ----
const STEPS = [
  { n: 1, title: 'Clique em Atribuir Tarefa', desc: 'Botão roxo no canto direito do topo, em qualquer aba. Atalho de teclado: N' },
  { n: 2, title: 'Título e descrição', desc: 'Título é obrigatório. Na descrição vai o escopo: referências, limite de polycount, o que conta como pronto.' },
  { n: 3, title: 'Escolha o cargo', desc: 'O cargo filtra quem pode receber a tarefa — só aparece quem tem esse cargo (ou um deles, se a pessoa tiver mais de um).' },
  { n: 4, title: 'Selecione o responsável', desc: 'A lista mostra quantas tarefas abertas cada pessoa já tem — use isso para não sobrecarregar ninguém.' },
  { n: 5, title: 'Prazo e prioridade', desc: 'Atalhos Hoje / Amanhã / Próxima semana. Prioridade Baixa, Média ou Alta. Passou do prazo, a tarefa vira Atrasada.' },
  { n: 6, title: 'Confirme', desc: 'A tarefa nasce como Pendente e já aparece no quadro para todo mundo. O histórico registra quem atribuiu.', highlight: true },
]

// ---- entrance ----
const heroEl = ref(null)
const shortcutsEl = ref(null)
onMounted(async () => {
  await nextTick()
  if (reduceMotion) return
  gsap.from(heroEl.value, { y: 16, autoAlpha: 0, duration: 0.5, ease: 'power3.out', clearProps: 'transform' })
  const cards = shortcutsEl.value?.querySelectorAll('.shortcut-card')
  if (cards?.length) {
    gsap.from(cards, { y: 12, autoAlpha: 0, duration: 0.4, stagger: 0.05, ease: 'power2.out', delay: 0.15, clearProps: 'transform' })
  }
})
</script>

<template>
  <div style="padding:28px 26px 60px; display:flex; flex-direction:column; gap:40px;">

    <!-- hero -->
    <div ref="heroEl" style="display:flex; align-items:flex-start; gap:24px; flex-wrap:wrap;">
      <div style="flex:1; min-width:320px;">
        <div style="display:flex; align-items:center; gap:8px; font-size:11.5px; font-weight:600; color:#8b899f; margin-bottom:12px;">
          <span style="width:6px; height:6px; border-radius:50%; background:#7c6fff;" aria-hidden="true"></span>ShyDevs · Studio de jogos Roblox
        </div>
        <h1 style="margin:0 0 10px; font-size:38px; line-height:1.08; font-weight:800; color:#f5f4fb; letter-spacing:-.03em; text-wrap:balance;">O quadro onde a studio combina o que vai ser feito.</h1>
        <p style="margin:0 0 20px; font-size:14px; line-height:1.6; color:#9a97b8; max-width:560px;">Cada demanda do jogo vira uma tarefa com cargo, responsável, prazo e prioridade. Esta página é o atalho para tudo: o quadro, os números do time e o passo a passo de como atribuir uma tarefa.</p>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <button type="button" @click="go('board')" style="display:inline-flex; align-items:center; gap:8px; background:#7c6fff; color:#0a0a10; border:none; border-radius:10px; padding:12px 18px; font-size:13px; font-weight:700; cursor:pointer;">
            <i class="fi fi-sr-table-list" aria-hidden="true"></i>Abrir o Quadro de Tarefas
          </button>
          <button type="button" @click="go('dashboard')" style="display:inline-flex; align-items:center; gap:8px; border:1px solid #26263a; background:#14141d; color:#c7c5dc; border-radius:10px; padding:12px 18px; font-size:13px; font-weight:700; cursor:pointer;">
            <i class="fi fi-sr-chart-simple" aria-hidden="true"></i>Ver o Dashboard
          </button>
        </div>
      </div>
      <img :src="mascot" alt="Mascote ShyDevs" style="width:132px; height:132px; flex:none; object-fit:contain; filter:drop-shadow(0 10px 24px rgba(124,111,255,.3));" />
    </div>

    <!-- shortcuts -->
    <div>
      <div style="font-size:10.5px; font-weight:700; letter-spacing:.09em; color:#8b899f; margin-bottom:12px; font-family:'JetBrains Mono', monospace;">ATALHOS</div>
      <div ref="shortcutsEl" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
        <button v-for="(s, i) in SHORTCUTS" :key="i" type="button" @click="go(s.name)" class="shortcut-card"
          :style="{ textAlign: 'left', background: s.highlight ? 'rgba(124,111,255,.10)' : '#14141d', border: `1px solid ${s.highlight ? 'rgba(124,111,255,.35)' : '#22222f'}`, borderRadius: '12px', padding: '14px', cursor: 'pointer', font: 'inherit' }">
          <div :style="{ width: '30px', height: '30px', borderRadius: '9px', background: s.bg, color: s.color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', marginBottom: '10px' }">
            <i :class="`fi ${s.icon}`" aria-hidden="true"></i>
          </div>
          <div style="font-size:13px; font-weight:700; color:#f5f4fb;">{{ s.title }}</div>
          <div :style="{ fontSize: '11.5px', lineHeight: 1.5, color: s.highlight ? '#b0abd6' : '#8b899f', marginTop: '3px' }">{{ s.desc }}</div>
        </button>
      </div>
    </div>

    <!-- tab preview -->
    <div>
      <div style="font-size:10.5px; font-weight:700; letter-spacing:.09em; color:#8b899f; margin-bottom:6px; font-family:'JetBrains Mono', monospace;">AS ABAS DO TOPO</div>
      <div style="font-size:13px; color:#9a97b8; margin-bottom:14px;">Clique numa aba para ver o que ela mostra.</div>

      <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:14px;">
        <div style="display:inline-flex; flex-wrap:wrap; gap:7px; background:#0e0e14; border:1px solid #22222f; border-radius:10px; padding:4px; margin-bottom:16px;">
          <button v-for="t in TABS" :key="t.key" type="button" @click="activeTab = t.key"
            :style="{ display: 'inline-flex', alignItems: 'center', gap: '6px', border: 'none', borderRadius: '8px', padding: '8px 12px', fontSize: '12px', fontWeight: '700', cursor: 'pointer', background: activeTab === t.key ? 'rgba(124,111,255,.16)' : 'transparent', color: activeTab === t.key ? '#b3aaff' : '#8b899f' }">
            <i :class="`fi ${t.icon}`" aria-hidden="true"></i>{{ t.label }}
          </button>
        </div>

        <div v-if="activeTab === 'board'" style="display:flex; gap:18px; flex-wrap:wrap;">
          <div style="flex:1 1 280px; min-width:260px;">
            <div style="font-size:15px; font-weight:800; color:#f5f4fb; margin-bottom:6px;">Quadro de Tarefas</div>
            <p style="margin:0 0 12px; font-size:12.5px; line-height:1.6; color:#9a97b8;">A aba padrão. Lista todas as demandas do projeto com cargo, responsável, prazo, prioridade e status. Leitura é pública — qualquer pessoa vê o quadro mesmo sem entrar.</p>
            <div style="display:flex; flex-direction:column; gap:7px;">
              <div style="font-size:12px; color:#c7c5dc; display:flex; gap:8px;"><i class="fi fi-sr-filter" style="color:#b3aaff; margin-top:2px;" aria-hidden="true"></i>Chips de cargo em cima: Modelador, Scripter, Vfx Maker…</div>
              <div style="font-size:12px; color:#c7c5dc; display:flex; gap:8px;"><i class="fi fi-sr-search" style="color:#b3aaff; margin-top:2px;" aria-hidden="true"></i>Busca por título, cargo ou responsável — atalho <span style="font-family:'JetBrains Mono', monospace; background:#0e0e14; border:1px solid #26263a; border-radius:4px; padding:1px 5px;">/</span></div>
              <div style="font-size:12px; color:#c7c5dc; display:flex; gap:8px;"><i class="fi fi-sr-time-oclock" style="color:#b3aaff; margin-top:2px;" aria-hidden="true"></i>Filtros de status: Todas · Pendentes · Em andamento · Concluídas · Atrasadas</div>
            </div>
          </div>
          <div style="flex:1 1 380px; min-width:340px; background:#101017; border:1px solid #22222f; border-radius:10px; overflow:hidden;">
            <div style="display:grid; grid-template-columns:minmax(0,1fr) 104px 118px 86px 104px; gap:8px; padding:9px 12px; background:#0e0e14; border-bottom:1px solid #1f1f2b; font-size:9.5px; font-weight:700; letter-spacing:.06em; color:#8b899f;">
              <div>TAREFA</div><div>CARGO</div><div>RESPONSÁVEL</div><div>PRAZO</div><div>STATUS</div>
            </div>
            <div style="display:grid; grid-template-columns:minmax(0,1fr) 104px 118px 86px 104px; gap:8px; padding:10px 12px; border-bottom:1px solid #1a1a25; align-items:center;">
              <div style="min-width:0;"><span style="font-family:'JetBrains Mono', monospace; font-size:9.5px; color:#8f8da8;">SD-104</span> <span style="font-size:12px; font-weight:700; color:#f5f4fb;">Lobby v2 — props</span></div>
              <div><span style="display:inline-flex; align-items:center; gap:4px; border-radius:6px; padding:3px 7px; font-size:10px; font-weight:700; background:color-mix(in oklab, oklch(0.62 0.15 45) 20%, #14141d); color:color-mix(in oklab, oklch(0.62 0.15 45) 75%, #fff);"><i class="fi fi-sr-model-cube" aria-hidden="true"></i>Modelador</span></div>
              <div style="display:flex; align-items:center; gap:6px; min-width:0;"><span style="width:20px; height:20px; border-radius:50%; flex:none; background:color-mix(in oklab, oklch(0.62 0.15 45) 45%, #14141d); color:#f5f4fb; font-size:8.5px; font-weight:800; display:flex; align-items:center; justify-content:center;">CM</span><span style="font-size:11px; font-weight:600; color:#d6d4e6;">Clara M.</span></div>
              <div style="font-size:10.5px; font-weight:600; color:#9a97b8;"><i class="fi fi-sr-calendar" style="opacity:.75; font-size:9.5px;" aria-hidden="true"></i> 22 de Out</div>
              <div><span style="display:inline-flex; border-radius:6px; padding:3px 8px; font-size:10px; font-weight:700; background:rgba(124,111,255,.18); color:#b3aaff;">Em andamento</span></div>
            </div>
            <div style="display:grid; grid-template-columns:minmax(0,1fr) 104px 118px 86px 104px; gap:8px; padding:10px 12px; align-items:center;">
              <div style="min-width:0;"><span style="font-family:'JetBrains Mono', monospace; font-size:9.5px; color:#8f8da8;">SD-112</span> <span style="font-size:12px; font-weight:700; color:#f5f4fb;">Hitbox da espada</span></div>
              <div><span style="display:inline-flex; align-items:center; gap:4px; border-radius:6px; padding:3px 7px; font-size:10px; font-weight:700; background:color-mix(in oklab, oklch(0.62 0.15 265) 20%, #14141d); color:color-mix(in oklab, oklch(0.62 0.15 265) 75%, #fff);"><i class="fi fi-sr-code-simple" aria-hidden="true"></i>Scripter</span></div>
              <div style="display:flex; align-items:center; gap:6px; min-width:0;"><span style="width:20px; height:20px; border-radius:50%; flex:none; background:color-mix(in oklab, oklch(0.62 0.15 265) 45%, #14141d); color:#f5f4fb; font-size:8.5px; font-weight:800; display:flex; align-items:center; justify-content:center;">LS</span><span style="font-size:11px; font-weight:600; color:#d6d4e6;">Lucas S.</span></div>
              <div style="font-size:10.5px; font-weight:600; color:#ff8f98;"><i class="fi fi-sr-calendar" style="opacity:.75; font-size:9.5px;" aria-hidden="true"></i> Ontem</div>
              <div><span style="display:inline-flex; border-radius:6px; padding:3px 8px; font-size:10px; font-weight:700; background:rgba(154,154,176,.12); color:#adaac8;">Pendente</span></div>
            </div>
          </div>
        </div>

        <div v-else-if="activeTab === 'dashboard'" style="display:flex; gap:18px; flex-wrap:wrap;">
          <div style="flex:1 1 280px; min-width:260px;">
            <div style="font-size:15px; font-weight:800; color:#f5f4fb; margin-bottom:6px;">Dashboard</div>
            <p style="margin:0 0 12px; font-size:12.5px; line-height:1.6; color:#9a97b8;">Os mesmos dados do quadro, só que somados. Serve para ver se alguém está sobrecarregado antes de atribuir mais uma tarefa.</p>
            <div style="display:flex; flex-direction:column; gap:7px;">
              <div style="font-size:12px; color:#c7c5dc; display:flex; gap:8px;"><i class="fi fi-sr-chart-simple" style="color:#b3aaff; margin-top:2px;" aria-hidden="true"></i>Total, atrasadas, concluídas e em andamento no topo</div>
              <div style="font-size:12px; color:#c7c5dc; display:flex; gap:8px;"><i class="fi fi-sr-scale-comparison" style="color:#b3aaff; margin-top:2px;" aria-hidden="true"></i>Barras por status, prioridade, cargo e carga por pessoa</div>
            </div>
          </div>
          <div style="flex:1 1 380px; min-width:340px;">
            <div style="display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:8px; margin-bottom:10px;">
              <div style="background:#101017; border:1px solid #22222f; border-radius:10px; padding:11px;"><div style="font-size:19px; font-weight:800; color:#f5f4fb;">18</div><div style="font-size:10.5px; color:#8b899f; margin-top:2px;">Total</div></div>
              <div style="background:#101017; border:1px solid #22222f; border-radius:10px; padding:11px;"><div style="font-size:19px; font-weight:800; color:#ff8f98;">2</div><div style="font-size:10.5px; color:#8b899f; margin-top:2px;">Atrasadas</div></div>
              <div style="background:#101017; border:1px solid #22222f; border-radius:10px; padding:11px;"><div style="font-size:19px; font-weight:800; color:#6fe3a4;">3</div><div style="font-size:10.5px; color:#8b899f; margin-top:2px;">Concluídas</div></div>
              <div style="background:#101017; border:1px solid #22222f; border-radius:10px; padding:11px;"><div style="font-size:19px; font-weight:800; color:#b3aaff;">8</div><div style="font-size:10.5px; color:#8b899f; margin-top:2px;">Em and.</div></div>
            </div>
            <div style="background:#101017; border:1px solid #22222f; border-radius:10px; padding:13px;">
              <div style="font-size:11.5px; font-weight:800; color:#f5f4fb; margin-bottom:10px;">Carga por pessoa</div>
              <div style="margin-bottom:9px;">
                <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#c7c5dc; margin-bottom:4px;"><span>Lucas Silva</span><span style="color:#8b899f;">6 abertas · 2 feitas</span></div>
                <div style="background:#0e0e14; border-radius:6px; height:8px; overflow:hidden; display:flex;"><div style="width:60%; height:100%; background:#7c6fff;"></div><div style="width:20%; height:100%; background:#3fcf8e;"></div></div>
              </div>
              <div>
                <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#c7c5dc; margin-bottom:4px;"><span>Clara Martins</span><span style="color:#8b899f;">4 abertas · 3 feitas</span></div>
                <div style="background:#0e0e14; border-radius:6px; height:8px; overflow:hidden; display:flex;"><div style="width:40%; height:100%; background:#7c6fff;"></div><div style="width:30%; height:100%; background:#3fcf8e;"></div></div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="activeTab === 'history'" style="display:flex; gap:18px; flex-wrap:wrap;">
          <div style="flex:1 1 280px; min-width:260px;">
            <div style="font-size:15px; font-weight:800; color:#f5f4fb; margin-bottom:6px;">Histórico</div>
            <p style="margin:0 0 12px; font-size:12.5px; line-height:1.6; color:#9a97b8;">Registro automático de tudo: criação de tarefa, mudança de status, reatribuição e anexos. Aparece só para quem está logado.</p>
            <div style="font-size:12px; color:#c7c5dc; display:flex; gap:8px;"><i class="fi fi-sr-clock" style="color:#b3aaff; margin-top:2px;" aria-hidden="true"></i>Ninguém precisa anotar nada — o log é gerado pelo próprio sistema.</div>
          </div>
          <div style="flex:1 1 380px; min-width:340px; background:#101017; border:1px solid #22222f; border-radius:10px; padding:13px; display:flex; flex-direction:column; gap:10px;">
            <div style="display:flex; gap:9px;"><i class="fi fi-sr-clock" style="color:#8f8da8; font-size:11px; margin-top:3px;" aria-hidden="true"></i><div><div style="font-size:12px; color:#e4e2f1;"><span style="font-weight:700; color:#f5f4fb;">Akanub</span> — atribuiu SD-112 a Lucas Silva</div><div style="font-size:10.5px; color:#8f8da8; margin-top:2px;">hoje às 14:02</div></div></div>
            <div style="display:flex; gap:9px;"><i class="fi fi-sr-clock" style="color:#8f8da8; font-size:11px; margin-top:3px;" aria-hidden="true"></i><div><div style="font-size:12px; color:#e4e2f1;"><span style="font-weight:700; color:#f5f4fb;">Beatriz Costa</span> — anexou uma prova em SD-090</div><div style="font-size:10.5px; color:#8f8da8; margin-top:2px;">hoje às 11:47</div></div></div>
            <div style="display:flex; gap:9px;"><i class="fi fi-sr-clock" style="color:#8f8da8; font-size:11px; margin-top:3px;" aria-hidden="true"></i><div><div style="font-size:12px; color:#e4e2f1;"><span style="font-weight:700; color:#f5f4fb;">Clara Martins</span> — moveu SD-104 para Em andamento</div><div style="font-size:10.5px; color:#8f8da8; margin-top:2px;">ontem às 18:20</div></div></div>
          </div>
        </div>

        <div v-else-if="activeTab === 'team'" style="display:flex; gap:18px; flex-wrap:wrap;">
          <div style="flex:1 1 280px; min-width:260px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
              <span style="font-size:15px; font-weight:800; color:#f5f4fb;">Equipe</span>
              <span style="font-size:9px; font-weight:700; letter-spacing:.04em; color:#b3aaff; background:rgba(124,111,255,.16); border-radius:999px; padding:2px 6px;">SÓ ADMIN</span>
            </div>
            <p style="margin:0 0 12px; font-size:12.5px; line-height:1.6; color:#9a97b8;">Adicionar ou remover pessoas, definir cargos e senha, e promover alguém a admin. A aba só aparece se você for administrador.</p>
            <div style="font-size:12px; color:#c7c5dc; display:flex; gap:8px;"><i class="fi fi-sr-users" style="color:#b3aaff; margin-top:2px;" aria-hidden="true"></i>Sempre precisa sobrar pelo menos um admin.</div>
          </div>
          <div style="flex:1 1 380px; min-width:340px; background:#101017; border:1px solid #22222f; border-radius:10px; padding:13px; display:flex; flex-direction:column; gap:8px;">
            <div style="display:flex; align-items:center; gap:10px; background:#0e0e14; border:1px solid #22222f; border-radius:9px; padding:9px 11px;">
              <span style="width:26px; height:26px; border-radius:50%; flex:none; background:#7c6fff; color:#0a0a10; font-size:10px; font-weight:800; display:flex; align-items:center; justify-content:center;">AK</span>
              <div style="flex:1;"><div style="font-size:12px; font-weight:700; color:#f5f4fb;">Akanub</div><div style="font-size:10.5px; color:#8b899f;">Manager</div></div>
              <span style="font-size:9px; font-weight:700; color:#b3aaff; background:rgba(124,111,255,.16); border-radius:999px; padding:2px 6px;">ADMIN</span>
            </div>
            <div style="display:flex; align-items:center; gap:10px; background:#0e0e14; border:1px solid #22222f; border-radius:9px; padding:9px 11px;">
              <span style="width:26px; height:26px; border-radius:50%; flex:none; background:color-mix(in oklab, oklch(0.62 0.15 265) 45%, #14141d); color:#f5f4fb; font-size:10px; font-weight:800; display:flex; align-items:center; justify-content:center;">LS</span>
              <div style="flex:1;"><div style="font-size:12px; font-weight:700; color:#f5f4fb;">Lucas Silva</div><div style="font-size:10.5px; color:#8b899f;">Scripter</div></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- how to assign -->
    <div>
      <div style="font-size:10.5px; font-weight:700; letter-spacing:.09em; color:#8b899f; margin-bottom:6px; font-family:'JetBrains Mono', monospace;">COMO ATRIBUIR UMA TAREFA</div>
      <div style="font-size:13px; color:#9a97b8; margin-bottom:14px;">Só o administrador atribui. Leva menos de um minuto.</div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:10px;">
        <div v-for="s in STEPS" :key="s.n" :style="{ background: s.highlight ? 'rgba(124,111,255,.10)' : '#14141d', border: `1px solid ${s.highlight ? 'rgba(124,111,255,.3)' : '#22222f'}`, borderRadius: '12px', padding: '14px' }">
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <span style="width:22px; height:22px; border-radius:7px; background:#7c6fff; color:#0a0a10; font-size:11px; font-weight:800; display:flex; align-items:center; justify-content:center; flex:none;">{{ s.n }}</span>
            <span style="font-size:13px; font-weight:700; color:#f5f4fb;">{{ s.title }}</span>
          </div>
          <div :style="{ fontSize: '11.5px', lineHeight: 1.55, color: s.highlight ? '#b0abd6' : '#8b899f' }">{{ s.desc }}</div>
        </div>
      </div>
    </div>

    <!-- two column explainer -->
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:14px;">
      <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
        <div style="font-size:13px; font-weight:700; color:#f5f4fb; margin-bottom:6px;">Modo Tabela ou Modo Cards</div>
        <p style="margin:0 0 12px; font-size:11.5px; line-height:1.6; color:#8b899f;">O mesmo quadro em duas visões. Tabela é para ler tudo de uma vez e agir em massa. Cards é o Kanban por status — o admin arrasta o card de Pendente para Em andamento e para Concluída.</p>
        <div style="display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:7px;">
          <div style="background:#101017; border:1px solid #22222f; border-radius:9px; padding:8px;"><div style="font-size:10px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Pendente <span style="opacity:.6;">4</span></div><div style="background:#0e0e14; border:1px solid #22222f; border-radius:7px; padding:7px;"><div style="font-family:'JetBrains Mono', monospace; font-size:8.5px; color:#8f8da8; margin-bottom:4px;">SD-112</div><div style="font-size:10.5px; font-weight:700; color:#f5f4fb;">Hitbox da espada</div></div></div>
          <div style="background:#101017; border:1px solid #22222f; border-radius:9px; padding:8px;"><div style="font-size:10px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Em andamento <span style="opacity:.6;">8</span></div><div style="background:#0e0e14; border:1px dashed #7c6fff; border-radius:7px; padding:7px;"><div style="font-family:'JetBrains Mono', monospace; font-size:8.5px; color:#8f8da8; margin-bottom:4px;">SD-104</div><div style="font-size:10.5px; font-weight:700; color:#f5f4fb;">Lobby v2 — props</div></div></div>
          <div style="background:#101017; border:1px solid #22222f; border-radius:9px; padding:8px;"><div style="font-size:10px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Concluída <span style="opacity:.6;">3</span></div><div style="background:#0e0e14; border:1px solid #22222f; border-radius:7px; padding:7px;"><div style="font-family:'JetBrains Mono', monospace; font-size:8.5px; color:#8f8da8; margin-bottom:4px;">SD-090</div><div style="font-size:10.5px; font-weight:700; color:#f5f4fb;">VFX do portal</div></div></div>
        </div>
      </div>
      <div style="background:#14141d; border:1px solid #22222f; border-radius:12px; padding:16px;">
        <div style="font-size:13px; font-weight:700; color:#f5f4fb; margin-bottom:6px;">A página de cada tarefa</div>
        <p style="margin:0 0 12px; font-size:11.5px; line-height:1.6; color:#8b899f;">Clique numa linha do quadro e a tarefa abre em endereço próprio, fácil de mandar para alguém. Dentro dela: checklist, anexos e histórico.</p>
        <div style="display:flex; flex-direction:column; gap:7px;">
          <div style="background:#101017; border:1px solid #22222f; border-radius:9px; padding:10px;">
            <div style="font-size:11px; font-weight:700; color:#c7c5dc; margin-bottom:6px;">Checklist do que fazer <span style="font-weight:500; color:#8b899f;">2/3</span></div>
            <div style="display:flex; align-items:center; gap:8px; background:#0e0e14; border:1px solid #22222f; border-radius:7px; padding:6px 9px;">
              <span style="width:13px; height:13px; border-radius:4px; background:#7c6fff; color:#0a0a10; font-size:8px; display:flex; align-items:center; justify-content:center; flex:none;"><i class="fi fi-sr-check" aria-hidden="true"></i></span>
              <span style="font-size:11px; color:#8f8da8; text-decoration:line-through;">Blockout aprovado</span>
            </div>
          </div>
          <div style="display:flex; gap:7px;">
            <div style="flex:1; background:#101017; border:1px solid #22222f; border-radius:9px; padding:10px;"><div style="font-size:11px; font-weight:700; color:#c7c5dc; display:flex; align-items:center; gap:6px;"><i class="fi fi-sr-paperclip" style="color:#b3aaff;" aria-hidden="true"></i>Anexos</div><div style="font-size:10.5px; color:#8b899f; margin-top:4px; line-height:1.5;">Print, vídeo ou link como prova do que foi feito. Qualquer pessoa logada pode anexar.</div></div>
            <div style="flex:1; background:#101017; border:1px solid #22222f; border-radius:9px; padding:10px;"><div style="font-size:11px; font-weight:700; color:#c7c5dc; display:flex; align-items:center; gap:6px;"><i class="fi fi-sr-clock" style="color:#b3aaff;" aria-hidden="true"></i>Histórico</div><div style="font-size:10.5px; color:#8b899f; margin-top:4px; line-height:1.5;">Cada mudança de status e reatribuição fica registrada na própria tarefa.</div></div>
          </div>
        </div>
      </div>
    </div>

    <!-- footer -->
    <div style="padding:16px 0 0; border-top:1px solid #1a1a25; display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
      <span style="font-size:11.5px; color:#8b899f;">Leitura é pública. Só o administrador cria, edita e exclui tarefas.</span>
      <div style="flex:1;"></div>
      <button type="button" @click="go('board')" style="border:none; background:transparent; color:#8a7dff; font-size:12px; font-weight:700; cursor:pointer;">Ir para o quadro →</button>
    </div>

  </div>
</template>
