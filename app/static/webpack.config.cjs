const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const TerserPlugin = require("terser-webpack-plugin");

module.exports = {
    entry: './src/index.ts',
    mode: 'production',
    output: {
        path: path.resolve(__dirname, './js'),
        filename: 'app.js',
        // asyncChunks: true,
        // chunkFilename: '[name].js',
    },
    resolve: {
        extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
    },
    devtool: "inline-source-map",
    module: {
        rules: [
            {
                test: /\.(ts|tsx)$/,
                exclude: /node_modules/,
                use: ['ts-loader']
            },
            {
                test: /\.(css|scss|sass)$/i,
                use: [
                    {
                        loader: MiniCssExtractPlugin.loader,
                    }, 
                    {
                        loader: 'css-loader',
                        options: {
                            sourceMap: true,
                        },
                    },
                    {
                        loader: 'postcss-loader',
                    }, 
                    {
                        loader: 'sass-loader',
                    }
                ],
            },
        ],
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
    },
    plugins: [
        new MiniCssExtractPlugin({
            filename: '../css/app.css',
        }),
    ],
};