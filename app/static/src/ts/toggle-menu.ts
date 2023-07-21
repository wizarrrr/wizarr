const closeAllMenus = () => {
    const menus = document.getElementsByClassName("menu");

    Array.from(menus).forEach((menu) => {
        const menuDiv = menu as HTMLDivElement;
        menuDiv.style.maxWidth = "0px";
        menuDiv.parentElement?.children[0].children[0].classList.remove("fa-rotate-90");
    });
};

const toggleMenu = (menuButton: Element) => {
    const parentElement = menuButton?.parentElement;

    if (!parentElement) {
        throw new Error("Missing menu button or parent element");
    }

    closeAllMenus();

    const icon = menuButton.children[0];
    const menu = parentElement.children[1] as HTMLDivElement;

    if (!icon || !menu) {
        throw new Error("Missing icon or menu element");
    }

    if (menu.style.maxWidth === "0px") {
        menu.style.maxWidth = "1000px";
        icon.classList.add("fa-rotate-90");
    } else {
        menu.style.maxWidth = "0px";
        icon.classList.remove("fa-rotate-90");
    }

    const clickHandler = (event: Event) => {
        if (!menuButton.contains(event.target as Node)) {
            menu.style.maxWidth = "0px";
            menu.parentElement?.children[0].children[0].classList.remove("fa-rotate-90");
            document.removeEventListener("click", clickHandler);
        }
    };

    document.addEventListener("click", clickHandler);
};

export { closeAllMenus, toggleMenu };
