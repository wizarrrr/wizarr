const { merge } = require('webpack-merge');
const TerserPlugin = require("terser-webpack-plugin");

const common = require('./webpack.config.cjs');
const config = merge(common, {
    mode: 'production',
    watch: false,
    infrastructureLogging: {
        debug: false
    },
    optimization: {
        minimizer: [
            new TerserPlugin({
                terserOptions: {
                    keep_classnames: true,
                    keep_fnames: true,
                },
                extractComments: false,
            }),
        ],
    }
});

delete config.watchOptions;
delete config.devtool;

module.exports = config;