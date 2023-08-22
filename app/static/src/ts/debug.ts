import * as Sentry from '@sentry/browser';

/* Track page analytics, using Matomo. NO PERSONAL DATA IS COLLECTED. */
let _paq = window._paq = window._paq || [];
let _url = window.location.href.replace('https://', '').replace('http://', '');
_paq.push(["setDocumentTitle", _url]);
_paq.push(["setCookieDomain", location.host]);
_paq.push(['trackPageView']);
_paq.push(['enableLinkTracking']);
(function () {
    let u = "//analytics.gitcloud.co.uk/";
    _paq.push(['setTrackerUrl', u + 'matomo.php']);
    _paq.push(['setSiteId', '1']);
    let d = document, g = d.createElement('script'), s = d.getElementsByTagName('script')[0];
    g.async = true; g.src = u + 'matomo.js'; s.parentNode?.insertBefore(g, s);
})();

/* Function to collect feedback. ONLY COLLECTS NAME, EMAIL AND COMMENTS. DEFAULTS TO ANONYMOUS. */
function feedback() {
    const modal = document.createElement('div');
    modal.classList.add('fixed', 'flex', 'items-center', 'justify-center', 'w-full', 'h-full', 'top-0', 'left-0', 'z-50', 'overflow-auto', 'bg-gray-900', 'bg-opacity-50', 'dark:bg-gray-900', 'dark:bg-opacity-50');

    const modalContent = document.createElement('div');
    modalContent.classList.add('relative', 'w-full', 'max-w-2xl', 'max-h-full');

    const modalContentInner = document.createElement('div');
    modalContentInner.classList.add('relative', 'bg-white', 'rounded-lg', 'shadow', 'dark:bg-gray-700');

    const modalHeader = document.createElement('div');
    modalHeader.classList.add('flex', 'items-start', 'justify-between', 'p-4', 'border-b', 'rounded-t', 'dark:border-gray-600');

    const modalHeaderTitle = document.createElement('h3');
    modalHeaderTitle.classList.add('text-xl', 'font-semibold', 'text-gray-900', 'dark:text-white');
    modalHeaderTitle.innerText = 'Something went wrong';

    const modalHeaderButton = document.createElement('button');
    modalHeaderButton.type = 'button';
    modalHeaderButton.classList.add('text-gray-400', 'bg-transparent', 'hover:bg-gray-200', 'hover:text-gray-900', 'rounded-lg', 'text-sm', 'w-8', 'h-8', 'ml-auto', 'inline-flex', 'justify-center', 'items-center', 'dark:hover:bg-gray-600', 'dark:hover:text-white');
    modalHeaderButton.addEventListener('click', () => {
        modal.remove();
    });

    const modalHeaderButtonIcon = document.createElement('i');
    modalHeaderButtonIcon.classList.add('w-3', 'h-3', 'fa', 'fa-times');

    const modalBody = document.createElement('div');
    modalBody.classList.add('p-6', 'space-y-2');

    const modalBodyText = document.createElement('p');
    modalBodyText.classList.add('text-base', 'leading-relaxed', 'text-gray-500', 'dark:text-gray-400', 'ml-1');
    modalBodyText.innerText = 'If you want to help us improve, please send us the error report.';

    const modalBodyTextarea = document.createElement('textarea');
    modalBodyTextarea.classList.add('w-full', 'px-4', 'py-2', 'text-gray-700', 'bg-gray-100', 'border', 'border-gray-300', 'rounded', 'focus:border-primary', 'focus:ring-0', 'dark:bg-gray-800', 'dark:text-gray-300', 'dark:border-gray-600', 'dark:focus:border-primary');
    modalBodyTextarea.rows = 4;
    modalBodyTextarea.placeholder = 'Describe the error here...';

    const modalFooter = document.createElement('div');
    modalFooter.classList.add('flex', 'items-center', 'p-6', 'space-x-2', 'border-t', 'border-gray-200', 'rounded-b', 'dark:border-gray-600', 'justify-end');

    const modalFooterButtonSend = document.createElement('button');
    modalFooterButtonSend.type = 'button';
    modalFooterButtonSend.classList.add('text-white', 'bg-blue-700', 'hover:bg-blue-800', 'focus:ring-4', 'focus:outline-none', 'focus:ring-blue-300', 'font-medium', 'rounded-lg', 'text-sm', 'px-5', 'py-2.5', 'text-center', 'dark:bg-blue-600', 'dark:hover:bg-blue-700', 'dark:focus:ring-blue-800');
    modalFooterButtonSend.innerText = 'Send';
    modalFooterButtonSend.addEventListener('click', () => {
        const user = localStorage.getItem('user');
        const userObject = user ? JSON.parse(user) : null;
        const userName = userObject?.display_name ?? userObject?.username ?? 'Anonymous';
        const userEmail = userObject?.email ?? 'annoymous@wizarr.dev';
        const eventId = Sentry.captureMessage(modalBodyTextarea.value);

        Sentry.captureUserFeedback({
            name: userName,
            email: userEmail,
            comments: modalBodyTextarea.value,
            event_id: Sentry.lastEventId() ?? eventId,
        });

        modal.remove();
    });

    const modalFooterButtonClose = document.createElement('button');
    modalFooterButtonClose.type = 'button';
    modalFooterButtonClose.classList.add('text-gray-500', 'bg-white', 'hover:bg-gray-100', 'focus:ring-4', 'focus:outline-none', 'focus:ring-blue-300', 'rounded-lg', 'border', 'border-gray-200', 'text-sm', 'font-medium', 'px-5', 'py-2.5', 'hover:text-gray-900', 'focus:z-10', 'dark:bg-gray-700', 'dark:text-gray-300', 'dark:border-gray-500', 'dark:hover:text-white', 'dark:hover:bg-gray-600', 'dark:focus:ring-gray-600');
    modalFooterButtonClose.innerText = 'Close';
    modalFooterButtonClose.addEventListener('click', () => {
        modal.remove();
    });

    modalHeaderButton.appendChild(modalHeaderButtonIcon);
    modalHeader.appendChild(modalHeaderTitle);
    modalHeader.appendChild(modalHeaderButton);
    modalBody.appendChild(modalBodyText);
    modalBody.appendChild(modalBodyTextarea);
    modalFooter.appendChild(modalFooterButtonSend);
    modalFooter.appendChild(modalFooterButtonClose);
    modalContentInner.appendChild(modalHeader);
    modalContentInner.appendChild(modalBody);
    modalContentInner.appendChild(modalFooter);
    modalContent.appendChild(modalContentInner);
    modal.appendChild(modalContent);

    document.body.appendChild(modal);
}

window.feedback = feedback;

/* Track errors, using Sentry. NO PERSONAL DATA IS COLLECTED. */
Sentry.init({
    dsn: "https://c7dcd29d70695f80ced9b23374d12185@o4505748808400896.ingest.sentry.io/4505748995178496",
    replaysSessionSampleRate: 1.0,
    replaysOnErrorSampleRate: 1.0,
    integrations: [new Sentry.Replay({
        maskAllText: false,
        blockAllMedia: false,
        maskAllInputs: false,
        errorSampleRate: 1.0,
        sessionSampleRate: 1.0,
    })],
    beforeSend(event, hint) {
        if (event.exception) {
            feedback();
        }
        return event;
    },
});
