import { nanoid } from 'nanoid';
import React, { useState } from 'react';

type SidebarButtonProps = {
    menu: boolean;
    setMenu: React.Dispatch<React.SetStateAction<boolean>>;
};

function SideBar({ menu, setMenu }: SidebarButtonProps) {

    const onClick = (event: any, nodeType: any) => {
        console.log(event);
    };

    const onDragStart = (event: any, nodeType: any) => {
        event.dataTransfer.setData('application/reactflow', nodeType);
        event.dataTransfer.effectAllowed = 'move';
    };

    return (
        <aside id="default-sidebar" style={{ height: `calc(${window.innerHeight}px - 64px)` }} className={`absolute bottom-0 right-0 z-19 w-64 transition-transform w-full md:w-64 ${menu ? 'block md:translate-x-0' : 'hidden md:block md:translate-x-full'}`}>
            <div className="h-full px-4 py-4 overflow-y-auto bg-white dark:bg-gray-900 md:border-l border-gray-200 dark:border-gray-600">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center">
                        <span className="text-xl font-bold text-gray-800 dark:text-white">Discord Editor</span>
                    </div>
                    <button onClick={() => setMenu(!menu)} className="py-1 px-2 rounded text-black dark:text-white bg-white dark:bg-gray-800 focus:outline-none focus:bg-gray-100 dark:focus:bg-gray-700">
                        <i className="fas fa-times"></i>
                    </button>
                </div>
                <div className="space-y-2 flex flex-col">
                    <div className="bg-white px-4 dark:bg-gray-800 dark:text-white p-2 rounded shadow-lg" onClick={(event) => onClick(event, 'custom')} onDragStart={(event) => onDragStart(event, 'custom')} draggable>
                        <div className="flex flex-col">
                            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">Test Node</h3>
                            <p>This is a test node.</p>
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
}

export default SideBar;