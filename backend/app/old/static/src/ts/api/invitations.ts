import axios from "axios";

import addToWindow from "../utils/addToWindow";

const getInvitations = async (): Promise<any> => {
    const resp = await axios.get('/api/invitations');
    return resp.data;
}

const getInvitation = async (id: number): Promise<any> => {
    const resp = await axios.get(`/api/invitations/${id}`);
    return resp.data;
}

const createInvitation = async (invitation: FormData): Promise<any> => {
    const resp = await axios.post('/api/invitations', invitation);
    return resp.data;
}

const updateInvitation = async (id: number, invitation: FormData): Promise<any> => {
    const resp = await axios.put(`/api/invitations/${id}`, invitation);
    return resp.data;
}

const deleteInvitation = async (id: number): Promise<void> => {
    await axios.delete(`/api/invitations/${id}`);
}

addToWindow(['api', 'invitations', 'getInvitations'], getInvitations);
addToWindow(['api', 'invitations', 'getInvitation'], getInvitation);
addToWindow(['api', 'invitations', 'createInvitation'], createInvitation);
addToWindow(['api', 'invitations', 'updateInvitation'], updateInvitation);
addToWindow(['api', 'invitations', 'deleteInvitation'], deleteInvitation);