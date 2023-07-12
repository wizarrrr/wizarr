// @ts-nocheck
class Carousel {

    currentSlide = 0;

    defaults = {
        container: document.querySelector('.subpage-container'),
        items: document.querySelectorAll('.subpage'),
        navigation: {
            prevEl: document.querySelector('#prevBtn'),
            nextEl: document.querySelector('#nextBtn')
        },
        paths: null,
        events: {
            onSlideChange: () => { },
            onStart: () => { }
        },
        disabled: {}
    }

    constructor(defaults) {
        this.container = defaults.container;
        this.items = defaults.items;

        this.prevEl = defaults.navigation.prevEl;
        this.nextEl = defaults.navigation.nextEl;

        this.prevEl.disabled = true;
        this.prevEl.classList.add('disabled');

        this.paths = defaults.paths;
        this.disabled = defaults.disabled;

        this.events = defaults.events;
        this.events.onSlideChange = defaults.events.onSlideChange;
        this.events.onStart = defaults.events.onStart;

        this.items[this.currentSlide].classList.add('active');
        this.disableButtons();
        this.events.onStart(this.currentSlide);
    }

    prev() {
        if (this.currentSlide == 0) {
            return;
        }

        this.enableButtons();
        this.currentSlide = (this.currentSlide - 1 + this.items.length) % this.items.length;
        this.updateActivePage();
        this.updateCarousel();
        this.disableButtons();
    }

    next() {
        if (this.currentSlide == this.items.length - 1) {
            return;
        }

        this.enableButtons();
        this.currentSlide = (this.currentSlide + 1) % this.items.length;
        this.updateActivePage();
        this.updateCarousel();
        this.disableButtons();
    }

    enableButtons() {
        this.prevEl.disabled = false;
        this.nextEl.disabled = false;
        this.prevEl.classList.remove('disabled');
        this.nextEl.classList.remove('disabled');
    }

    disableButtons() {
        // If this.disabled has a value for the current slide, disable the buttons
        if (this.disabled[this.currentSlide]) {
            this.prevEl.disabled = this.disabled[this.currentSlide].prev || false;
            this.nextEl.disabled = this.disabled[this.currentSlide].next || false;
        }

        if (this.currentSlide == 0) {
            this.prevEl.disabled = true;
            this.prevEl.classList.add('disabled');
        }

        if (this.currentSlide == this.items.length - 1) {
            this.nextEl.disabled = true;
            this.nextEl.classList.add('disabled');
        }
    }

    updateCarousel() {
        const translateXValue = `-${this.currentSlide * 25}%`;
        this.container.style.transform = `translateX(${translateXValue})`;
        this.changePath();
    }

    updateActivePage() {
        this.events.onSlideChange(this.currentSlide);
        this.items.forEach((item, index) => {
            if (index == this.currentSlide) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    setSlide(slide, animated = true) {
        slide = parseInt(slide) - 1;

        if (slide < 0 || slide > this.items.length - 1) {
            return;
        }

        this.container.style.transition = animated ? 'transform 0.5s ease-in-out' : 'none';

        this.currentSlide = slide;
        this.updateActivePage();
        this.updateCarousel();
        this.enableButtons();
        this.disableButtons();

        this.container.style.transition = 'transform 0.5s ease-in-out';

        this.changePath();
    }

    changePath() {
        if (!this.paths) return;
        let path = this.paths[this.currentSlide];
        let currentPath = window.location.pathname;
        currentPath = currentPath.substring(0, currentPath.lastIndexOf('/'));
        currentPath += '/' + path;
        history.pushState(null, null, currentPath);
    }
}

window.Carousel = Carousel;