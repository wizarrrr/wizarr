
interface Window {
    darkMode: () => void;
    closeModal: (that: Element) => void;
    toggleSwitches: () => void;
    [key: string]: any;
}