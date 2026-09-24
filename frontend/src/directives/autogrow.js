function resize(element) {
  element.style.height = 'auto'
  // scrollHeight excludes borders; with border-box sizing the height we set
  // has to include them or the last line gets clipped by a couple of pixels.
  const style = getComputedStyle(element)
  const border = style.boxSizing === 'border-box'
    ? parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth)
    : 0
  element.style.height = `${element.scrollHeight + border}px`
}

function handleInput(event) {
  resize(event.currentTarget)
}

const observers = new WeakMap()

export const vAutogrow = {
  mounted(element) {
    element.style.overflowY = 'hidden'
    element.style.resize = 'none'
    element.addEventListener('input', handleInput)
    resize(element)

    // At this point v-model hasn't filled the value in yet (directive hooks
    // run before it) and the surrounding layout may not be final either, so
    // the first measurement is of an empty/narrow field. Re-measure once
    // it has settled, and again whenever the width changes (wrapping changes
    // the needed height).
    Promise.resolve().then(() => resize(element))
    if (typeof ResizeObserver !== 'undefined') {
      // Always fires once right after observe(), then only on real width
      // changes (height changes come from resize() itself — ignore those).
      let lastWidth = null
      const observer = new ResizeObserver(() => {
        if (element.clientWidth === lastWidth) return
        lastWidth = element.clientWidth
        resize(element)
      })
      observer.observe(element)
      observers.set(element, observer)
    }
  },
  updated(element) {
    resize(element)
  },
  beforeUnmount(element) {
    element.removeEventListener('input', handleInput)
    observers.get(element)?.disconnect()
    observers.delete(element)
  },
}
