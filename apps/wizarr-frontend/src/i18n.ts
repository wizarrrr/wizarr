import { createGettext, type GetTextOptions } from 'vue3-gettext';
import translations from './language/translations.json';

// Available languages
const availableLanguages: GetTextOptions['availableLanguages'] = {
    vi: 'Tiếng Việt',
    cs: 'Čeština',
    da: 'Dansk',
    de: 'Deutsch',
    en: 'English',
    es: 'Español',
    fa: 'فارسی',
    fr: 'Français',
    he: 'עברית',
    hr: 'Hrvatski',
    hu: 'Magyar',
    is: 'Íslenska',
    it: 'Italiano',
    lt: 'Lietuvių',
    nl: 'Nederlands',
    no: 'Norsk',
    pl: 'Polski',
    pt: 'Português',
    ro: 'Română',
    ru: 'Русский',
    sv: 'Svenska',
    zh_cn: '简体中文',
    zh_tw: '繁體中文',
};

// Get the preferred languages
const preferredLanguages = navigator.languages.map(
    (language) => language.split('-')[0],
);

// Find the first available language that matches the preferred languages
const language =
    preferredLanguages.find((language) => availableLanguages[language]) ?? 'en';

// Log the preferred languages
console.log('Preferred languages:', preferredLanguages);
console.log('Selected Language:', language);

// Create the gettext instance
const gettext = createGettext({
    availableLanguages,
    defaultLanguage: language,
    translations: translations,
    globalProperties: {
        gettext: ['$gettext', '__'],
        ngettext: ['$ngettext', '_n'],
        pgettext: ['$pgettext', '_x'],
        npgettext: ['$npgettext', '_xn'],
    },
});

export { language, availableLanguages };
export default gettext;
