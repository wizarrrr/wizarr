import htmx from "htmx.org";
import { initFlowbite } from '../../node_modules/flowbite/lib/esm/index';
import CustomToast from "./CustomToastify";
//import loadSSE from "./SSEListener";
import { Carousel } from "flowbite";
import PlexAuth from "./PlexAuth";
import ScanLibraries from "./ScanLibraries";
import startTinyMCE from "./TinyMCE";

const modules = [ScanLibraries, CustomToast, /*loadSSE,*/ PlexAuth, Carousel, startTinyMCE];

modules.forEach((module) => {
    window[module.name] = module;
});

htmx.onLoad(() => {
    initFlowbite();
    // loadSSE();
});

