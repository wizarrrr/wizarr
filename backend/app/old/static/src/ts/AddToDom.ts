import htmx from 'htmx.org';

import { initFlowbite } from '../../node_modules/flowbite/lib/esm/index';

htmx.onLoad(() => {
    initFlowbite();
});

