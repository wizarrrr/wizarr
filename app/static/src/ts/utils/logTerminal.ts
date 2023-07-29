import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';

import addToWindow from './addToWindow';

const startLogTerminal = async (terminal: HTMLDivElement) => {
    const term = new Terminal({
        convertEol: true,
        fontFamily: `'Fira Mono', monospace`,
        fontSize: 15
    });

    // always keep the last line in view
    term.onData((data: string) => {
        if (data === '\r') {
            term.scrollToBottom();
        }
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    term.open(terminal);
    fitAddon.fit();

    return term;
}

addToWindow(['utils', 'startLogTerminal'], startLogTerminal);