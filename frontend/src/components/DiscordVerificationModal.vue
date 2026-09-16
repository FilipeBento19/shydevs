<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { api } from '../api'
import { mascot } from '../mascotFace'

const props = defineProps({
  open: { type: Boolean, default: false },
  person: { type: Object, default: null },
})
const emit = defineEmits(['close', 'verified'])

const code = ref('')
const loading = ref(false)
const verified = ref(false)
const copied = ref(false)
const error = ref('')
let pollTimer = null

const title = computed(() => verified.value ? 'Discord verificado' : `Verificar Discord de ${props.person?.name || ''}`)

function stopPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
}

async function checkStatus() {
  if (!props.person?.id) return
  try {
    const status = await api.getDiscordVerification(props.person.id)
    if (status.verified) {
      verified.value = true
      stopPolling()
      emit('verified', { ...props.person, discord_id: status.discord_id, discord_verified: true, discord_verified_at: status.verified_at })
    }
  } catch (e) {
    // Keep polling; a temporary network error should not interrupt the flow.
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(checkStatus, 2500)
}

async function begin() {
  if (!props.person?.id) return
  loading.value = true
  error.value = ''
  copied.value = false
  try {
    const result = await api.startDiscordVerification(props.person.id)
    code.value = result.code
    verified.value = false
    startPolling()
  } catch (e) {
    error.value = e.message || 'Não foi possível iniciar a verificação.'
  } finally {
    loading.value = false
  }
}

async function copyCode() {
  if (!code.value) return
  try {
    await navigator.clipboard.writeText(code.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch (e) {
    error.value = 'Copie o código manualmente.'
  }
}

watch(() => props.open, async (open) => {
  stopPolling()
  code.value = ''
  error.value = ''
  copied.value = false
  verified.value = !!props.person?.discord_verified
  if (open && !verified.value) await begin()
})

onUnmounted(stopPolling)
</script>

<template>
  <Teleport to="body">
    <Transition name="verify-modal">
      <div v-if="open" class="verify-backdrop" @mousedown.self="$emit('close')">
        <section class="verify-modal" role="dialog" aria-modal="true" :aria-labelledby="`verify-title-${person?.id}`">
          <button class="verify-close" type="button" aria-label="Fechar verificação" @click="$emit('close')"><i class="fi fi-sr-cross-small" aria-hidden="true"></i></button>

          <div class="verify-heading">
            <span class="discord-mark"><i class="fi fi-sr-comment-alt" aria-hidden="true"></i></span>
            <div>
              <span class="verify-eyebrow">Conexão segura</span>
              <h2 :id="`verify-title-${person?.id}`">{{ title }}</h2>
              <p v-if="!verified">O código precisa ser enviado pela conta do Discord de {{ person?.name }}. Ela só será confirmada depois que o bot conseguir responder.</p>
              <p v-else>O bot confirmou uma conversa direta com esta conta.</p>
            </div>
          </div>

          <div v-if="verified" class="verified-result">
            <span><i class="fi fi-sr-check" aria-hidden="true"></i></span>
            <strong>Pronto para receber mensagens</strong>
            <p>O Discord ID foi capturado automaticamente e não precisa ser digitado.</p>
            <button type="button" @click="$emit('close')">Concluir</button>
          </div>

          <template v-else>
            <div class="motion-tutorial" aria-label="Tutorial animado: copie o código, envie por DM ao bot e aguarde a confirmação">
              <div class="motion-step site-step">
                <span class="motion-label">1 · Copie</span>
                <div class="mini-code"><img :src="mascot" alt="" /><span>SHY-••••••</span><i class="fi fi-sr-copy" aria-hidden="true"></i></div>
              </div>
              <div class="motion-path" aria-hidden="true"><span></span><i class="fi fi-sr-arrow-right"></i></div>
              <div class="motion-step dm-step">
                <span class="motion-label">2 · Envie por DM</span>
                <div class="mini-chat"><i class="fi fi-sr-comment-alt" aria-hidden="true"></i><span>SHY-••••••</span></div>
                <div class="mini-reply"><i class="fi fi-sr-check-circle" aria-hidden="true"></i>Verificado</div>
              </div>
            </div>

            <ol class="verify-steps">
              <li><span>1</span><div><strong>Encontre o bot ShyDevs no Discord</strong><p>Abra o servidor, clique no bot na lista de membros e escolha “Mensagem”.</p></div></li>
              <li><span>2</span><div><strong>Envie somente este código na conta correta</strong><p>{{ person?.name }} deve enviar pela própria conta. O Discord ID será capturado automaticamente.</p></div></li>
              <li><span>3</span><div><strong>Aguarde a resposta do bot</strong><p>Quando ele responder, esta janela será atualizada automaticamente.</p></div></li>
            </ol>

            <div class="verification-code" :class="{ loading }">
              <span>{{ loading ? 'Gerando código…' : code || 'Código indisponível' }}</span>
              <button type="button" :disabled="loading || !code" @click="copyCode"><i :class="`fi ${copied ? 'fi-sr-check' : 'fi-sr-copy'}`" aria-hidden="true"></i>{{ copied ? 'Copiado' : 'Copiar' }}</button>
            </div>
            <p class="code-expiry"><i class="fi fi-sr-clock" aria-hidden="true"></i>O código expira em 15 minutos.</p>
            <p v-if="error" class="verify-error" role="alert">{{ error }}</p>
            <div class="waiting-row"><span class="waiting-pulse" aria-hidden="true"></span>Aguardando a mensagem no Discord…<button type="button" @click="begin">Gerar outro código</button></div>
          </template>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.verify-backdrop { position: fixed; inset: 0; z-index: 1200; display: grid; place-items: center; padding: 18px; background: rgba(4,4,8,.78); backdrop-filter: blur(5px); }
.verify-modal { position: relative; width: min(620px, 100%); max-height: calc(100vh - 36px); overflow-y: auto; box-sizing: border-box; padding: 22px; border: 1px solid #2b2a3c; border-radius: 16px; background: #121219; color: #f5f4fb; box-shadow: 0 28px 90px rgba(0,0,0,.65); }
.verify-close { position: absolute; top: 13px; right: 13px; display: grid; place-items: center; width: 30px; height: 30px; border: 1px solid #292837; border-radius: 8px; background: #171720; color: #858297; cursor: pointer; }
.verify-heading { display: flex; align-items: flex-start; gap: 12px; padding-right: 34px; }
.discord-mark { display: grid; place-items: center; width: 39px; height: 39px; flex: none; border: 1px solid rgba(124,111,255,.32); border-radius: 11px; background: rgba(124,111,255,.14); color: #aaa1ff; font-size: 17px; }
.verify-eyebrow { color: #9187f2; font-size: 8.5px; font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
.verify-heading h2 { margin: 4px 0; font-size: 18px; letter-spacing: -.02em; }
.verify-heading p { margin: 0; color: #858297; font-size: 10.5px; line-height: 1.5; }
.motion-tutorial { display: grid; grid-template-columns: 1fr 68px 1fr; align-items: center; gap: 8px; min-height: 126px; margin-top: 18px; padding: 14px; overflow: hidden; border: 1px solid #242332; border-radius: 12px; background: #0d0d13; }
.motion-step { min-width: 0; }
.motion-label { display: block; margin-bottom: 7px; color: #747185; font-size: 8px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }
.mini-code, .mini-chat { display: flex; align-items: center; gap: 7px; height: 43px; padding: 0 9px; border: 1px solid #302e42; border-radius: 9px; background: #171720; }
.mini-code img { width: 25px; height: 25px; object-fit: contain; }
.mini-code span, .mini-chat span { min-width: 0; flex: 1; color: #cbc7df; font-size: 10px; font-weight: 800; letter-spacing: .06em; }
.mini-code i { color: #8177df; }
.mini-chat { transform: translateY(8px); animation: dm-arrive 6s cubic-bezier(.22,1,.36,1) infinite; }
.mini-chat > i { color: #8e84eb; font-size: 15px; }
.mini-reply { display: inline-flex; align-items: center; gap: 5px; margin: 13px 0 0 9px; padding: 5px 7px; border: 1px solid rgba(63,207,142,.28); border-radius: 7px; background: rgba(63,207,142,.1); color: #72dca7; font-size: 8px; font-weight: 800; opacity: 0; animation: reply-in 6s ease-out infinite; }
.motion-path { position: relative; display: flex; align-items: center; color: #756bda; }
.motion-path::before { content: ''; width: 100%; height: 1px; background: #302d4d; }
.motion-path i { margin-left: -4px; font-size: 10px; }
.motion-path span { position: absolute; left: 0; width: 7px; height: 7px; border-radius: 50%; background: #8f84ff; box-shadow: 0 0 10px rgba(124,111,255,.65); animation: code-travel 6s cubic-bezier(.22,1,.36,1) infinite; }
.verify-steps { display: grid; gap: 8px; margin: 14px 0; padding: 0; list-style: none; }
.verify-steps li { display: flex; gap: 9px; padding: 9px 10px; border: 1px solid #22212e; border-radius: 9px; background: #101017; }
.verify-steps li > span { display: grid; place-items: center; width: 21px; height: 21px; flex: none; border-radius: 6px; background: rgba(124,111,255,.14); color: #aaa1ff; font-size: 8.5px; font-weight: 800; }
.verify-steps strong, .verify-steps p { display: block; }
.verify-steps strong { font-size: 10.5px; }
.verify-steps p { margin: 3px 0 0; color: #77758d; font-size: 9px; line-height: 1.45; }
.verification-code { display: flex; align-items: center; gap: 9px; padding: 9px 9px 9px 13px; border: 1px solid rgba(124,111,255,.4); border-radius: 10px; background: rgba(124,111,255,.08); }
.verification-code > span { flex: 1; color: #d8d4ff; font-size: 18px; font-weight: 900; letter-spacing: .12em; }
.verification-code button { display: inline-flex; align-items: center; gap: 5px; min-height: 31px; padding: 0 10px; border: 0; border-radius: 7px; background: #7c6fff; color: #0a0a10; font: inherit; font-size: 9.5px; font-weight: 800; cursor: pointer; }
.verification-code button:disabled { opacity: .45; cursor: wait; }
.code-expiry { display: flex; align-items: center; gap: 5px; margin: 6px 0 0; color: #615e70; font-size: 8.5px; }
.waiting-row { display: flex; align-items: center; gap: 7px; margin-top: 13px; color: #858297; font-size: 9.5px; }
.waiting-row button { margin-left: auto; padding: 0; border: 0; background: transparent; color: #9187e9; font: inherit; font-size: 9px; font-weight: 700; cursor: pointer; }
.waiting-pulse { width: 7px; height: 7px; border-radius: 50%; background: #7c6fff; animation: waiting 1.6s ease-in-out infinite; }
.verify-error { margin: 9px 0 0; color: #ff8f98; font-size: 10px; }
.verified-result { display: grid; justify-items: center; margin-top: 20px; padding: 25px; border: 1px solid rgba(63,207,142,.25); border-radius: 12px; background: rgba(63,207,142,.07); text-align: center; }
.verified-result > span { display: grid; place-items: center; width: 44px; height: 44px; margin-bottom: 10px; border-radius: 50%; background: #3fcf8e; color: #07150e; font-size: 17px; }
.verified-result strong { font-size: 14px; }
.verified-result p { margin: 5px 0 15px; color: #79a58d; font-size: 10px; }
.verified-result button { border: 0; border-radius: 8px; padding: 8px 16px; background: #3fcf8e; color: #07150e; font: inherit; font-size: 10.5px; font-weight: 800; cursor: pointer; }
.verify-modal-enter-active { transition: opacity 220ms ease-out; }
.verify-modal-leave-active { transition: opacity 160ms ease-in; }
.verify-modal-enter-from, .verify-modal-leave-to { opacity: 0; }
.verify-modal-enter-active .verify-modal { transition: transform 280ms cubic-bezier(.22,1,.36,1), opacity 220ms ease-out; }
.verify-modal-enter-from .verify-modal { transform: translateY(14px) scale(.985); opacity: 0; }
@keyframes code-travel { 0%,18% { transform: translateX(0); opacity: 0; } 24% { opacity: 1; } 53% { transform: translateX(58px); opacity: 1; } 60%,100% { transform: translateX(58px); opacity: 0; } }
@keyframes dm-arrive { 0%,36% { transform: translateY(8px); opacity: .45; } 53%,88% { transform: translateY(0); opacity: 1; } 100% { opacity: .45; } }
@keyframes reply-in { 0%,58% { transform: translateY(5px); opacity: 0; } 68%,90% { transform: translateY(0); opacity: 1; } 100% { opacity: 0; } }
@keyframes waiting { 0%,100% { opacity: .35; transform: scale(.8); } 50% { opacity: 1; transform: scale(1); } }
@media (prefers-reduced-motion: reduce) {
  .motion-path span, .mini-chat, .mini-reply, .waiting-pulse { animation: none; }
  .mini-chat { transform: none; opacity: 1; }
  .mini-reply { transform: none; opacity: 1; }
  .motion-path span { left: calc(100% - 7px); }
}
@media (max-width: 560px) {
  .verify-modal { padding: 17px; }
  .motion-tutorial { grid-template-columns: 1fr; }
  .motion-path { height: 22px; transform: rotate(90deg); justify-self: center; width: 28px; }
  .verification-code > span { font-size: 14px; }
}
</style>
