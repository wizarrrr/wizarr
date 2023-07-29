import addToWindow from './addToWindow';

type DARK_TYPE = 'dark'
type LIGHT_TYPE = 'light'
type SYSTEM_TYPE = 'system'

type MODE = DARK_TYPE | LIGHT_TYPE | SYSTEM_TYPE

const DARK: DARK_TYPE = 'dark'
const LIGHT: LIGHT_TYPE = 'light'
const SYSTEM: SYSTEM_TYPE = 'system'

const getMode = (): MODE => {
    const colorTheme = localStorage.getItem('color-theme') ?? SYSTEM as MODE

    if (colorTheme === DARK) {
        return DARK
    } else if (colorTheme === LIGHT) {
        return LIGHT
    } else {
        return SYSTEM
    }
}

const getTheme = (): MODE => {
    const colorTheme = localStorage.getItem('color-theme') ?? SYSTEM as MODE
    const systemPrefence = window.matchMedia('(prefers-color-scheme: dark)').matches ? DARK : LIGHT

    if (colorTheme === DARK) {
        return DARK
    } else if (colorTheme === LIGHT) {
        return LIGHT
    } else if (colorTheme === SYSTEM) {
        return systemPrefence
    }

    return DARK
}

const setIcon = (mode: MODE) => {
    const dark = document.querySelector('#theme-toggle-dark-icon')
    const light = document.querySelector('#theme-toggle-light-icon')
    const system = document.querySelector('#theme-toggle-system-icon')

    if (dark === null || light === null || system === null) return

    if (mode === DARK) {
        dark.classList.remove('hidden')
        light.classList.add('hidden')
        system.classList.add('hidden')
    } else if (mode === LIGHT) {
        dark.classList.add('hidden')
        light.classList.remove('hidden')
        system.classList.add('hidden')
    } else {
        dark.classList.add('hidden')
        light.classList.add('hidden')
        system.classList.remove('hidden')
    }
}

const setDark = () => {
    document.documentElement.classList.add('dark');
    localStorage.setItem('color-theme', 'dark');
    setIcon(LIGHT)
    document.dispatchEvent(new Event('theme-changed'))
}

const setLight = () => {
    document.documentElement.classList.remove('dark');
    localStorage.setItem('color-theme', 'light');
    setIcon(DARK)
    document.dispatchEvent(new Event('theme-changed'))
}

const setSystem = () => {
    const systemPrefence = window.matchMedia('(prefers-color-scheme: dark)').matches ? DARK : LIGHT
    localStorage.setItem('color-theme', 'system');
    setIcon(SYSTEM)

    if (systemPrefence === DARK) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }

    document.dispatchEvent(new Event('theme-changed'))
}

const toggleColorTheme = () => {
    const mode = getMode()

    if (mode === DARK) {
        setLight()
    } else if (mode === LIGHT) {
        setSystem()
    } else {
        setDark()
    }

    return getMode()
}

const init = () => {
    const mode = getMode()

    if (mode === DARK) {
        setDark()
    } else if (mode === LIGHT) {
        setLight()
    } else {
        setSystem()
    }
}

window.addEventListener('load', init)
document.querySelector('#theme-toggle')?.addEventListener('click', toggleColorTheme)

addToWindow(['utils', 'theme', 'toggleColorTheme'], toggleColorTheme)
addToWindow(['utils', 'theme', 'getMode'], getMode)
addToWindow(['utils', 'theme', 'getTheme'], getTheme)
addToWindow(['utils', 'theme', 'setDark'], setDark)
addToWindow(['utils', 'theme', 'setLight'], setLight)
addToWindow(['utils', 'theme', 'setSystem'], setSystem)

export { toggleColorTheme, getMode, setDark, setLight, getTheme, setSystem, DARK, LIGHT, SYSTEM, MODE }
