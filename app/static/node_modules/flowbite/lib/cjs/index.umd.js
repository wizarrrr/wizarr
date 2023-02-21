"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
require("./flowbite.css");
// core components
var accordion_1 = require("./components/accordion");
var carousel_1 = require("./components/carousel");
var collapse_1 = require("./components/collapse");
var dial_1 = require("./components/dial");
var dismiss_1 = require("./components/dismiss");
var drawer_1 = require("./components/drawer");
var dropdown_1 = require("./components/dropdown");
var modal_1 = require("./components/modal");
var popover_1 = require("./components/popover");
var tabs_1 = require("./components/tabs");
var tooltip_1 = require("./components/tooltip");
var events_1 = require("./dom/events");
var events = new events_1.default('load', [
    accordion_1.initAccordions,
    collapse_1.initCollapses,
    carousel_1.initCarousels,
    dismiss_1.initDismisses,
    dropdown_1.initDropdowns,
    modal_1.initModals,
    drawer_1.initDrawers,
    tabs_1.initTabs,
    tooltip_1.initTooltips,
    popover_1.initPopovers,
    dial_1.initDials,
]);
events.init();
exports.default = {
    Accordion: accordion_1.default,
    Carousel: carousel_1.default,
    Collapse: collapse_1.default,
    Dial: dial_1.default,
    Drawer: drawer_1.default,
    Dismiss: dismiss_1.default,
    Dropdown: dropdown_1.default,
    Modal: modal_1.default,
    Popover: popover_1.default,
    Tabs: tabs_1.default,
    Tooltip: tooltip_1.default,
    Events: events_1.default,
};
//# sourceMappingURL=index.umd.js.map