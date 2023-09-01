import axios from 'axios';

import addToWindow from '../utils/addToWindow';

const deleteUser = async (id: number): Promise<void> => {
    await axios.delete(`/api/users/${id}`);
}

addToWindow(['api', 'users', 'deleteUser'], deleteUser);
