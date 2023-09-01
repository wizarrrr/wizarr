import addToWindow from './addToWindow';
import debounce from './deboundFunction';

function searchSettings(searchValue: string) {
    // If the search value is empty, show all of the categories and buttons
    if (!searchValue) {
        document.getElementById("settings-content")?.querySelectorAll(".settings-section")?.forEach((category) => {
            // Show the category
            category.classList.remove("hidden");
            category.removeAttribute("hidden");

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
            category.setAttribute("hidden", "")
        } else {
            category.classList.remove("hidden");
            category.removeAttribute("hidden");
        }
    });

    // If all categories are hidden, show the no results message
    const categories = document.getElementById("settings-content")?.querySelectorAll(".settings-section");
    const hiddenCategories = document.getElementById("settings-content")?.querySelectorAll(".settings-section.hidden");
    if (categories?.length == hiddenCategories?.length) {
        document.getElementById("settings-no-results")?.classList.remove("hidden");
    } else {
        document.getElementById("settings-no-results")?.classList.add("hidden");
    }
}

addToWindow(['utils', 'settingsSearch'], debounce(searchSettings, 150, false));