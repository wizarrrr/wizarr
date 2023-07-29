import htmx from 'htmx.org';
import { ITerminalOptions, Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';

import addToWindow from './addToWindow';
import { getTheme, MODE } from './themeSelector';

const createTerminalTheme = (theme: MODE) => {
    const themeOptions: ITerminalOptions["theme"] = {};

    if (theme === 'dark') {
        themeOptions.background = '#00000000'
        themeOptions.foreground = '#fff';
        themeOptions.cursor = '#fff';
    } else {
        themeOptions.background = '#ffffff00'
        themeOptions.foreground = '#000';
        themeOptions.cursor = '#000';
    }

    return themeOptions;
}

const startLogTerminal = async (terminal: HTMLDivElement) => {
    const theme = getTheme();
    const themeOptions: ITerminalOptions["theme"] = createTerminalTheme(theme);

    const term = new Terminal({
        convertEol: true,
        fontFamily: `'Fira Mono', monospace`,
        fontSize: 15,
        theme: themeOptions,
    });

    document.addEventListener('theme-changed', () => {
        const theme = getTheme();
        const themeOptions: ITerminalOptions["theme"] = createTerminalTheme(theme);
        term.options.theme = themeOptions;
    });

    term.onData((data: string) => {
        if (data === '\r') {
            term.scrollToBottom();
        }
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    term.open(terminal);
    fitAddon.fit();

    const event = new EventSource('/api/logging/stream')
    event.onmessage = function (e) {
        term.writeln(e.data)
    }

    window.addEventListener('beforeunload', () => {
        event.close();
    });


    htmx.on('htmx:afterSwap', () => {
        event.close();
    });

    return term;
}

addToWindow(['utils', 'startLogTerminal'], startLogTerminal);