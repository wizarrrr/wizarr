import '@fortawesome/fontawesome-free/js/all.js';
import 'animate.css/animate.css';
import htmx from 'htmx.org';
import 'toastify-js/src/toastify.css';
import 'tw-elements/dist/js/tw-elements.es.min';
import './scss/style.scss';
import './ts/carousel';
import './ts/close-modal';
import './ts/dark-mode';
import './ts/nav-bar';
import './ts/toastify';
import './ts/toggle-menu';
import './ts/toggle-switches';

htmx.config.defaultSwapStyle = 'innerHTML';
window.htmx = htmx;
