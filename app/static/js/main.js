// TOGGLE BUTTONS
function toggleEventListeners() {
    const toggles = document.querySelectorAll(".switch");

    toggles.forEach((toggle) => {
        const checkbox = toggle.querySelector("input[type=checkbox]");
        const slider = toggle.querySelector(".slider");

        slider.addEventListener("click", function () {
            checkbox.checked = !checkbox.checked;
        });
    });
}

function closeModal(that) {
    that.closest("#modal").remove()
}

async function scanLibraries() {

    // let settings = document.getElementById("settings");
    // settings.classList.add('animate__shakeX');

    console.log(document.getElementById("server_type").value)

    if (document.getElementById("server_type").value == "jellyfin") {

        let container = document.getElementById("libraries");

        while (container.hasChildNodes()) {
            container.removeChild(container.lastChild);
        }

        let jellyfin_url = document.getElementById("server_url").value;

        //enocde the url
        let jellyfin_url_encoded = encodeURIComponent(jellyfin_url);

        let jellyfin_api_key = document.getElementById("server_api_key").value;
        let url = "/jf-scan?jellyfin_url=" + jellyfin_url_encoded + "&jellyfin_api_key=" + jellyfin_api_key;

        let i = 0;

        let error = () => {
            let error_message = document.createElement("p");
            error_message.innerHTML = "Error: Please Check Your Jellyfin URL and Token";
            error_message.className = "mt-2 text-sm text-red-600 dark:text-red-500";
            container.appendChild(error_message);
            document.getElementById('settings').classList.add('animate__shakeX');
        }

        let response = await fetch(url, { method: "POST" }).catch(error);
        let data = await response.json();

        for (let [key, value] of Object.entries(data)) {
            i = i + 1;
            let checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.name = "library_" + i;
            checkbox.className =
                "w-4 h-4 text-blue-600 bg-gray-100 rounded border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600";
            checkbox.value = value;
            let label = document.createElement("label");
            label.for = "library_" + i;
            label.className = "ml-2 text-sm text-gray-600 dark:text-gray-400";
            label.innerHTML = key;

            let structure = document.createElement("div");
            structure.className = "flex items-center mb-4";
            container.appendChild(structure);
            container.appendChild(checkbox);
            container.appendChild(label);

            let library_count_helper = document.getElementById("library_count");
            library_count_helper.value = i;
        }

        let createHiddenElement = (name, value) => {
            let hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name = name;
            hidden.value = value;
            container.parentElement.appendChild(hidden);
        }

        createHiddenElement("server_type", "jellyfin");
        createHiddenElement("server_url", jellyfin_url);
        createHiddenElement("server_api_key", jellyfin_api_key);
    }


    if (document.getElementById("server_type").value == "plex") {

        let container = document.getElementById("libraries");
        while (container.hasChildNodes()) {
            container.removeChild(container.lastChild);
        }
        let plex_url = document.getElementById("server_url").value;
        let plex_token = document.getElementById("api_key").value;

        //encode the url
        plex_url = encodeURIComponent(plex_url);
        let url = "/scan?plex_url=" + plex_url + "&plex_token=" + plex_token;

        let error = () => {
            let error_message = document.createElement("p");
            error_message.innerHTML = "Error: Please Check Your Server URL and Token";
            error_message.className = "mt-2 text-sm text-red-600 dark:text-red-500";
            container.appendChild(error_message);
            document.getElementById('settings').classList.add('animate__shakeX');
        }


        const response = await fetch(url, { method: "POST" }).catch(error);
        const data = await response.json()

        for (let i = 0; i < data.length; i++) {
            let checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.name = "library_" + i;
            checkbox.className =
                "w-4 h-4 text-blue-600 bg-gray-100 rounded border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600";
            checkbox.value = data[i];
            let label = document.createElement("label");
            label.for = "library_" + i;
            label.className = "ml-2 text-sm text-gray-600 dark:text-gray-400";
            label.innerHTML = data[i];

            let structure = document.createElement("div");
            structure.className = "flex items-center mb-4";
            container.appendChild(structure);
            container.appendChild(checkbox);
            container.appendChild(label);

            let library_count_helper = document.getElementById("library_count");
            library_count_helper.value = i;
        }
    }
}

