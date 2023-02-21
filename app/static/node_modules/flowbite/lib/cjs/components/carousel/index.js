"use strict";
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.initCarousels = void 0;
var Default = {
    defaultPosition: 0,
    indicators: {
        items: [],
        activeClasses: 'bg-white dark:bg-gray-800',
        inactiveClasses: 'bg-white/50 dark:bg-gray-800/50 hover:bg-white dark:hover:bg-gray-800',
    },
    interval: 3000,
    onNext: function () { },
    onPrev: function () { },
    onChange: function () { },
};
var Carousel = /** @class */ (function () {
    function Carousel(items, options) {
        if (items === void 0) { items = []; }
        if (options === void 0) { options = Default; }
        this._items = items;
        this._options = __assign(__assign(__assign({}, Default), options), { indicators: __assign(__assign({}, Default.indicators), options.indicators) });
        this._activeItem = this.getItem(this._options.defaultPosition);
        this._indicators = this._options.indicators.items;
        this._intervalDuration = this._options.interval;
        this._intervalInstance = null;
        this._init();
    }
    /**
     * initialize carousel and items based on active one
     */
    Carousel.prototype._init = function () {
        var _this = this;
        this._items.map(function (item) {
            item.el.classList.add('absolute', 'inset-0', 'transition-transform', 'transform');
        });
        // if no active item is set then first position is default
        if (this._getActiveItem()) {
            this.slideTo(this._getActiveItem().position);
        }
        else {
            this.slideTo(0);
        }
        this._indicators.map(function (indicator, position) {
            indicator.el.addEventListener('click', function () {
                _this.slideTo(position);
            });
        });
    };
    Carousel.prototype.getItem = function (position) {
        return this._items[position];
    };
    /**
     * Slide to the element based on id
     * @param {*} position
     */
    Carousel.prototype.slideTo = function (position) {
        var nextItem = this._items[position];
        var rotationItems = {
            left: nextItem.position === 0
                ? this._items[this._items.length - 1]
                : this._items[nextItem.position - 1],
            middle: nextItem,
            right: nextItem.position === this._items.length - 1
                ? this._items[0]
                : this._items[nextItem.position + 1],
        };
        this._rotate(rotationItems);
        this._setActiveItem(nextItem);
        if (this._intervalInstance) {
            this.pause();
            this.cycle();
        }
        this._options.onChange(this);
    };
    /**
     * Based on the currently active item it will go to the next position
     */
    Carousel.prototype.next = function () {
        var activeItem = this._getActiveItem();
        var nextItem = null;
        // check if last item
        if (activeItem.position === this._items.length - 1) {
            nextItem = this._items[0];
        }
        else {
            nextItem = this._items[activeItem.position + 1];
        }
        this.slideTo(nextItem.position);
        // callback function
        this._options.onNext(this);
    };
    /**
     * Based on the currently active item it will go to the previous position
     */
    Carousel.prototype.prev = function () {
        var activeItem = this._getActiveItem();
        var prevItem = null;
        // check if first item
        if (activeItem.position === 0) {
            prevItem = this._items[this._items.length - 1];
        }
        else {
            prevItem = this._items[activeItem.position - 1];
        }
        this.slideTo(prevItem.position);
        // callback function
        this._options.onPrev(this);
    };
    /**
     * This method applies the transform classes based on the left, middle, and right rotation carousel items
     * @param {*} rotationItems
     */
    Carousel.prototype._rotate = function (rotationItems) {
        // reset
        this._items.map(function (item) {
            item.el.classList.add('hidden');
        });
        // left item (previously active)
        rotationItems.left.el.classList.remove('-translate-x-full', 'translate-x-full', 'translate-x-0', 'hidden', 'z-20');
        rotationItems.left.el.classList.add('-translate-x-full', 'z-10');
        // currently active item
        rotationItems.middle.el.classList.remove('-translate-x-full', 'translate-x-full', 'translate-x-0', 'hidden', 'z-10');
        rotationItems.middle.el.classList.add('translate-x-0', 'z-20');
        // right item (upcoming active)
        rotationItems.right.el.classList.remove('-translate-x-full', 'translate-x-full', 'translate-x-0', 'hidden', 'z-20');
        rotationItems.right.el.classList.add('translate-x-full', 'z-10');
    };
    /**
     * Set an interval to cycle through the carousel items
     */
    Carousel.prototype.cycle = function () {
        var _this = this;
        if (typeof window !== 'undefined') {
            this._intervalInstance = window.setInterval(function () {
                _this.next();
            }, this._intervalDuration);
        }
    };
    /**
     * Clears the cycling interval
     */
    Carousel.prototype.pause = function () {
        clearInterval(this._intervalInstance);
    };
    /**
     * Get the currently active item
     */
    Carousel.prototype._getActiveItem = function () {
        return this._activeItem;
    };
    /**
     * Set the currently active item and data attribute
     * @param {*} position
     */
    Carousel.prototype._setActiveItem = function (item) {
        var _a, _b;
        var _this = this;
        this._activeItem = item;
        var position = item.position;
        // update the indicators if available
        if (this._indicators.length) {
            this._indicators.map(function (indicator) {
                var _a, _b;
                indicator.el.setAttribute('aria-current', 'false');
                (_a = indicator.el.classList).remove.apply(_a, _this._options.indicators.activeClasses.split(' '));
                (_b = indicator.el.classList).add.apply(_b, _this._options.indicators.inactiveClasses.split(' '));
            });
            (_a = this._indicators[position].el.classList).add.apply(_a, this._options.indicators.activeClasses.split(' '));
            (_b = this._indicators[position].el.classList).remove.apply(_b, this._options.indicators.inactiveClasses.split(' '));
            this._indicators[position].el.setAttribute('aria-current', 'true');
        }
    };
    return Carousel;
}());
if (typeof window !== 'undefined') {
    window.Carousel = Carousel;
}
function initCarousels() {
    document.querySelectorAll('[data-carousel]').forEach(function ($carouselEl) {
        var interval = $carouselEl.getAttribute('data-carousel-interval');
        var slide = $carouselEl.getAttribute('data-carousel') === 'slide'
            ? true
            : false;
        var items = [];
        var defaultPosition = 0;
        if ($carouselEl.querySelectorAll('[data-carousel-item]').length) {
            Array.from($carouselEl.querySelectorAll('[data-carousel-item]')).map(function ($carouselItemEl, position) {
                items.push({
                    position: position,
                    el: $carouselItemEl,
                });
                if ($carouselItemEl.getAttribute('data-carousel-item') ===
                    'active') {
                    defaultPosition = position;
                }
            });
        }
        var indicators = [];
        if ($carouselEl.querySelectorAll('[data-carousel-slide-to]').length) {
            Array.from($carouselEl.querySelectorAll('[data-carousel-slide-to]')).map(function ($indicatorEl) {
                indicators.push({
                    position: parseInt($indicatorEl.getAttribute('data-carousel-slide-to')),
                    el: $indicatorEl,
                });
            });
        }
        var carousel = new Carousel(items, {
            defaultPosition: defaultPosition,
            indicators: {
                items: indicators,
            },
            interval: interval ? interval : Default.interval,
        });
        if (slide) {
            carousel.cycle();
        }
        // check for controls
        var carouselNextEl = $carouselEl.querySelector('[data-carousel-next]');
        var carouselPrevEl = $carouselEl.querySelector('[data-carousel-prev]');
        if (carouselNextEl) {
            carouselNextEl.addEventListener('click', function () {
                carousel.next();
            });
        }
        if (carouselPrevEl) {
            carouselPrevEl.addEventListener('click', function () {
                carousel.prev();
            });
        }
    });
}
exports.initCarousels = initCarousels;
exports.default = Carousel;
//# sourceMappingURL=index.js.map