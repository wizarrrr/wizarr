"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.initTooltips = exports.initTabs = exports.initPopovers = exports.initModals = exports.initDropdowns = exports.initDrawers = exports.initDismisses = exports.initDials = exports.initCollapses = exports.initCarousels = exports.initAccordions = exports.Tooltip = exports.Tabs = exports.Popover = exports.Modal = exports.Dropdown = exports.Drawer = exports.Dismiss = exports.Dial = exports.Collapse = exports.Carousel = exports.Accordion = void 0;
var events_1 = require("./dom/events");
var accordion_1 = require("./components/accordion");
var collapse_1 = require("./components/collapse");
var carousel_1 = require("./components/carousel");
var dismiss_1 = require("./components/dismiss");
var dropdown_1 = require("./components/dropdown");
var modal_1 = require("./components/modal");
var drawer_1 = require("./components/drawer");
var tabs_1 = require("./components/tabs");
var tooltip_1 = require("./components/tooltip");
var popover_1 = require("./components/popover");
var dial_1 = require("./components/dial");
// setup events for data attributes
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
// export all components
var accordion_2 = require("./components/accordion");
Object.defineProperty(exports, "Accordion", { enumerable: true, get: function () { return accordion_2.default; } });
var carousel_2 = require("./components/carousel");
Object.defineProperty(exports, "Carousel", { enumerable: true, get: function () { return carousel_2.default; } });
var collapse_2 = require("./components/collapse");
Object.defineProperty(exports, "Collapse", { enumerable: true, get: function () { return collapse_2.default; } });
var dial_2 = require("./components/dial");
Object.defineProperty(exports, "Dial", { enumerable: true, get: function () { return dial_2.default; } });
var dismiss_2 = require("./components/dismiss");
Object.defineProperty(exports, "Dismiss", { enumerable: true, get: function () { return dismiss_2.default; } });
var drawer_2 = require("./components/drawer");
Object.defineProperty(exports, "Drawer", { enumerable: true, get: function () { return drawer_2.default; } });
var dropdown_2 = require("./components/dropdown");
Object.defineProperty(exports, "Dropdown", { enumerable: true, get: function () { return dropdown_2.default; } });
var modal_2 = require("./components/modal");
Object.defineProperty(exports, "Modal", { enumerable: true, get: function () { return modal_2.default; } });
var popover_2 = require("./components/popover");
Object.defineProperty(exports, "Popover", { enumerable: true, get: function () { return popover_2.default; } });
var tabs_2 = require("./components/tabs");
Object.defineProperty(exports, "Tabs", { enumerable: true, get: function () { return tabs_2.default; } });
var tooltip_2 = require("./components/tooltip");
Object.defineProperty(exports, "Tooltip", { enumerable: true, get: function () { return tooltip_2.default; } });
// export all types
__exportStar(require("./components/accordion/types"), exports);
__exportStar(require("./components/carousel/types"), exports);
__exportStar(require("./components/collapse/types"), exports);
__exportStar(require("./components/dial/types"), exports);
__exportStar(require("./components/dismiss/types"), exports);
__exportStar(require("./components/drawer/types"), exports);
__exportStar(require("./components/dropdown/types"), exports);
__exportStar(require("./components/modal/types"), exports);
__exportStar(require("./components/popover/types"), exports);
__exportStar(require("./components/tabs/types"), exports);
__exportStar(require("./components/tooltip/types"), exports);
// export all interfaces
__exportStar(require("./components/accordion/interface"), exports);
__exportStar(require("./components/carousel/interface"), exports);
__exportStar(require("./components/collapse/interface"), exports);
__exportStar(require("./components/dial/interface"), exports);
__exportStar(require("./components/dismiss/interface"), exports);
__exportStar(require("./components/drawer/interface"), exports);
__exportStar(require("./components/dropdown/interface"), exports);
__exportStar(require("./components/modal/interface"), exports);
__exportStar(require("./components/popover/interface"), exports);
__exportStar(require("./components/tabs/interface"), exports);
__exportStar(require("./components/tooltip/interface"), exports);
// export init functions
var accordion_3 = require("./components/accordion");
Object.defineProperty(exports, "initAccordions", { enumerable: true, get: function () { return accordion_3.initAccordions; } });
var carousel_3 = require("./components/carousel");
Object.defineProperty(exports, "initCarousels", { enumerable: true, get: function () { return carousel_3.initCarousels; } });
var collapse_3 = require("./components/collapse");
Object.defineProperty(exports, "initCollapses", { enumerable: true, get: function () { return collapse_3.initCollapses; } });
var dial_3 = require("./components/dial");
Object.defineProperty(exports, "initDials", { enumerable: true, get: function () { return dial_3.initDials; } });
var dismiss_3 = require("./components/dismiss");
Object.defineProperty(exports, "initDismisses", { enumerable: true, get: function () { return dismiss_3.initDismisses; } });
var drawer_3 = require("./components/drawer");
Object.defineProperty(exports, "initDrawers", { enumerable: true, get: function () { return drawer_3.initDrawers; } });
var dropdown_3 = require("./components/dropdown");
Object.defineProperty(exports, "initDropdowns", { enumerable: true, get: function () { return dropdown_3.initDropdowns; } });
var modal_3 = require("./components/modal");
Object.defineProperty(exports, "initModals", { enumerable: true, get: function () { return modal_3.initModals; } });
var popover_3 = require("./components/popover");
Object.defineProperty(exports, "initPopovers", { enumerable: true, get: function () { return popover_3.initPopovers; } });
var tabs_3 = require("./components/tabs");
Object.defineProperty(exports, "initTabs", { enumerable: true, get: function () { return tabs_3.initTabs; } });
var tooltip_3 = require("./components/tooltip");
Object.defineProperty(exports, "initTooltips", { enumerable: true, get: function () { return tooltip_3.initTooltips; } });
//# sourceMappingURL=index.js.map