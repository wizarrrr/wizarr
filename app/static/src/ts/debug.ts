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

/* Track errors, using Sentry. NO PERSONAL DATA IS COLLECTED. */
Sentry.init({
    dsn: "https://c7dcd29d70695f80ced9b23374d12185@o4505748808400896.ingest.sentry.io/4505748995178496",
    replaysSessionSampleRate: 1.0,
    replaysOnErrorSampleRate: 1.0,
    integrations: [new Sentry.Replay({
        maskAllText: false,
        blockAllMedia: false,
    })],
});

window.debug_sentry = () => {
    const eventId = Sentry.captureMessage('User Feedback');
    // OR: const eventId = Sentry.lastEventId();

    const userFeedback = {
        event_id: eventId,
        name: 'John Doe',
        email: 'john@doe.com',
        comments: 'I really like your App, thanks!'
    }
    Sentry.captureUserFeedback(userFeedback);
}

window.feedback = () => {
    const eventId = Sentry.captureMessage('User Feedback');
    Sentry.showReportDialog({ eventId: eventId });
}

window.Sentry = Sentry;