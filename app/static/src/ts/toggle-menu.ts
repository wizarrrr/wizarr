// <td class="p-5 pr-8 hidden md:block text-right">
// <div class="flex col justify-end">
//     <button class="focus:ring-2 p-2 rounded-md focus:outline-none" onclick="window.toggleMenu(this)" role="button" aria-label="option">
//         <i class="transition-all fa-solid fa-ellipsis"></i>
//     </button>
//     <div class="menu flex row overflow-hidden transition-all items-center space-x-2 ml-2" style="max-width: 0px;">
//         <button hx-get="" hx-target="" hx-trigger="click" class="bg-gray-600 focus:outline-none text-white font-medium rounded-lg px-4 py-2.5 text-sm dark:bg-gray-600">
//             {{ _("Edit") }}
//         </button>
//         <button hx-get="" hx-target="" hx-trigger="click" class="bg-primary focus:outline-none text-white font-medium rounded-lg px-4 py-2.5 text-sm dark:bg-primary">
//             {{ _("Delete") }}
//         </button>
//     </div>
// </div>
// </td>

function closeAllMenus() {
    let menus = document.getElementsByClassName("menu")

    for (let i = 0; i < menus.length; i++) {
        let menu = menus[i] as HTMLDivElement
        menu.style.maxWidth = "0px"
        menu.parentElement?.children[0].children[0].classList.remove("fa-rotate-90")
    }
}

function toggleMenu(menuButton: Element) {

    if (!menuButton?.parentElement) {
        throw new Error("Missing menu button or parent element")
    }
    
    closeAllMenus()

    let icon = menuButton.children[0]
    let menu = menuButton.parentElement.children[1] as HTMLDivElement

    if (!icon || !menu) {
        throw new Error("Missing icon or menu element")
    }

    if (menu.style.maxWidth == "0px") {
        menu.style.maxWidth = "1000px"
        icon.classList.add("fa-rotate-90")
    } else {
        menu.style.maxWidth = "0px"
        icon.classList.remove("fa-rotate-90")
    }

    try {
        document.addEventListener("click", function (event: Event) {
            if (!menuButton.contains(event.target as Node)) {
                menu.style.maxWidth = "0px"
                menu.parentElement?.children[0].children[0].classList.remove("fa-rotate-90")
                document.removeEventListener("click", this as any)
            }
        });
    } catch (error) {
        console.log(error)
    }
}

window.toggleMenu = toggleMenu;
window.closeAllMenus = closeAllMenus;
