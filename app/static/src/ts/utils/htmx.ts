import htmx from 'htmx.org';

import { errorToast } from './customToastify';

htmx.on('htmx:responseError', (event: any) => {
    if (event.detail.xhr.status === 404) {
        // if response data is json parseable
        if (event.detail.xhr.response) {
            try {
                const response = JSON.parse(event.detail.xhr.response);
                // if response data has a message
                if (response.message) {
                    // show the message
                    errorToast(response.message);
                }
            } catch (error) {
                // if response data is not json parseable
                // show the response data
                errorToast(event.detail.error);
            }
        }
    }
});