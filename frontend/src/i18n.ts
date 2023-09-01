import { createGettext } from "vue3-gettext";
import translations from "./language/translations.json";

const gettext = createGettext({
    availableLanguages: {
        ca: "Català",
        cs: "Čeština",
        da: "Dansk",
        de: "Deutsch",
        en: "English",
        es: "Español",
        fa: "فارسی",
        fr: "Français",
        he: "עברית",
        hr: "Hrvatski",
        hu: "Magyar",
        is: "Íslenska",
        it: "Italiano",
        lt: "Lietuvių",
        nl: "Nederlands",
        no: "Norsk",
        pl: "Polski",
        pt: "Português",
        ro: "Română",
        ru: "Русский",
        sv: "Svenska",
        zh_cn: "简体中文",
        zh_tw: "繁體中文",
    },
    defaultLanguage: "en",
    translations: translations,
    globalProperties: {
        gettext: ["$gettext", "__"],
        ngettext: ["$ngettext", "_n"],
        pgettext: ["$pgettext", "_x"],
        npgettext: ["$npgettext", "_xn"],
    },
});

export default gettext;
