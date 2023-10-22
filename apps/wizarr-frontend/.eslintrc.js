module.exports = {
    env: {
        node: true,
    },
    parser: 'babel-eslint',
    extends: [
        'eslint:recommended',
        'plugin:vue/vue3-recommended',
        'plugin:@typescript-eslint/recommended',
        'prettier',
        '@vue/eslint-config-prettier',
    ],
    rules: {
        // override/add rules settings here, such as:
        // 'vue/no-unused-vars': 'error'
    },
};
