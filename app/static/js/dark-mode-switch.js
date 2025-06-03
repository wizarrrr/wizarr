/**
 * Updates the theme toggle icons based on the current theme
 * @param {string} theme - The current theme ('dark' or 'light')
 */
function setThemeIcon(theme) {
    const darkIcon = document.getElementById('theme-toggle-dark-icon');
    const lightIcon = document.getElementById('theme-toggle-light-icon');
    if (theme === 'dark') {
        darkIcon.classList.remove('hidden');
        lightIcon.classList.add('hidden');
    } else {
        darkIcon.classList.add('hidden');
        lightIcon.classList.remove('hidden');
    }
}

/**
 * Initializes the theme based on user's saved preference or system preference
 * Checks localStorage for saved theme preference, falls back to system preference
 * Applies the appropriate theme class to the document and updates the theme icons
 */
function initTheme() {
    if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
        setThemeIcon('dark');
    } else {
        document.documentElement.classList.remove('dark');
        setThemeIcon('light');
    }
}

/**
 * Toggles between light and dark themes
 * Updates the document's theme class, saves the preference to localStorage,
 * and updates the theme toggle icons accordingly
 */
function toggleTheme() {
    if (localStorage.getItem('color-theme') === 'light') {
        document.documentElement.classList.add('dark');
        localStorage.setItem('color-theme', 'dark');
        setThemeIcon('dark');
    } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('color-theme', 'light');
        setThemeIcon('light');
    }
}
