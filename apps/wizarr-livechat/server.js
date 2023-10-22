const handler = require('serve-handler');
const http = require('http');
const path = require('path');

const root = path.join(__dirname, 'build'); // Change 'your_custom_directory' to your desired root directory
const customPath = '/livechat'; // Set the custom path you want

const server = http.createServer((request, response) => {
	// Modify the request URL to prepend the custom path
	request.url = request.url.replace(customPath, '/');
	return handler(request, response, { public: root });
});

server.listen(9000, () => {
	console.log(`Running at http://localhost:9000${customPath}, serving ${root}`);
});
