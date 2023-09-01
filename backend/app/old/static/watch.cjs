const webpack = require('webpack');

// Define the custom watcher class
class CustomWatcher {
    constructor(compiler) {
        this.compiler = compiler;
    }

    watch() {
        console.log('Watching files for changes...');

        this.compiler.watch({}, (err, stats) => {
            if (err) {
                console.error(err);
                return;
            }
            console.log(stats.toString({ colors: true }));
            console.log('Build complete.');
        });
    }
}


// Webpack configuration exported from webpack.config.cjs
const config = require('./webpack.config.cjs');

const compiler = webpack(config);
const customWatcher = new CustomWatcher(compiler);

// Create and start the custom watcher
customWatcher.watch(config.watchOptions);
