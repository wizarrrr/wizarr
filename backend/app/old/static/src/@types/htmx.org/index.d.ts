declare module 'htmx.org' {

    /**
     * A string used in `querySelector` and / or `querySelectorAll`
     */
    interface htmx {
        /**
         * This method adds a class to the given element or first matched selector.
         *
         * See: {@link https://htmx.org/api/#addClass}
         *
         * @example
         * // add the class 'myClass' to the element with the id 'demo'
         * htmx.addClass(htmx.find('#demo'), 'myClass');
         */
        addClass(elt: HTMLElement, className: string): undefined,

        /**
         * Issues an htmx-style AJAX request
         *
         * See: {@link https://htmx.org/api/#ajax}
         *
         * @example
         * // issue a GET to /example and put the response HTML into #myDiv
         * htmx.ajax('GET', '/example', '#myDiv')
         */
        ajax(
            verb: string,
            path: string,
            context?: null | string | HTMLElement | {
                source?: any
                event?: any
                handler?: any
                target?: any
                values?: any
                headers?: any
            }): void,

        /**
         * Finds the closest matching element in the given elements parentage, inclusive of the element
         *
         * See: {@link https://htmx.org/api/#closest}
         *
         * @example
         * // find the closest enclosing div of the element with the id 'demo'
         * htmx.closest(htmx.find('#demo'), 'div');
         */
        closest(elt: HTMLElement, className: string): HTMLElement | void,

        /**
         * A property holding the configuration htmx uses at runtime.
         * Note that using a meta tag is the preferred mechanism for setting these properties.
         *
         * See: {@link https://htmx.org/api/#config}
         */
        config: {
            /** Array of strings: the attributes to settle during the settling phase */
            attributesToSettle: Array<string>,
            /** the default delay between completing the content swap and settling attributes **/
            defaultSettleDelay: number,
            /** The default delay between receiving a response from the server and doing the swap **/
            defaultSwapDelay: number,
            /** The default swap style to use if {@link https://htmx.org/attributes/hx-swap hx-swap} is omitted */
            defaultSwapStyle: "none" | "innerHTML" | "outerHTML" | "afterbegin" | "beforebegin" | "beforeend" | "afterend",
            /** The number of pages to keep in localStorage for history support **/
            historyCacheSize: number,
            /** hether or not to use history **/
            historyEnabled: boolean,
            /** If true, htmx will inject a small amount of CSS into the page to make indicators invisible unless the htmx-indicator class is present **/
            includeIndicatorStyles: boolean,
            /** The class to place on indicators when a request is in flight **/
            indicatorClass: string,
            /** The class to place on triggering elements when a request is in flight **/
            requestClass: string,
            /** The class to place on target elements when htmx is in the settling phase **/
            settlingClass: string,
            /** The class to place on target elements when htmx is in the swapping phase **/
            swappingClass: string,
            /** Allows the use of eval-like functionality in htmx, to enable hx-vars, trigger conditions & script tag evaluation. Can be set to false for CSP compatibility **/
            allowEval: boolean,
            /** Use HTML template tags for parsing content from the server. This allows you to use Out of Band content when returning things like table rows, but it is not IE11 compatible. **/
            useTemplateFragments: boolean,
            /** Allow cross-site Access-Control requests using credentials such as cookies, authorization headers or TLS client certificates **/
            withCredentials: boolean,
            /** The default implementation of getWebSocketReconnectDelay for reconnecting after unexpected connection loss by the event code Abnormal Closure, Service Restart or Try Again Later **/
            wsReconnectDelay: "full-jitter" | Function,

            refreshOnHistoryMiss: boolean,
            disableSelector: string,
        }

        /**
         * A property used to create new {@link https://htmx.org/docs/#sse Server Sent Event sources}. This can be updated to provide custom SSE setup.
         *
         * See: {@link https://htmx.org/api/#createEventSource}
         *
         * @example
         * // override SSE event sources to not use credentials
         * htmx.createEventSource = function(url) {
         *   return new EventSource(url, {withCredentials:false});
         * };
         */
        createEventSource: (url: string) => EventSource,

        /**
         * A property used to create new {@link https://htmx.org/docs/#websockets WebSocket}. This can be updated to provide custom WebSocket setup.
         *
         * See: {@link https://htmx.org/api/#createWebSocket}
         *
         * @example
         * // override WebSocket to use a specific protocol
         * htmx.createWebSocket = function(url) {
         *   return new WebSocket(url, ['wss']);
         * };
         */
        createWebSocket: (url: string) => WebSocket,

        /**
         * Defines a new htmx {@link https://htmx.org/extensions extension}.
         *
         * See: {@link https://htmx.org/api/#defineExtension}
         *
         * @example
         * // defines a silly extension that just logs the name of all events triggered
         * htmx.defineExtension("silly", {
         *   onEvent : function(name, evt) {
         *     console.log("Event " + name + " was triggered!")
         *   }
         * });
         */
        defineExtension(name: string, ext: any): void,

        /**
         * Finds an element matching the selector
         *
         * See: {@link https://htmx.org/api/#find}
         *
         * @example
         * // find div with id my-div
         * let div = htmx.find("#my-div")
         *
         * // find div with id another-div within that div
         * let anotherDiv = htmx.find(div, "#another-div")
         */
        find(selector: string): HTMLElement | null,
        find(elt: HTMLElement, selector: string): HTMLElement | null,

        /**
         * Finds all elements matching the selector
         *
         * See: {@link https://htmx.org/api/#findAll}
         *
         * @example
         * // find all divs
         * let allDivs = htmx.find("div")
         *
         * // find all paragraphs within a given div
         * let allParagraphsInMyDiv = htmx.find(htmx.find("#my-div"), "p")
         */
        findAll(selector: string): NodeList,
        findAll(elt: HTMLElement, selector: string): NodeList,

        /**
         * Log all htmx events, useful for debugging.
         *
         * See: {@link https://htmx.org/api/#logAll}
         *
         * @example
         * htmx.logAll();
         */
        logAll(): void,

        /**
         * Log all htmx events, useful for debugging.
         *
         * See: {@link https://htmx.org/api/#logAll}
         *
         * @example
         * htmx.logger = function(elt, event, data) {
         *   if(console) {
         *     console.log("INFO:", event, elt, data);
         *   }
         * }
         */
        logger: (elt: HTMLElement, event: Event, data: any) => void,

        /**
         * Removes an event listener from an element
         *
         * See: {@link https://htmx.org/api/#off}
         *
         * @example
         * // remove this click listener from the body
         * htmx.off("click", myEventListener1);
         * // remove this click listener from the given div
         * htmx.off("#my-div", "click", myEventListener2)
         */
        off(eventName: string, listener: EventListener): EventListener,
        off(target: string | HTMLElement, eventName: string, listener: EventListener): EventListener,

        /**
         * Adds an event listener to an element
         *
         * See: {@link https://htmx.org/api/#off}
         *
         * @example
         * // add a click listener to the body
         * let myEventListener1 = htmx.on("click", function(evt){ console.log(evt); });
         * // add a click listener to the given div
         * let myEventListener2 = htmx.on("#my-div", "click", function(evt){ console.log(evt); });
         */
        on(eventName: string, listener: EventListener): EventListener,
        on(target: string | HTMLElement, eventName: string, listener: EventListener): EventListener,

        /**
         * Adds a callback for the htmx:load event. This can be used to process new content, for example initializing the content with a javascript library
         *
         * See: {@link https://htmx.org/api/#onLoad}
         *
         * @example
         * htmx.onLoad(function(elt){
         *   MyLibrary.init(elt);
         * })
         */
        onLoad(callback: (elt: HTMLElement) => void): EventListener,

        /**
         * Parses an interval string consistent with the way htmx does.
         * Useful for plugins that have timing-related attributes.
         * Caution: Accepts an int followed by either `s` or `ms`. All other values use `parseFloat`
         *
         * See: {@link https://htmx.org/api/#parseInterval}
         *
         * @example
         * // returns 3000
         * htmx.parseInterval("3s");
         *
         * // returns 3
         * htmx.parseInterval("3m");
         */
        parseInterval(string: string): number,

        /**
         * Processes new content, enabling htmx behavior.
         * This can be useful if you have content that is added to the DOM
         * outside of the normal htmx request cycle but still want htmx attributes to work.
         *
         * See: {@link https://htmx.org/api/#process}
         *
         * @example
         * document.body.innerHTML = "<div hx-get='/example'>Get it!</div>"
         * // process the newly added content
         * htmx.process(document.body);
         */
        process(elt: HTMLElement): undefined

        /**
         * Removes an element from the DOM
         *
         * See: {@link https://htmx.org/api/#remove}
         *
         * @example
         * // removes my-div from the DOM
         * htmx.remove(htmx.find("#my-div"));
         */
        remove(elt: HTMLElement): undefined,

        /**
         * Removes a class from the given element
         *
         * See: {@link https://htmx.org/api/#removeClass}
         *
         * @example
         * // removes .myClass from my-div
         * htmx.removeClass(htmx.find("#my-div"), "myClass");
         */
        removeClass(elt: HTMLElement, className: string): undefined,

        /**
         * Removes the given extension from htmx
         *
         * See: {@link https://htmx.org/api/#removeExtension}
         *
         * @example
         * htmx.removeExtension("my-extension");
         */
        removeExtension(name: string): undefined,

        /**
         * Takes the given class from its siblings, so that among its siblings, only the given element will have the class.
         *
         * See: {@link https://htmx.org/api/#takeClass}
         *
         * @example
         * // takes the selected class from tab2's siblings
         * htmx.takeClass(htmx.find("#tab2"), "selected");
         */
        takeClass(elt: HTMLElement, className: string): undefined,

        /**
         * Toggles the given class on an element
         *
         * See: {@link https://htmx.org/api/#toggleClass}
         *
         * @example
         * // toggles the selected class on tab2
         * htmx.toggleClass(htmx.find("#tab2"), "selected");
         */
        toggleClass(elt: HTMLElement, className: string): undefined,

        /**
         * Toggles the given class on an element
         *
         * See: {@link https://htmx.org/api/#toggleClass}
         *
         * @example
         * // triggers the myEvent event on #tab2 with the answer 42
         * htmx.trigger(htmx.find("#tab2"), "myEvent", {answer:42});
         */
        trigger(elt: HTMLElement, name: string, details: any): any,

        /**
         * Returns the input values that would resolve for a given element via the htmx value resolution mechanism
         *
         * See: {@link https://htmx.org/api/#values}
         *
         * @example
         * // gets the values associated with this form
         * let values = htmx.values(htmx.find("#myForm"));
         */
        values(elt: HTMLElement, requestType?: string): object,
    }

    const htmx: htmx;
    export = htmx;
}