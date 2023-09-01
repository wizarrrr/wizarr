function handleNavar() {
    let defaultNavbar = document.getElementById('navbar-default');
    let settingsNavbar = document.getElementById('navbar-settings');
    let accountNavbar = document.getElementById('navbar-account');

    let currentPage = window.location.pathname;

    if (defaultNavbar) {
        let currentPageTrimmed = (currentPage.includes('/settings/')) ? "/admin/settings" : currentPage;
        let currentPageButton = defaultNavbar.querySelector('[hx-push-url="' + currentPageTrimmed + '"]');

        defaultNavbar.querySelectorAll('button').forEach(function (button) {
            button.removeAttribute('aria-current');
        });

        if (currentPageButton) {
            currentPageButton.setAttribute('aria-current', 'page');
        }
    }

    if (settingsNavbar) {
        let currentPageTrimmed = (currentPage.endsWith('/settings')) ? "/admin/settings/general" : currentPage;
        let currentPageButton = settingsNavbar.querySelector('[hx-push-url="' + currentPageTrimmed + '"]');

        settingsNavbar.querySelectorAll('button').forEach(function (button) {
            button.removeAttribute('aria-current');
        });

        if (currentPageButton) {
            currentPageButton.setAttribute('aria-current', 'page');
        }
    }

    if (accountNavbar) {
        let currentPageTrimmed = (currentPage.endsWith('/account')) ? "/account/general" : currentPage;
        let currentPageButton = accountNavbar.querySelector('[hx-push-url="' + currentPageTrimmed + '"]');

        accountNavbar.querySelectorAll('button').forEach(function (button) {
            button.removeAttribute('aria-current');
        });

        if (currentPageButton) {
            currentPageButton.setAttribute('aria-current', 'page');
        }
    }
}

document.addEventListener("htmx:pushedIntoHistory", handleNavar);
document.addEventListener("DOMContentLoaded", handleNavar);