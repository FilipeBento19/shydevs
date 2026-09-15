function resize(element) {
  element.style.height = 'auto'
  element.style.height = `${element.scrollHeight}px`
}

function handleInput(event) {
  resize(event.currentTarget)
}

export const vAutogrow = {
  mounted(element) {
    element.style.overflowY = 'hidden'
    element.style.resize = 'none'
    element.addEventListener('input', handleInput)
    resize(element)
  },
  updated(element) {
    resize(element)
  },
  beforeUnmount(element) {
    element.removeEventListener('input', handleInput)
  },
}
