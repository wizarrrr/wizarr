import type { CollapseOptions } from './types';
import { CollapseInterface } from './interface';
declare class Collapse implements CollapseInterface {
    _targetEl: HTMLElement | null;
    _triggerEl: HTMLElement | null;
    _options: CollapseOptions;
    _visible: boolean;
    constructor(targetEl?: HTMLElement | null, triggerEl?: HTMLElement | null, options?: CollapseOptions);
    _init(): void;
    collapse(): void;
    expand(): void;
    toggle(): void;
}
export declare function initCollapses(): void;
export default Collapse;
//# sourceMappingURL=index.d.ts.map