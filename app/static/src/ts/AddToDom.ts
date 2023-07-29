//import loadSSE from "./SSEListener";
import { Carousel } from 'flowbite';
import htmx from 'htmx.org';

import { initFlowbite } from '../../node_modules/flowbite/lib/esm/index';
import closeModal from './CloseModal';
import CustomToast from './CustomToastify';
import PlexAuth from './PlexAuth';
import ScanLibraries from './ScanLibraries';
import { closeAllMenus, toggleMenu } from './toggle-menu';

const modules = [ScanLibraries, CustomToast, /*loadSSE,*/ PlexAuth, Carousel, closeModal, closeAllMenus, toggleMenu];

modules.forEach((module) => {
    window[module.name] = module;
});

window.toggleMenu = toggleMenu;

htmx.onLoad(() => {
    initFlowbite();
    // loadSSE();
});

