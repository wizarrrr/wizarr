import '@fortawesome/fontawesome-free/js/all.js';
import 'animate.css/animate.css';
import htmx from 'htmx.org';
import Cookie from 'js-cookie';
import 'toastify-js/src/toastify.css';
import 'tw-elements/dist/js/tw-elements.es.min';
import './scss/style.scss';
import './ts/AddToDom';
import { infoToast } from './ts/CustomToastify';
import './ts/carousel';
import './ts/close-modal';
import './ts/dark-mode';
import './ts/navbar';
import './ts/toggle-menu';
import './ts/toggle-switches';

htmx.config.defaultSwapStyle = 'innerHTML';
window.htmx = htmx;

htmx.on('htmx:responseRedirect', (event: any) => {
    console.log(event);
});

window.getCookie = Cookie.get;
window.setCookie = Cookie.set;

const toast = new URLSearchParams(window.location.search).get('toast');
if (toast) setTimeout(() => infoToast(toast), 500);
if (toast) history.replaceState(null, '', window.location.pathname);