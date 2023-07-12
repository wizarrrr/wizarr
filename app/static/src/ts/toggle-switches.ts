import htmx from "htmx.org";

function toggleSwitches() {
    const toggles = document.querySelectorAll(".switch");

    toggles.forEach((toggle) => {
        const checkbox = toggle.querySelector("input[type=checkbox]") as HTMLInputElement;
        const slider = toggle.querySelector(".slider");

        if (!checkbox || !slider) {
            throw new Error("Missing checkbox or slider element");
        }

        slider.addEventListener("click", () => {
            checkbox.checked = !checkbox.checked;
        });
    });
}

htmx.on("htmx:afterSwap", () => {
    
});

htmx.on("htmx:load", () => {
    toggleSwitches();
});

window.toggleSwitches = toggleSwitches;