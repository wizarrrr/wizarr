const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const TerserPlugin = require("terser-webpack-plugin");
const HtmlWebpackPlugin = require('html-webpack-plugin');
const ProgressPlugin = require('webpack').ProgressPlugin;

module.exports = {
    entry: './src/index.ts',
    infrastructureLogging: { debug: true },
    mode: 'development',
    output: {
        filename: 'dist/[name].bundle.js',
        path: path.resolve(__dirname),
    },
    resolve: {
        extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
    },
    watchOptions: {
        ignored: ['**/*.!(ts|html)', '**/node_modules', '**/dist', '**/templates'],
        aggregateTimeout: 300,
        poll: 1000,
        followSymlinks: false
    },
    devtool: "source-map",
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
        runtimeChunk: 'single',
        splitChunks: {
            cacheGroups: {
                vendor: {
                    test: /[\\/]node_modules[\\/]/,
                    name: 'vendors',
                    chunks: 'all'
                }
            },
            chunks: 'all'
        }
    },
    performance: {
        hints: false,
        maxEntrypointSize: 512000,
        maxAssetSize: 512000
    },
    plugins: [
        new MiniCssExtractPlugin({
            filename: 'dist/[name].bundle.css'
        }),
        new HtmlWebpackPlugin({
            filename: '../templates/templates/base.html',
            template: '../templates/base.template.html',
            publicPath: '/static/',
            minify: false
        }),
        new ProgressPlugin()
    ],
};