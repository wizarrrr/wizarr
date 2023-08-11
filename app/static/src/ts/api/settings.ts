import axios from 'axios';

import addToWindow from '../utils/addToWindow';

const getSettings = async (): Promise<any> => {
    const resp = await axios.get('/api/settings');
    return resp.data;
}

const updateSettings = async (settings: FormData): Promise<any> => {
    const resp = await axios.put('/api/settings', settings);
    return resp.data;
}

const deleteSettings = async (id: number): Promise<void> => {
    const resp = await axios.delete(`/api/settings/${id}`);
    return resp.data;
}

addToWindow(['api', 'settings', 'getSettings'], getSettings);
addToWindow(['api', 'settings', 'updateSettings'], updateSettings);
addToWindow(['api', 'settings', 'deleteSettings'], deleteSettings);