document.addEventListener('DOMContentLoaded', function() {
    /**
     * Initializes the theme based on user's saved preference or system preference
     * Checks localStorage for saved theme preference, falls back to system preference
     * Applies the appropriate theme class to the document
     */
    function initTheme() {
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    }

    /**
     * Toggles between light and dark themes
     * Updates the document's theme class, saves the preference to localStorage
     */
    function toggleTheme() {
        if (localStorage.getItem('color-theme') === 'light') {
            document.documentElement.classList.add('dark');
            localStorage.setItem('color-theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('color-theme', 'light');
        }
    }

    const themeToggleBtn = document.getElementById('theme-toggle');
    
    themeToggleBtn?.addEventListener('click', function() {
        toggleTheme();
    });

    initTheme();
});
