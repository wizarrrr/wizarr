const { merge } = require('webpack-merge');

const common = require('./webpack.config.cjs');
const config = merge(common, {
    mode: 'production',
    watch: false,
    infrastructureLogging: {
        debug: false
    }
});

delete config.watchOptions;
delete config.devtool;

module.exports = config;