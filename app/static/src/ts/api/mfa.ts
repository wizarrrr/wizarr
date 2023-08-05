import axios from 'axios';

import addToWindow from '../utils/addToWindow';

const getMFA = async (id: number): Promise<any> => {
    const resp = await axios.get(`/api/mfa/${id}`);
    return resp.data;
}

const deleteMFA = async (id: number): Promise<void> => {
    await axios.delete(`/api/mfa/${id}`);
}

addToWindow(['api', 'mfa', 'getMFA'], getMFA);
addToWindow(['api', 'mfa', 'deleteMFA'], deleteMFA);
