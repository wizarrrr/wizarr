module.exports = {
    input: {
        path: './src', // only files in this directory are considered for extraction
        include: ['**/*.js', '**/*.ts', '**/*.vue'], // glob patterns to select files for extraction
        exclude: [], // glob patterns to exclude files from extraction
        jsExtractorOpts: [
            // custom extractor keyword. default empty.
            {
                keyword: '__', // only extractor default keyword such as $gettext,use keyword to custom
                options: {
                    // see https://github.com/lukasgeiter/gettext-extractor
                    content: {
                        replaceNewLines: '\n',
                    },
                    arguments: {
                        text: 0,
                    },
                },
            },
            {
                keyword: '_n', // $ngettext
                options: {
                    content: {
                        replaceNewLines: '\n',
                    },
                    arguments: {
                        text: 0,
                        textPlural: 1,
                    },
                },
            },
        ],
        compileTemplate: false, // do not compile <template> tag when its lang is not html
    },
    output: {
        path: './src/language', // output path of all created files
        potPath: './messages.pot', // relative to output.path, so by default "./src/language/messages.pot"
        jsonPath: './translations.json', // relative to output.path, so by default "./src/language/translations.json"
        locales: [
            'vi',
            'cs',
            'da',
            'de',
            'en',
            'es',
            'fa',
            'fr',
            'he',
            'hr',
            'hu',
            'is',
            'it',
            'lt',
            'nl',
            'no',
            'pl',
            'pt',
            'ro',
            'ru',
            'sv',
            'zh_cn',
            'zh_tw',
        ],
        flat: false, // don't create subdirectories for locales
        linguas: true, // create a LINGUAS file
        splitJson: false, // create separate json files for each locale. If used, jsonPath must end with a directory, not a file
    },
};
