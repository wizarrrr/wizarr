import Cookie from 'js-cookie';
import { infoToast } from './CustomToastify';

let loadSSE = () => {
    if (Cookie.get('csrf_access_token')) {
        let source = new window.EventSource("/api/stream");

        // On error log the error
        source.addEventListener("error", () => {
            source.close();
        });

        window.unloadSSE = () => {
            source.close();
        };

        // if source is redirected log the new url
        source.addEventListener("data", (e: any) => {
            infoToast(e.data);
        });
    }
};

export default loadSSE;