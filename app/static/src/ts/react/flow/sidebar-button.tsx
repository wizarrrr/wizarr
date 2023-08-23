import React, { StrictMode } from 'react';

type SidebarButtonProps = {
  menu: boolean;
  setMenu: React.Dispatch<React.SetStateAction<boolean>>;
};

function SidebarButton({ menu, setMenu }: SidebarButtonProps) {
    return (
        <div className="fixed right-6 bottom-6 group z-10">
            <button type="button" className={`flex transition-opacity duration-75 ease-in-out items-center justify-center text-white bg-primary rounded-full w-14 h-14 hover:bg-primary-hover dark:bg-primary dark:hover:bg-primary-hover focus:ring-4 focus:ring-primary focus:outline-none dark:focus:ring-primary ${menu ? 'opacity-0' : 'opacity-100'}`} onClick={() => setMenu(!menu)}>
                <i className="text-2xl fas fa-plus"></i>
            </button>
        </div>
    );
}

export default SidebarButton;