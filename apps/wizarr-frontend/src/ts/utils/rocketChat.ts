import mitt from 'mitt';

class RocketChat {
    // Declare variables for the class
    private widget: HTMLElement = document.createElement('div');
    private iframe: HTMLIFrameElement = document.createElement('iframe');
    private hookQueue: any[] = [];
    private isReady = false;
    private smallScreen = false;
    private scrollPosition: number = 0;
    private widget_height: number = 0;
    private popup: Window | null = null;

    // Declare the current page
    private currentPage = {
        href: null as string | null,
        title: null as string | null,
    };

    // Declare the valid callbacks
    public validCallbacks = [
        'chat-maximized',
        'chat-minimized',
        'chat-started',
        'chat-ended',
        'pre-chat-form-submit',
        'offline-form-submit',
        'show-widget',
        'hide-widget',
        'assign-agent',
        'agent-status-change',
        'queue-position-change',
        'no-agent-online',
    ];

    // Declare the mitt event emitter
    private callbacks = mitt();

    // Declare the Widget Size Constants
    private WIDGET_OPEN_WIDTH = 365;
    private WIDGET_OPEN_HEIGHT = 525;
    private WIDGET_MINIMIZED_WIDTH = 54;
    private WIDGET_MINIMIZED_HEIGHT = 54;
    private WIDGET_MARGIN = 16;

    // Declare the config
    private config = {
        url: 'https://chat.wizarr.dev/livechat',
        theme: {
            title: 'Wizarr Support',
            color: '#fc425d',
            offlineTitle: 'Leave a message',
            offlineColor: '#666666',
        },
    };

    constructor(url: string, config?: any) {
        if (!url) throw new Error('Missing required parameter: url');

        this.config.url = url;

        this.createWidget(url);
        this.attachMessageListener();
        this.trackNavigation();

        this.initialize({ config, ...this.config });
    }

    initialize(params: any) {
        for (const method in params) {
            if (!params.hasOwnProperty(method)) {
                continue;
            }

            this.log('WizarrChat: ', method, params[method]);

            switch (method) {
                case 'customField':
                    const { key, value, overwrite } = params[method];
                    this.setCustomField(key, value, overwrite);
                    continue;
                case 'setCustomFields':
                    if (!Array.isArray(params[method])) {
                        console.log(
                            'Error: Invalid parameters. Value must be an array of objects',
                        );
                        continue;
                    }
                    params[method].forEach(
                        (data: {
                            key: string;
                            value: string;
                            overwrite: boolean;
                        }) => {
                            const { key, value, overwrite } = data;
                            this.setCustomField(key, value, overwrite);
                        },
                    );
                    continue;
                case 'theme':
                    this.setTheme(params[method]);
                    continue;
                case 'department':
                    this.setDepartment(params[method]);
                    continue;
                case 'businessUnit': {
                    this.setBusinessUnit(params[method]);
                    continue;
                }
                case 'guestToken':
                    this.setGuestToken(params[method]);
                    continue;
                case 'guestName':
                    this.setGuestName(params[method]);
                    continue;
                case 'guestEmail':
                    this.setGuestEmail(params[method]);
                    continue;
                case 'registerGuest':
                    this.registerGuest(params[method]);
                    continue;
                case 'language':
                    this.setLanguage(params[method]);
                    continue;
                case 'agent':
                    this.setAgent(params[method]);
                    continue;
                default:
                    continue;
            }
        }
    }

    log =
        process.env.NODE_ENV === 'development'
            ? (...args: any) =>
                  window.console.log(
                      '%cwidget%c',
                      'color: red',
                      'color: initial',
                      ...args,
                  )
            : () => {};

    createWidget(url: string) {
        this.widget.className = 'rocketchat-widget';
        this.widget.style.position = 'fixed';
        this.widget.style.width = `${
            this.WIDGET_MARGIN +
            this.WIDGET_MINIMIZED_WIDTH +
            this.WIDGET_MARGIN
        }px`;
        this.widget.style.height = `${
            this.WIDGET_MARGIN +
            this.WIDGET_MINIMIZED_HEIGHT +
            this.WIDGET_MARGIN
        }px`;
        this.widget.style.maxHeight = '100vh';
        this.widget.style.bottom = '0';
        this.widget.style.right = '0';
        this.widget.style.zIndex = '12345';
        this.widget.dataset.state = 'closed';

        const container = document.createElement('div');
        container.className = 'rocketchat-container';
        container.style.width = '100%';
        container.style.height = '100%';

        this.iframe.id = 'rocketchat-iframe';
        this.iframe.src = url;
        this.iframe.style.width = '100%';
        this.iframe.style.height = '100%';
        this.iframe.style.border = 'none';
        this.iframe.style.backgroundColor = 'transparent';

        container.appendChild(this.iframe);
        this.widget.appendChild(container);
        document.body.appendChild(this.widget);

        const handleMediaQueryTest = (event: Partial<MediaQueryListEvent>) => {
            if (!this.widget) return;

            this.smallScreen = event.matches ?? false;
            this.updateWidgetStyle(this.widget.dataset.state === 'opened');
            this.callHook('setExpanded', this.smallScreen);
        };

        const mediaQueryList = window.matchMedia(
            'screen and (max-device-width: 480px)',
        );
        mediaQueryList.addEventListener('change', handleMediaQueryTest);
        handleMediaQueryTest(mediaQueryList);
    }