function handleRequestTypeChange() {
    const selectInput = document.getElementById("request_type");

    const urlInput = document.getElementById("request_url");
    const apiInput = document.getElementById("request_api_key");

    const urlDiv = urlInput.parentElement;
    const apiDiv = apiInput.parentElement;

    function selectChanged() {
        urlDiv.style.display = selectInput.children[0].selected ? "none" : "block";
        apiDiv.style.display = selectInput.children[0].selected ? "none" : "block";

        if (!selectInput.children[0].selected) {
            inputChanged();
        }
    }

    function inputChanged() {
        apiDiv.style.display = urlInput.value !== "" ? "block" : "none";
    }

    selectInput.addEventListener("change", selectChanged);
    urlInput.addEventListener("input", inputChanged);

    selectChanged();
}

function navbarDefault() {
    try {
        let navbarContainer = document.getElementById('navbar-default');

        let pageSwap = () => {
            let currentPage = "/partials" + window.location.pathname;
            currentPage = (currentPage.includes('/partials/admin/settings')) ? '/partials/admin/settings' : currentPage;
            let currentPageButton = navbarContainer.querySelector('[hx-get="' + currentPage + '"]');

            navbarContainer.querySelectorAll('button').forEach(function (button) {
                button.removeAttribute('aria-current');
            });

            if (currentPageButton) {
                currentPageButton.setAttribute('aria-current', 'page');
            }
        }

        navbarContainer.addEventListener('click', function (event) {
            if (event.target.tagName === 'BUTTON') {
                let hxGet = event.target.getAttribute('hx-get');
                hxGet = hxGet.replace('/partials/admin/', '')
                history.pushState(null, null, '/admin/' + hxGet);
            }

            pageSwap();
        });

        pageSwap();
    } catch (error) {
        console.error(error);
    }
}

function navbarSettings() {
    try {
        let navbarContainer = document.querySelector('#navbar-settings');

        let pageSwap = () => {
            let currentPage = "/partials" + window.location.pathname;
            currentPage = (currentPage === '/partials/admin/settings') ? '/partials/admin/settings/general' : currentPage;
            let currentPageButton = navbarContainer.querySelector('[hx-get="' + currentPage + '"]');

            navbarContainer.querySelectorAll('button').forEach(function (button) {
                button.removeAttribute('aria-current');
            });

            if (currentPageButton) {
                currentPageButton.setAttribute('aria-current', 'page');
            }
        }

        navbarContainer.addEventListener('click', function (event) {
            if (event.target.tagName === 'BUTTON') {
                let hxGet = event.target.getAttribute('hx-get');
                hxGet = hxGet.replace('/partials/admin/', '')
                history.pushState(null, null, '/admin/' + hxGet);
            }

            pageSwap();
        });

        pageSwap();
    } catch (error) {
        console.error(error);
    }
}
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

// htmx:afterSwap is fired when HTMX swaps content
document.addEventListener("htmx:afterSwap", function (data) {
    let requestPath = data.detail.pathInfo.requestPath;

    // These will be called every time the page is swapped
    toggleEventListeners();

    // Use requestPath to determine which page is being loaded and run the appropriate code
    if (requestPath === "/partials/admin/settings/requests") {
        handleRequestTypeChange();
    }

    if (requestPath === "/partials/admin/settings") {
        navbarSettings();
    }
});

// htmx:load is fired when HTMX loads content
document.addEventListener("htmx:load", function (data) {
    let requestPath = document.location.pathname;

    // These will be called every time the page is loaded
    toggleEventListeners();

    // Use requestPath to determine which page is being loaded and run the appropriate code
    if (requestPath === "/admin/settings/requests") {
        handleRequestTypeChange();
    }

    if (requestPath.includes("/admin/settings")) {
        navbarSettings();
    }
});

// When the page is loaded, run the appropriate code
document.addEventListener("DOMContentLoaded", function () {
    navbarDefault();
});