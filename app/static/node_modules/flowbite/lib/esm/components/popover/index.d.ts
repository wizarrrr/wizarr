import type { Instance as PopperInstance } from '@popperjs/core';
import type { PopoverOptions } from './types';
import { PopoverInterface } from './interface';
declare class Popover implements PopoverInterface {
    _targetEl: HTMLElement;
    _triggerEl: HTMLElement;
    _options: PopoverOptions;
    _popperInstance: PopperInstance;
    _clickOutsideEventListener: EventListenerOrEventListenerObject;
    _visible: boolean;
    constructor(targetEl?: HTMLElement | null, triggerEl?: HTMLElement | null, options?: PopoverOptions);
    _init(): void;
    _setupEventListeners(): void;
    _createPopperInstance(): PopperInstance;
    _getTriggerEvents(): {
        showEvents: string[];
        hideEvents: string[];
    };
    _setupClickOutsideListener(): void;
    _removeClickOutsideListener(): void;
    _handleClickOutside(ev: Event, targetEl: HTMLElement): void;
    isVisible(): boolean;
    toggle(): void;
    show(): void;
    hide(): void;
}
export declare function initPopovers(): void;
export default Popover;
//# sourceMappingURL=index.d.ts.map