import React, { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import addToWindow from '../utils/addToWindow';
import DiscordFlow from './flow';

const renderDiscordFlow = (element: HTMLElement) => {
    const root = createRoot(element);

    root.render(
        <StrictMode>
            <DiscordFlow />
        </StrictMode>
    );
};

addToWindow(['react', 'renderDiscordFlow'], renderDiscordFlow);