    openWidget() {
        if (this.widget.dataset.state === 'opened') return;

        this.widget_height = this.WIDGET_OPEN_HEIGHT;
        this.updateWidgetStyle(true);
        this.widget.dataset.state = 'opened';
        this.iframe.focus();
        this.emitCallback('chat-maximized');
    }

    resizeWidget(height: number) {
        this.widget_height = height;
        this.updateWidgetStyle(true);
        this.widget.dataset.state = 'triggered';
    }

    closeWidget() {
        if (this.widget.dataset.state === 'closed') {
            return;
        }

        this.updateWidgetStyle(false);
        this.widget.dataset.state = 'closed';
        this.emitCallback('chat-minimized');
    }

    updateWidgetStyle(isOpened: boolean) {
        if (this.smallScreen && isOpened) {
            this.scrollPosition = document.documentElement.scrollTop;
            document.body.classList.add('rc-livechat-mobile-full-screen');
        } else {
            document.body.classList.remove('rc-livechat-mobile-full-screen');
            if (this.smallScreen) {
                document.documentElement.scrollTop = this.scrollPosition;
            }
        }

        if (isOpened) {
            this.widget.style.left = this.smallScreen ? '0' : 'auto';

            /**
             * If we use widget.style.height = smallScreen ? '100vh' : ...
             * In above case some browser's viewport height is not rendered correctly
             * so, as 100vh will resolve to 100% of the current viewport height,
             * so fixed it to 100% avoiding problem for some browsers. Similar resolution
             * for widget.style.width
             */

            this.widget.style.height = this.smallScreen
                ? '100%'
                : `${
                      this.WIDGET_MARGIN +
                      this.widget_height +
                      this.WIDGET_MARGIN +
                      this.WIDGET_MINIMIZED_HEIGHT
                  }px`;
            this.widget.style.width = this.smallScreen
                ? '100%'
                : `${
                      this.WIDGET_MARGIN +
                      this.WIDGET_OPEN_WIDTH +
                      this.WIDGET_MARGIN
                  }px`;
        } else {
            this.widget.style.left = 'auto';
            this.widget.style.width = `${
                this.WIDGET_MARGIN +
                this.WIDGET_MINIMIZED_WIDTH +
                this.WIDGET_MARGIN
            }px`;
            this.widget.style.height = `${
                this.WIDGET_MARGIN +
                this.WIDGET_MINIMIZED_HEIGHT +
                this.WIDGET_MARGIN
            }px`;
        }
    }

    ready() {
        this.isReady = true;
        if (this.hookQueue.length > 0) {
            this.hookQueue.forEach((hookParams) => {
                this.callHook.apply(this, hookParams);
            });
            this.hookQueue = [];
        }
    }

    minimizeWindow() {
        this.closeWidget();
    }

    restoreWindow() {
        if (this.popup && this.popup.closed !== true) {
            this.popup.close();
            this.popup = null;
        }
        this.openWidget();
    }

    openPopout() {
        this.closeWidget();
        this.popup = window.open(
            `${this.config.url}${
                this.config.url.lastIndexOf('?') > -1 ? '&' : '?'
            }mode=popout`,
            'livechat-popout',
            `width=${this.WIDGET_OPEN_WIDTH}, height=${this.widget_height}, toolbars=no`,
        );
        this.popup!.focus();
    }

    removeWidget() {
        document.body.removeChild(this.widget);
    }

    callback(eventName: string, data?: any) {
        this.emitCallback(eventName, data);
    }

    showWidget() {
        this.iframe.style.display = 'initial';
        this.emitCallback('show-widget');
    }

    hideWidget() {
        this.iframe.style.display = 'none';
        this.emitCallback('hide-widget');
    }

    resetDocumentStyle() {
        document.body.classList.remove('rc-livechat-mobile-full-screen');
    }

    setFullScreenDocumentMobile() {
        this.smallScreen &&
            document.body.classList.add('rc-livechat-mobile-full-screen');
    }

