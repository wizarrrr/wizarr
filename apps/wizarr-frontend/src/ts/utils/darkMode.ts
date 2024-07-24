const DARKMODE = "dark" as const;
const LIGHTMODE = "light" as const;
const SYSTEMMODE = "system" as const;

type THEME = typeof DARKMODE | typeof LIGHTMODE | typeof SYSTEMMODE;

const getTheme = (theme: THEME = SYSTEMMODE): Omit<THEME, "system"> => {
    const systemPrefence = window.matchMedia("(prefers-color-scheme: dark)").matches ? DARKMODE : LIGHTMODE;

    if (theme === SYSTEMMODE) {
        return systemPrefence;
    }
    return theme;
};

const watchTheme = (e: MediaQueryListEvent) => {
    // Add event listener for system preference change
    if (e.matches) {
        // Set the theme to dark
        document.documentElement.classList.add(DARKMODE);
        document.documentElement.classList.remove(LIGHTMODE);
    } else {
        // Set the theme to light
        document.documentElement.classList.add(LIGHTMODE);
        document.documentElement.classList.remove(DARKMODE);
    }
};

const updateTheme = (THEME: THEME): void => {
    switch (THEME) {
        case DARKMODE:
            // Set the theme to dark
            document.documentElement.classList.add(DARKMODE);
            // Remove event listener for system preference change
            window.matchMedia("(prefers-color-scheme: dark)").removeEventListener("change", watchTheme);
            break;
        case LIGHTMODE:
            // Set the theme to light
            document.documentElement.classList.remove(DARKMODE);
            // Remove event listener for system preference change
            window.matchMedia("(prefers-color-scheme: dark)").removeEventListener("change", watchTheme);
            break;
        case SYSTEMMODE:
            // Get the system preference and set the theme to it
            const systemPrefence = window.matchMedia("(prefers-color-scheme: dark)").matches ? DARKMODE : LIGHTMODE;
            document.documentElement.classList.add(systemPrefence);
            document.documentElement.classList.remove(systemPrefence === DARKMODE ? LIGHTMODE : DARKMODE);

            // Add event listener for system preference change
            window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", watchTheme);
            break;
        default:
            // Set the theme to dark
            document.documentElement.classList.add(DARKMODE);
            break;
    }
};

export { getTheme, updateTheme, DARKMODE, LIGHTMODE, SYSTEMMODE };
export type { THEME };
