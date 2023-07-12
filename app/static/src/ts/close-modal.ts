function closeModal(that: Element) {
    const modal = that.closest("#modal");
    
    if (!modal) {
        throw new Error("Missing modal element");
    }

    modal.classList.add("animate__fadeOut");
    modal.addEventListener("animationend", () => {
        modal.remove();
    }, { once: true });
}

window.closeModal = closeModal;