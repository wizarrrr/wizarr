import debounce from './deboundFunction';

function searchSettings() {
    // Get the search input value
    const searchValue = document.getElementById("settings-search")?.querySelector("input")?.value;

    // If the search value is empty, show all of the categories and buttons
    if (!searchValue) {
        document.getElementById("settings-content")?.querySelectorAll(".settings-section")?.forEach((category) => {
            // Show the category
            category.classList.remove("hidden");

            // Show all of the buttons inside the category
            category.querySelectorAll("button")?.forEach((button) => {
                button.classList.remove("hidden");
            });
        });
        return;
    }

    // Get all of the settings buttons
    const settingsButtons = document.getElementById("settings-content")?.querySelectorAll("button");

    // Loop through all of the settings buttons
    settingsButtons?.forEach((button) => {

        // Check the button exists
        if (!button) return;

        const title_div = button.querySelector(".settings-item-title") as HTMLDivElement;
        const description_div = button.querySelector(".settings-item-description") as HTMLDivElement;

        // Check the title and description divs exist
        if (!title_div || !description_div) return;

        // Get the title and description
        const title = title_div.innerText;
        const description = description_div.innerText;

        // If the title or description contains the search value, show the button otherwise hide it
        if (title.toLowerCase().includes(searchValue.toLowerCase()) || description.toLowerCase().includes(searchValue.toLowerCase())) {
            button.classList.remove("hidden");
        } else {
            button.classList.add("hidden");
        }
    });

    // If all buttons are hidden inside a category, hide the category
    document.getElementById("settings-content")?.querySelectorAll(".settings-section")?.forEach((category) => {
        const buttons = category.querySelectorAll("button");
        const hiddenButtons = category.querySelectorAll("button.hidden");
        if (buttons.length == hiddenButtons.length) {
            category.classList.add("hidden");
        } else {
            category.classList.remove("hidden");
        }
    });
}

// Bind the searchSettings function to the search input's onkeyup event
document.getElementById("settings-search")?.querySelector("input")?.addEventListener("keyup", debounce(searchSettings, 250, false));
