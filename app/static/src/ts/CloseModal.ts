function closeModal(that: Element) {
    const modal = that.closest("#modal");

    modal?.classList.add("animate__fadeOut");
    modal?.addEventListener("animationend", () => {
        modal?.remove();
    }, { once: true });
}

export default closeModal;