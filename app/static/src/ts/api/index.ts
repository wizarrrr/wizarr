import './users';
import './settings';
import './invitations';
import './mfa';
import './utilities';

import axios from 'axios';
import cookie from 'js-cookie';
import toast from 'toastify-js';

// ((value: V) => V | Promise<V>) | null
function resp<V>(resp: any) {
    if (resp.data.message) {
        toast({ duration: 3000, gravity: 'bottom', position: 'right', className: 'toast', stopOnFocus: true, style: { background: '#28a745', }, text: resp.data.message }).showToast();
    }

    return resp;
}

// ((error: any) => any) | null
function error(error: any) {
    if (error.response.data.message) {
        toast({ duration: 3000, gravity: 'bottom', position: 'right', className: 'toast', stopOnFocus: true, style: { background: '#dc3545', }, text: error.response.data.message }).showToast();
    }

    return Promise.reject(error);
}

// @ts-ignore
axios.defaults.headers.common["X-CSRF-TOKEN"] = cookie.get('csrf_access_token');
axios.interceptors.response.use(resp, error);