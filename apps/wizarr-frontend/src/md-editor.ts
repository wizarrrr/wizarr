import { config } from 'md-editor-v3';
import "md-editor-v3/lib/style.css";
import gettext from '@/i18n';

import type { StaticTextDefaultValue } from 'md-editor-v3';

const getTranslation = (message: string, language: string): string => {
    const languageTranslations = gettext.translations[language];
    if (languageTranslations && languageTranslations[message]) {
        return languageTranslations[message] as string;
    }
    // Return the original message if no translation is found
    return message;
}

const getTranslations = (): Record<string, StaticTextDefaultValue> => {
    const languages = Object.keys(gettext.translations);
    const translations: Record<string, StaticTextDefaultValue> = {};
    languages.forEach((language) => {
        translations[language] = {
            toolbarTips: {
                bold: getTranslation('Bold', language),
                underline: getTranslation('Underline', language),
                italic: getTranslation('Italic', language),
                strikeThrough: getTranslation('Strikethrough', language),
                title: getTranslation('Title', language),
                sub: getTranslation('Subscript', language),
                sup: getTranslation('Superscript', language),
                quote: getTranslation('Quote', language),
                codeRow: getTranslation('Inline code', language),
                code: getTranslation('Block-level code', language),
                link: getTranslation('Link', language),
                image: getTranslation('Image', language),
                table: getTranslation('Table', language),
                prettier: getTranslation('Prettier', language),
                pageFullscreen: getTranslation('Fullscreen in page', language),
                preview: getTranslation('Preview', language),
            },
            titleItem: {
                h1: getTranslation('Lv1 Heading', language),
                h2: getTranslation('Lv2 Heading', language),
                h3: getTranslation('Lv3 Heading', language),
                h4: getTranslation('Lv4 Heading', language),
                h5: getTranslation('Lv5 Heading', language),
                h6: getTranslation('Lv6 Heading', language),
            },
            imgTitleItem: {
                link: getTranslation('Add image link', language),
                upload: getTranslation('Upload image', language),
                clip2upload: getTranslation('Clip upload', language),
            },
            linkModalTips: {
                linkTitle: getTranslation('Add link', language),
                imageTitle: getTranslation('Add image', language),
                descLabel: getTranslation('Description', language),
                descLabelPlaceHolder: getTranslation('Enter a description...', language),
                urlLabel: getTranslation('Link', language),
                urlLabelPlaceHolder: getTranslation('Enter a link...', language),
                buttonOK: getTranslation('OK', language),
            },
            clipModalTips: {
                title: getTranslation('Crop image', language),
                buttonUpload: getTranslation('Upload', language),
            },
            copyCode: {
                text: getTranslation('Copy', language),
                successTips: getTranslation('Copied!', language),
                failTips: getTranslation('Copy failed!', language),
            },
            footer: {
                markdownTotal: getTranslation('Word count', language),
                scrollAuto: getTranslation('Scroll auto', language),
            }
        };
    });
    return translations;
}

config({
    iconfontType: 'svg',
    editorConfig: {
        languageUserDefined: getTranslations(),
    }
});
