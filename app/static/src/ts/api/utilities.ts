import axios from 'axios';

import addToWindow from '../utils/addToWindow';

const detectServer = async (server_url: string): Promise<object> => {
    // Get the server type for the given server url
    const resp = await axios.get('/api/utilities/detect-server', { params: { server_url } });

    // Check that the server type is not null and return is status 200
    if (resp.data == null || resp.status != 200) {
        return { error: 'Unable to detect server type' };
    }

    // Return the server type
    return resp.data;
}

const verifyServer = async (server_url: string, api_key: string): Promise<object> => {
    // Get the server type for the given server url
    const resp = await axios.get('/api/utilities/verify-server', { params: { server_url, api_key } });

    // Check that the server type is not null and return is status 200
    if (resp.data == null || resp.status != 200) {
        return { error: 'Unable to verify server' };
    }

    // Return the server type
    return resp.data;
}

addToWindow(['api', 'utilities', 'detectServer'], detectServer);
addToWindow(['api', 'utilities', 'verifyServer'], verifyServer);