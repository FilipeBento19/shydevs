import gsap from 'gsap'

export const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function modalEnter(el, done) {
  if (reduceMotion) return done()
  const panel = el.querySelector('.modal-panel') || el.firstElementChild
  gsap.fromTo(el, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.25, ease: 'power1.out' })
  gsap.fromTo(
    panel,
    { y: 24, scale: 0.96, autoAlpha: 0 },
    { y: 0, scale: 1, autoAlpha: 1, duration: 0.4, ease: 'power3.out', onComplete: done }
  )
}

export function modalLeave(el, done) {
  if (reduceMotion) return done()
  const panel = el.querySelector('.modal-panel') || el.firstElementChild
  gsap.to(panel, { y: 16, scale: 0.97, autoAlpha: 0, duration: 0.2, ease: 'power2.in' })
  gsap.to(el, { autoAlpha: 0, duration: 0.26, ease: 'power1.in', onComplete: done })
}

export function popEnter(el, done) {
  if (reduceMotion) return done()
  gsap.fromTo(
    el,
    { autoAlpha: 0, y: -6, scale: 0.96 },
    { autoAlpha: 1, y: 0, scale: 1, duration: 0.22, ease: 'power2.out', onComplete: done }
  )
}
export function popLeave(el, done) {
  if (reduceMotion) return done()
  gsap.to(el, { autoAlpha: 0, y: -6, scale: 0.96, duration: 0.16, ease: 'power1.in', onComplete: done })
}

export function listEnter(el, done) {
  if (reduceMotion) return done()
  const index = Number(el.dataset.index || 0)
  gsap.fromTo(
    el,
    { autoAlpha: 0, y: -8 },
    { autoAlpha: 1, y: 0, duration: 0.32, ease: 'power2.out', delay: Math.min(index * 0.03, 0.3), onComplete: done }
  )
}
export function listLeave(el, done) {
  if (reduceMotion) return done()
  gsap.to(el, { autoAlpha: 0, x: -8, duration: 0.18, ease: 'power1.in', onComplete: done })
}

export function toastEnter(el, done) {
  if (reduceMotion) return done()
  gsap.fromTo(
    el,
    { autoAlpha: 0, y: 16, scale: 0.95 },
    { autoAlpha: 1, y: 0, scale: 1, duration: 0.3, ease: 'back.out(2)', onComplete: done }
  )
}
export function toastLeave(el, done) {
  if (reduceMotion) return done()
  gsap.to(el, { autoAlpha: 0, y: 10, scale: 0.95, duration: 0.2, ease: 'power1.in', onComplete: done })
}

export function cardEnter(el, done) {
  if (reduceMotion) return done()
  gsap.fromTo(
    el,
    { autoAlpha: 0, y: 10, scale: 0.97 },
    { autoAlpha: 1, y: 0, scale: 1, duration: 0.3, ease: 'power2.out', onComplete: done }
  )
}
export function cardLeave(el, done) {
  if (reduceMotion) return done()
  gsap.to(el, { autoAlpha: 0, scale: 0.92, duration: 0.18, ease: 'power1.in', onComplete: done })
}

export { gsap }
