function darkMode() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
    const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');


    const toggleColorTheme = () => {
        const colorTheme = localStorage.getItem('color-theme');

        if (colorTheme === 'light') {
            document.documentElement.classList.add('dark');
            localStorage.setItem('color-theme', 'dark');
            if (themeToggleDarkIcon && themeToggleLightIcon) {
                themeToggleDarkIcon.classList.remove('hidden');
                themeToggleLightIcon.classList.add('hidden');
            }
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('color-theme', 'light');
            if (themeToggleDarkIcon && themeToggleLightIcon) {
                themeToggleDarkIcon.classList.add('hidden');
                themeToggleLightIcon.classList.remove('hidden');
            }
        }
    };

    if (localStorage.getItem('color-theme') === 'dark' || (!localStorage.getItem('color-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        if (themeToggleDarkIcon && themeToggleLightIcon) {
            themeToggleLightIcon.classList.add('hidden');
            themeToggleDarkIcon.classList.remove('hidden');
        }
        document.documentElement.classList.add('dark');
    } else {
        if (themeToggleDarkIcon && themeToggleLightIcon) {
            themeToggleLightIcon.classList.remove('hidden');
            themeToggleDarkIcon.classList.add('hidden');
        }
        document.documentElement.classList.remove('dark');
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleColorTheme);
    }

    window.toggleColorTheme = toggleColorTheme;
}

function isDarkMode() {
    return localStorage.getItem('color-theme') === 'dark' || (!localStorage.getItem('color-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
}

window.isDarkMode = isDarkMode;


document.addEventListener('DOMContentLoaded', () => {
    darkMode();
});