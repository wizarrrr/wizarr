import React, { StrictMode, useCallback, useEffect } from 'react';

import Flow from './flow';
import SideBar from './sidebar';
import SidebarButton from './sidebar-button';

const DiscordFlow = () => {
  const defaultMenu = JSON.parse(localStorage.getItem("discord-flow") ?? "{}");
  const [menu, setMenu] = React.useState(defaultMenu.menu ?? false);

    useEffect(() => {
        localStorage.setItem("discord-flow", JSON.stringify({ menu: menu }));
    }, [menu]);

    return (
        <div
            className="absolute left-0 top-0 bottom-0 right-0 w-full mt-[64px]"
            style={{ height: `calc(${window.innerHeight}px - 64px)` }}
        >
            <Flow />
            <SideBar menu={menu} setMenu={setMenu} />
            <SidebarButton menu={menu} setMenu={setMenu} />
        </div>
    );
};

export default DiscordFlow;
