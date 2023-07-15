import CustomToast from "./CustomToastify";
import ScanLibraries from "./ScanLibraries";

const modules = [ScanLibraries, CustomToast];

modules.forEach((module) => {
    window[module.name] = module;
});
