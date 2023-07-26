import './scss/style.scss';
import './ts/AddToDom';
import './ts/carousel';
import './ts/dark-mode';
import './ts/navbar';
import './ts/toggle-menu';
import './ts/api';
import './ts/utils';

import htmx from 'htmx.org';
import Cookie from 'js-cookie';

import { infoToast } from './ts/CustomToastify';

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


function konamiCode() {
    const konamiCode = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];;
    let konamiIndex = 0;

    document.addEventListener('keydown', function (event) {
        if (event.key === konamiCode[konamiIndex]) {
            konamiIndex++;
            if (konamiIndex === konamiCode.length) {
                // Konami code detected
                console.log('Konami code detected');
                window.open('https://www.youtube.com/watch?v=dQw4w9WgXcQ', '_blank');
                konamiIndex = 0;
            }
        } else {
            konamiIndex = 0;
        }
    });
}

konamiCode();