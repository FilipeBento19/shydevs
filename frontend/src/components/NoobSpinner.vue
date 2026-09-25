<script setup>
// The ShyDevs mascot: a Roblox noob spinning in place (three.js, lazy-loaded).
// The static mascot only shows if WebGL or the model fails; while loading the
// box stays empty, so nothing jumps in size when the model appears.
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { mascot } from '../mascotFace'

const props = defineProps({ size: { type: Number, default: 32 } })
const host = ref(null)
const failed = ref(false)

const SPIN = 0.9 // rad/s
const START_YAW = 0.3

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
      if (!still) pivot.rotation.y += ((now - last) / 1000) * SPIN
      last = now
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
  <div ref="host" :style="{ position: 'relative', width: size + 'px', height: size + 'px', flex: 'none' }" role="img" aria-label="Mascote ShyDevs">
    <img v-if="failed" :src="mascot" alt="" :width="size" :height="size" style="width:100%; height:100%; object-fit:contain; display:block;" />
  </div>
</template>
