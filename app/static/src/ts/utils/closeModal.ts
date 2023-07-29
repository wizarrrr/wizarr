import addToWindow from './addToWindow';

function closeModal(that: Element) {
    const modal = that.closest("#modal");

    modal?.classList.add("animate__fadeOut");
    modal?.addEventListener("animationend", () => {
        modal?.remove();
    }, { once: true });
}

addToWindow(["utils", "closeModal"], closeModal);

export default closeModal;