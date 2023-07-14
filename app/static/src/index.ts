import '@fortawesome/fontawesome-free/js/all.js';
import 'animate.css/animate.css';
import htmx from 'htmx.org';
import 'toastify-js/src/toastify.css';
import 'tw-elements/dist/js/tw-elements.es.min';
import './scss/style.scss';
import './ts/AddToDom';
import './ts/carousel';
import './ts/close-modal';
import './ts/dark-mode';
import './ts/navbar';
import './ts/toggle-menu';
import './ts/toggle-switches';

htmx.config.defaultSwapStyle = 'innerHTML';
window.htmx = htmx;

// If htmx swap gets 301/302 redirect, follow it instead of replacing the current page
htmx.on('htmx:afterSwap', (event: any) => {
    console.log(event.detail.xhr.status);
    if (event.detail.xhr.status >= 300 && event.detail.xhr.status < 400) {
        window.location.href = event.detail.xhr.responseURL;
    }
});