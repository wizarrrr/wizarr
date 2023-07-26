import axios from 'axios';

import addToWindow from '../utils/addToWindow';

const getSettings = async (): Promise<any> => {
    const resp = await axios.get('/api/settings');
    return resp.data;
}

const updateSettings = async (settings: FormData): Promise<any> => {
    await axios.put('/api/settings', settings);
}

const deleteSettings = async (id: number): Promise<void> => {
    await axios.delete(`/api/settings/${id}`);
}

addToWindow(['api', 'settings', 'getSettings'], getSettings);
addToWindow(['api', 'settings', 'updateSettings'], updateSettings);
addToWindow(['api', 'settings', 'deleteSettings'], deleteSettings);