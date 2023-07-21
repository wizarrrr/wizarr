import htmx from "htmx.org";
import { initFlowbite } from '../../node_modules/flowbite/lib/esm/index';
import CustomToast from "./CustomToastify";
//import loadSSE from "./SSEListener";
import { Carousel } from "flowbite";
import closeModal from "./CloseModal";
import PlexAuth from "./PlexAuth";
import ScanLibraries from "./ScanLibraries";
import startTinyMCE from "./TinyMCE";
import { closeAllMenus, toggleMenu } from "./toggle-menu";

const modules = [ScanLibraries, CustomToast, /*loadSSE,*/ PlexAuth, Carousel, startTinyMCE, closeModal, closeAllMenus, toggleMenu];

modules.forEach((module) => {
    window[module.name] = module;
});

window.toggleMenu = toggleMenu;

htmx.onLoad(() => {
    initFlowbite();
    // loadSSE();
});

