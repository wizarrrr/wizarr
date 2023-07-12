function toggleMenu(element: Element) {

    if (!element) {
        throw new Error("Missing element")
    }

    if (!element.parentElement) {
        throw new Error("Missing parent element")
    }

    let icon = element.children[0]
    let menu = element.parentElement.children[1] as HTMLDivElement

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

    document.addEventListener("click", function (event: Event) {
        if (!element.contains(event.target as Node)) {
            menu.style.maxWidth = "0px"
            icon.classList.remove("fa-rotate-90")
            document.removeEventListener("click", this as any)
        }
    });
}

window.toggleMenu = toggleMenu;