    attachMessageListener() {
        window.addEventListener(
            'message',
            (msg) => {
                if (
                    typeof msg.data === 'object' &&
                    msg.data.src !== undefined &&
                    msg.data.src === 'rocketchat'
                ) {
                    // @ts-ignore
                    if (
                        this[msg.data.fn] !== undefined &&
                        typeof this[msg.data.fn] === 'function'
                    ) {
                        const args = [].concat(msg.data.args || []);
                        this.log(`api.${msg.data.fn}`, ...args);
                        // @ts-ignore
                        this[msg.data.fn].apply(this, args);
                    }
                }
            },
            false,
        );
    }

    trackNavigation() {
        setInterval(() => {
            if (document.location.href !== this.currentPage.href) {
                this.pageVisited('url');
                this.currentPage.href = document.location.href;
            }

            if (document.title !== this.currentPage.title) {
                this.pageVisited('title');
                this.currentPage.title = document.title;
            }
        }, 800);
    }

    registerCallback(eventName: string, fn: (data: any) => void) {
        if (this.validCallbacks.indexOf(eventName) === -1) {
            return false;
        }

        return this.callbacks.on(eventName, fn);
    }

    emitCallback(eventName: string, data?: any) {
        if (typeof data !== 'undefined') {
            this.callbacks.emit(eventName, data);
        } else {
            this.callbacks.emit(eventName);
        }
    }

    callHook(action: string, params?: any) {
        if (!this.isReady) return this.hookQueue.push([action, params]);

        const data = {
            src: 'rocketchat',
            fn: action,
            args: params,
        };

        if (!this.iframe) console.error('Iframe not found');
        if (!this.iframe.contentWindow)
            console.error('Iframe content window not found');

        if (!this.iframe?.contentWindow) return;

        this.iframe.contentWindow.postMessage(data, this.config.url);
    }

    pageVisited(change: string) {
        this.callHook('pageVisited', {
            change,
            location: JSON.parse(JSON.stringify(document.location)),
            title: document.title,
        });
    }

    setCustomField(key: string, value: string, overwrite: boolean) {
        if (typeof overwrite === 'undefined') {
            overwrite = true;
        }
        this.callHook('setCustomField', [key, value, overwrite]);
    }

    setTheme(theme: string) {
        this.callHook('setTheme', theme);
    }

    setDepartment(department: string) {
        this.callHook('setDepartment', department);
    }

    setBusinessUnit(businessUnit: string) {
        this.callHook('setBusinessUnit', businessUnit);
    }

    clearBusinessUnit() {
        this.callHook('clearBusinessUnit');
    }

    setGuestToken(token: string) {
        this.callHook('setGuestToken', token);
    }

    setGuestName(name: string) {
        this.callHook('setGuestName', name);
    }

    setGuestEmail(email: string) {
        this.callHook('setGuestEmail', email);
    }

    registerGuest(guest: string) {
        this.callHook('registerGuest', guest);
    }

    clearDepartment() {
        this.callHook('clearDepartment');
    }

    setAgent(agent: string) {
        this.callHook('setAgent', agent);
    }

    setLanguage(language: string) {
        this.callHook('setLanguage', language);
    }

    showWidgets() {
        this.callHook('showWidget');
    }

    hideWidgets() {
        this.callHook('hideWidget');
    }

    maximizeWidget() {
        this.callHook('maximizeWidget');
    }

    minimizeWidget() {
        this.callHook('minimizeWidget');
    }

    // Callbacks
    onChatMaximized(fn: (data: any) => void) {
        this.registerCallback('chat-maximized', fn);
    }

    onChatMinimized(fn: (data: any) => void) {
        this.registerCallback('chat-minimized', fn);
    }

    onChatStarted(fn: (data: any) => void) {
        this.registerCallback('chat-started', fn);
    }

    onChatEnded(fn: (data: any) => void) {
        this.registerCallback('chat-ended', fn);
    }

    onPrechatFormSubmit(fn: (data: any) => void) {
        this.registerCallback('pre-chat-form-submit', fn);
    }

    onOfflineFormSubmit(fn: (data: any) => void) {
        this.registerCallback('offline-form-submit', fn);
    }

    onWidgetShown(fn: (data: any) => void) {
        this.registerCallback('show-widget', fn);
    }

    onWidgetHidden(fn: (data: any) => void) {
        this.registerCallback('hide-widget', fn);
    }

    onAssignAgent(fn: (data: any) => void) {
        this.registerCallback('assign-agent', fn);
    }

    onAgentStatusChange(fn: (data: any) => void) {
        this.registerCallback('agent-status-change', fn);
    }

    onQueuePositionChange(fn: (data: any) => void) {
        this.registerCallback('queue-position-change', fn);
    }

    onServiceOffline(fn: (data: any) => void) {
        this.registerCallback('no-agent-online', fn);
    }
}

export default RocketChat;
