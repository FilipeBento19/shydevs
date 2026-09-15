import mascot from './assets/mascot.png'

export function mascotFaceStyle(size) {
  return {
    width: `${size}px`,
    height: `${size}px`,
    flex: 'none',
    borderRadius: '50%',
    backgroundColor: '#1c1c28',
    backgroundImage: `url(${mascot})`,
    backgroundSize: '260%',
    backgroundPosition: '48% 8%',
    backgroundRepeat: 'no-repeat',
  }
}

export function personAvatarStyle(person, size) {
  if (person && person.photo) {
    return {
      width: `${size}px`, height: `${size}px`, flex: 'none', borderRadius: '50%',
      backgroundImage: `url(${person.photo})`, backgroundSize: 'cover', backgroundPosition: 'center',
    }
  }
  return mascotFaceStyle(size)
}

export default mascotFaceStyle
export { mascot }
