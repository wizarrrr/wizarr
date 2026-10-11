/**
 * Show or hide the password in a field.
 *
 * A toggle is a <button data-password-toggle aria-controls="<field id>">
 * with two icons: [data-icon="show"] and [data-icon="hide"].
 * The templates make it with the password_toggle macro
 * (_partials/password_toggle.html). The listeners are on the document,
 * so that they also work for content that HTMX adds.
 */
(function () {
    function setVisible(button, visible) {
        const input = document.getElementById(button.getAttribute('aria-controls'));
        if (!input) return;

        input.type = visible ? 'text' : 'password';
        button.setAttribute('aria-pressed', String(visible));
        button.querySelector('[data-icon="show"]').classList.toggle('hidden', visible);
        button.querySelector('[data-icon="hide"]').classList.toggle('hidden', !visible);
    }

    document.addEventListener('click', function (event) {
        const button = event.target.closest('[data-password-toggle]');
        if (!button) return;

        setVisible(button, button.getAttribute('aria-pressed') !== 'true');
    });

    // Hide the passwords before the form sends them. Then the browser does
    // not keep a password as a text entry in its form history.
    document.addEventListener('submit', function (event) {
        event.target
            .querySelectorAll('[data-password-toggle][aria-pressed="true"]')
            .forEach(function (button) {
                setVisible(button, false);
            });
    });
})();
