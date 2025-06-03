import type { ModalOptions } from './types';
import { ModalInterface } from './interface';
declare class Modal implements ModalInterface {
    _targetEl: HTMLElement | null;
    _options: ModalOptions;
    _isHidden: boolean;
    _backdropEl: HTMLElement | null;
    _clickOutsideEventListener: EventListenerOrEventListenerObject;
    _keydownEventListener: EventListenerOrEventListenerObject;
    constructor(targetEl?: HTMLElement | null, options?: ModalOptions);
    _init(): void;
    _createBackdrop(): void;
    _destroyBackdropEl(): void;
    _setupModalCloseEventListeners(): void;
    _removeModalCloseEventListeners(): void;
    _handleOutsideClick(target: EventTarget): void;
    _getPlacementClasses(): string[];
    toggle(): void;
    show(): void;
    hide(): void;
    isVisible(): boolean;
    isHidden(): boolean;
}
export declare function initModals(): void;
export default Modal;
//# sourceMappingURL=index.d.ts.map