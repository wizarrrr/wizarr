type DARK = "dark";
type LIGHT = "light";
type SYSTEM = "system";

declare type THEME = DARK | LIGHT | SYSTEM;

const DARK_VALUE: DARK = "dark";
const LIGHT_VALUE: LIGHT = "light";
const SYSTEM_VALUE: SYSTEM = "system";

const getTheme = (theme?: THEME): THEME => {
    const colorTheme = theme ?? (SYSTEM_VALUE as THEME);
    const systemPrefence = window.matchMedia("(prefers-color-scheme: dark)").matches ? DARK_VALUE : LIGHT_VALUE;

    if (colorTheme === DARK_VALUE) {
        return DARK_VALUE;
    } else if (colorTheme === LIGHT_VALUE) {
        return LIGHT_VALUE;
    } else if (colorTheme === SYSTEM_VALUE) {
        return systemPrefence;
    }

    return DARK_VALUE;
};

const watchTheme = (e: MediaQueryListEvent) => {
    // Add event listener for system preference change
    if (e.matches) {
        // Set the theme to dark
        document.documentElement.classList.add(DARK_VALUE);
        document.documentElement.classList.remove(LIGHT_VALUE);
    } else {
        // Set the theme to light
        document.documentElement.classList.add(LIGHT_VALUE);
        document.documentElement.classList.remove(DARK_VALUE);
    }
};

const updateTheme = (THEME: THEME): void => {
    switch (THEME) {
        case DARK_VALUE:
            // Set the theme to dark
            document.documentElement.classList.add(DARK_VALUE);
            // Remove event listener for system preference change
            window.matchMedia("(prefers-color-scheme: dark)").removeEventListener("change", watchTheme);
            break;
        case LIGHT_VALUE:
            // Set the theme to light
            document.documentElement.classList.remove(DARK_VALUE);
            // Remove event listener for system preference change
            window.matchMedia("(prefers-color-scheme: dark)").removeEventListener("change", watchTheme);
            break;
        case SYSTEM_VALUE:
            // Get the system preference and set the theme to it
            const systemPrefence = window.matchMedia("(prefers-color-scheme: dark)").matches ? DARK_VALUE : LIGHT_VALUE;
            document.documentElement.classList.add(systemPrefence);
            document.documentElement.classList.remove(systemPrefence === DARK_VALUE ? LIGHT_VALUE : DARK_VALUE);

            // Add event listener for system preference change
            window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", watchTheme);
            break;
        default:
            // Set the theme to dark
            document.documentElement.classList.add(DARK_VALUE);
            break;
    }
};

export { getTheme, updateTheme, DARK_VALUE, LIGHT_VALUE, SYSTEM_VALUE };
export type { THEME, DARK, LIGHT, SYSTEM };
