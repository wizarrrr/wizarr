

// function initNavBars() {
//     const $defaultNavBar = document.getElementById('navbar-default');
//     const $defaultNavBarButton = document.getElementById('navbar-button');

//     if ($defaultNavBar || $defaultNavBarButton) {
//         const defaultCollapse: CollapseInterface = new Collapse($defaultNavBar, $defaultNavBarButton);
//         htmx.on('#navbar-button', 'click', defaultCollapse.toggle);
//     }

//     const $settingsNavBar = document.getElementById('navbar-settings');
//     const $settingsNavBarButton = document.getElementById('navbar-settings-button');

//     if ($settingsNavBar || $settingsNavBarButton) {
//         const settingsCollapse: CollapseInterface = new Collapse($settingsNavBar, $settingsNavBarButton);
//         htmx.on('#navbar-settings-button', 'click', settingsCollapse.toggle);
//     }
// }

// initNavBars();

// htmx.on('htmx:afterSettle', () => {
//     initNavBars();
// });