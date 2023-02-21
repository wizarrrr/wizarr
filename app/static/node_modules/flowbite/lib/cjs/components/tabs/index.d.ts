import type { TabItem, TabsOptions } from './types';
import { TabsInterface } from './interface';
declare class Tabs implements TabsInterface {
    _items: TabItem[];
    _activeTab: TabItem;
    _options: TabsOptions;
    constructor(items?: TabItem[], options?: TabsOptions);
    _init(): void;
    getActiveTab(): TabItem;
    _setActiveTab(tab: TabItem): void;
    getTab(id: string): TabItem;
    show(id: string, forceShow?: boolean): void;
}
export declare function initTabs(): void;
export default Tabs;
//# sourceMappingURL=index.d.ts.map