import htmx from "htmx.org";
import { initFlowbite } from '../../node_modules/flowbite/lib/esm/index';
import CustomToast from "./CustomToastify";
//import loadSSE from "./SSEListener";
import ScanLibraries from "./ScanLibraries";

const modules = [ScanLibraries, CustomToast, /*loadSSE*/];

modules.forEach((module) => {
    window[module.name] = module;
});

htmx.onLoad(() => {
    initFlowbite();
    // loadSSE();
});