<script setup>
// The ShyDevs mascot: a Roblox noob spinning in place (three.js, lazy-loaded).
// The static mascot only shows if WebGL or the model fails; while loading the
// box stays empty, so nothing jumps in size when the model appears.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { mascot } from '../mascotFace'
import { workload } from '../workload'

const props = defineProps({
  size: { type: Number, default: 32 },
  spinnable: { type: Boolean, default: false }, // click to flick it like a fidget spinner
})
const host = ref(null)
const failed = ref(false)

const SPIN = 0.9 // rad/s
const START_YAW = 0.3
const GLITCH_FROM = 3 // tasks at which the glitch (and speed-up) starts
const IDLE_BOOST = 11 // extra rad/s of idle spin at max task load
const CELEBRATE_SPIN = 22 // rad/s on task completion
const KICK = 7 // rad/s added per click
const MAX_SPIN = 30 // rad/s cap (~5 turns/s)
const DRAG = 0.55 // 1/s: how fast it coasts back to the idle speed

let vel = SPIN
// Completing a task sends every noob into a big spin that coasts back down.
watch(() => workload.completions, () => { vel = Math.max(vel, CELEBRATE_SPIN) })
function flick() {
  if (props.spinnable) vel = Math.min(vel + KICK, MAX_SPIN)
}

let raf = 0
let dispose = () => {}

// The model's UV atlas (1023x505), redrawn: the OBJ ships without its texture.
const B = '#0d69ac', Y = '#f5cd30', G = '#a6bd47'
const ATLAS = [
  [B, 0, 0, 145, 448], [Y, 150, 0, 144, 320], [Y, 300, 0, 144, 320], [G, 450, 0, 144, 320], [G, 600, 0, 144, 320],
  [B, 145, 322, 205, 76], [G, 350, 322, 219, 76], [Y, 569, 322, 161, 76],
  [Y, 146, 394, 57, 76], [B, 204, 401, 111, 104], [Y, 315, 400, 222, 105], [G, 537, 400, 222, 105],
  [Y, 895, 0, 128, 128], // head front, with the face
]
function atlasTexture(THREE) {
  const c = document.createElement('canvas')
  c.width = 1023; c.height = 505
  const g = c.getContext('2d')
  for (const [col, x, y, w, h] of ATLAS) { g.fillStyle = col; g.fillRect(x, y, w, h) }
  g.fillStyle = '#000'
  for (const x of [947, 970]) { g.beginPath(); g.ellipse(x, 39, 4.5, 10, 0, 0, Math.PI * 2); g.fill() }
  g.strokeStyle = '#000'; g.lineWidth = 7; g.lineCap = 'round'
  g.beginPath(); g.moveTo(941, 75); g.quadraticCurveTo(959, 102, 978, 75); g.stroke()
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  return t
}

onMounted(async () => {
  try {
    const [THREE, { OBJLoader }] = await Promise.all([
      import('three'),
      import('three/examples/jsm/loaders/OBJLoader.js'),
    ])
    const text = await (await fetch('/models/noob.obj')).text()
    if (!host.value) return

    const scene = new THREE.Scene()
    scene.add(new THREE.HemisphereLight(0xffffff, 0x555566, 1.6))
    const sun = new THREE.DirectionalLight(0xffffff, 1.4)
    sun.position.set(2, 4, 5)
    scene.add(sun)

    const model = new OBJLoader().parse(text)
    const material = new THREE.MeshLambertMaterial({ map: atlasTexture(THREE) })
    // Glitch: horizontal slices of the model get shoved sideways in random
    // bursts. Strength grows continuously with the person's open-task count.
    const uniforms = { uTime: { value: 0 }, uGlitch: { value: 0 }, uBurst: { value: 0 } }
    material.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, uniforms)
      sh.vertexShader = `uniform float uTime; uniform float uGlitch; uniform float uBurst;
float h(float n) { return fract(sin(n * 127.1) * 43758.5453); }
` + sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
float band = floor(position.y * 3.2);
float tick = floor(uTime * 22.0);
float on = step(0.35, h(band + tick * 3.7));
transformed.x += (h(band * 7.31 + tick) - 0.5) * (uBurst * 2.2 + 0.05) * uGlitch * on;
transformed.z += (h(band * 3.1 + tick) - 0.5) * uBurst * uGlitch * 0.9;`)
    }
    model.traverse((o) => { if (o.isMesh) o.material = material })

    model.position.sub(new THREE.Box3().setFromObject(model).getCenter(new THREE.Vector3()))
    const pivot = new THREE.Group()
    pivot.add(model)
    pivot.rotation.y = START_YAW
    scene.add(pivot)

    const half = 3.0
    const camera = new THREE.OrthographicCamera(-half, half, half, -half, 0.1, 100)
    const tilt = (14 * Math.PI) / 180
    camera.position.set(0, Math.sin(tilt) * 20, Math.cos(tilt) * 20)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setPixelRatio(Math.min(Math.max(window.devicePixelRatio || 1, 2), 3))
    renderer.setSize(props.size, props.size)
    renderer.domElement.style.cssText = 'position:absolute; inset:0; width:100%; height:100%; display:block;'
    host.value.appendChild(renderer.domElement)

    const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    let last = performance.now()
    const frame = (now) => {
      const dt = Math.min((now - last) / 1000, 0.1)
      // intensity 0..1, smooth in the task count (no stages): 0 below GLITCH_FROM, ~0.6 ten tasks later
      const g = 1 - Math.exp(-Math.max(0, workload.count - (GLITCH_FROM - 1)) / 10)
      // more tasks -> faster idle spin (0.9 rad/s up to ~12 rad/s)
      const idle = still ? 0 : SPIN + g * IDLE_BOOST
      vel = idle + (vel - idle) * Math.exp(-DRAG * dt)
      pivot.rotation.y += vel * dt
      last = now

      const t = now / 1000
      const burstRoll = Math.sin(Math.floor(t * 8) * 91.7) * 43758.5453 % 1
      const burst = Math.abs(burstRoll) > 1 - (0.08 + 0.7 * g) ? 1 : 0
      uniforms.uTime.value = t
      uniforms.uGlitch.value = g
      uniforms.uBurst.value = burst
      const d = (burst * 3 + 0.4) * g // RGB-split distance in px
      const el = renderer.domElement
      el.style.filter = g > 0.001 ? `drop-shadow(${d}px 0 0 rgba(255,40,80,.85)) drop-shadow(${-d}px 0 0 rgba(0,230,255,.85))` : ''
      el.style.opacity = burst && g > 0.5 && Math.sin(t * 90) > 0.6 ? String(1 - 0.5 * g) : '1'
      renderer.render(scene, camera)
      raf = requestAnimationFrame(frame)
    }
    raf = requestAnimationFrame(frame)

    dispose = () => {
      cancelAnimationFrame(raf)
      scene.traverse((o) => { o.geometry?.dispose() })
      material.map.dispose(); material.dispose()
      renderer.dispose()
    }
  } catch (e) {
    failed.value = true
  }
})
onBeforeUnmount(() => dispose())
</script>

<template>
  <div ref="host" @click="flick" :style="{ position: 'relative', width: size + 'px', height: size + 'px', flex: 'none' }" role="img" aria-label="Mascote ShyDevs">
    <img v-if="failed" :src="mascot" alt="" :width="size" :height="size" style="width:100%; height:100%; object-fit:contain; display:block;" />
  </div>
</template>
