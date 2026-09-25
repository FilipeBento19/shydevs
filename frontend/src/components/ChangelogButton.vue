<script setup>
import { nextTick, ref } from 'vue'
import { modalEnter, modalLeave } from '../motion'
import { currentVersion, releases } from '../changelog'

const open = ref(false)
const dialog = ref(null)
const trigger = ref(null)

async function show() {
  open.value = true
  await nextTick()
  dialog.value?.focus()
}
function hide() {
  open.value = false
  trigger.value?.focus()
}
</script>

<template>
  <button ref="trigger" type="button" class="cl-btn" aria-label="O que mudou nesta sprint" title="O que mudou nesta sprint" @click="show">?</button>

  <Teleport to="body">
    <Transition :css="false" @enter="modalEnter" @leave="modalLeave">
      <div v-if="open" class="cl-backdrop" @click.self="hide">
        <div ref="dialog" class="cl-dialog modal-panel nice-scroll" role="dialog" aria-modal="true" aria-labelledby="cl-title" tabindex="-1" @keydown.esc="hide">
          <header class="cl-head">
            <div>
              <h2 id="cl-title">Novidades</h2>
              <p>Sprint {{ currentVersion }} · a sprint muda a cada publicação</p>
            </div>
            <button type="button" class="cl-close" aria-label="Fechar" @click="hide"><i class="fi fi-sr-cross" aria-hidden="true"></i></button>
          </header>
          <section v-for="(r, i) in releases" :key="r.version" class="cl-release" :class="{ current: i === 0 }">
            <h3>Sprint {{ r.version }} <span v-if="i === 0" class="cl-tag">atual</span></h3>
            <ul>
              <li v-for="item in r.items" :key="item">{{ item }}</li>
            </ul>
          </section>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.cl-btn { width: 17px; height: 17px; flex: none; display: inline-grid; place-items: center; border: 1px solid #34344a; border-radius: 50%; background: transparent; color: #8b899f; font-size: 10.5px; font-weight: 800; line-height: 1; cursor: pointer; transition: background-color .15s ease, color .15s ease, border-color .15s ease; }
.cl-btn:hover, .cl-btn:focus-visible { background: rgba(124, 111, 255, .18); border-color: #7c6fff; color: #cfc9ff; outline: none; }

.cl-backdrop { position: fixed; inset: 0; z-index: 1000; background: rgba(3, 3, 8, .72); display: flex; align-items: center; justify-content: center; padding: 20px; }
.cl-dialog { width: min(520px, 100%); max-height: min(78vh, 640px); overflow-y: auto; background: #101018; border: 1px solid #22222f; border-radius: 16px; padding: 20px 22px 8px; color: #f5f4fb; outline: none; box-shadow: 0 24px 60px rgba(0, 0, 0, .5); }
.cl-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.cl-head h2 { margin: 0; font-size: 18px; font-weight: 800; letter-spacing: -.01em; }
.cl-head p { margin: 3px 0 0; font-size: 12px; color: #8b899f; }
.cl-close { width: 30px; height: 30px; flex: none; border: 1px solid #26263a; border-radius: 8px; background: #14141d; color: #c7c5dc; font-size: 11px; cursor: pointer; }
.cl-close:hover { background: #1c1c28; color: #fff; }

.cl-release { padding: 14px 0 16px; border-top: 1px solid #1c1c28; }
.cl-release h3 { margin: 0 0 8px; font-size: 13px; font-weight: 800; color: #c7c5dc; display: flex; align-items: center; gap: 8px; }
.cl-release.current h3 { color: #f5f4fb; }
.cl-tag { font-size: 10px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; color: #b8b1ff; background: rgba(124, 111, 255, .16); border-radius: 999px; padding: 2px 8px; }
.cl-release ul { margin: 0; padding-left: 18px; display: grid; gap: 5px; }
.cl-release li { font-size: 12.5px; line-height: 1.5; color: #9a97b8; }
.cl-release.current li { color: #d6d4e6; }
</style>
