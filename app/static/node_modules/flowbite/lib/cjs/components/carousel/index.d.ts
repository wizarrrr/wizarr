import type { CarouselOptions, CarouselItem, IndicatorItem, RotationItems } from './types';
import { CarouselInterface } from './interface';
declare class Carousel implements CarouselInterface {
    _items: CarouselItem[];
    _indicators: IndicatorItem[];
    _activeItem: CarouselItem;
    _intervalDuration: number;
    _intervalInstance: number;
    _options: CarouselOptions;
    constructor(items?: CarouselItem[], options?: CarouselOptions);
    /**
     * initialize carousel and items based on active one
     */
    _init(): void;
    getItem(position: number): CarouselItem;
    /**
     * Slide to the element based on id
     * @param {*} position
     */
    slideTo(position: number): void;
    /**
     * Based on the currently active item it will go to the next position
     */
    next(): void;
    /**
     * Based on the currently active item it will go to the previous position
     */
    prev(): void;
    /**
     * This method applies the transform classes based on the left, middle, and right rotation carousel items
     * @param {*} rotationItems
     */
    _rotate(rotationItems: RotationItems): void;
    /**
     * Set an interval to cycle through the carousel items
     */
    cycle(): void;
    /**
     * Clears the cycling interval
     */
    pause(): void;
    /**
     * Get the currently active item
     */
    _getActiveItem(): CarouselItem;
    /**
     * Set the currently active item and data attribute
     * @param {*} position
     */
    _setActiveItem(item: CarouselItem): void;
}
export declare function initCarousels(): void;
export default Carousel;
//# sourceMappingURL=index.d.ts.map