import { POSITION, TYPE } from 'vue-toastification';
import type {
    PluginOptions,
    CommonOptions,
} from 'vue-toastification/dist/types/types/index.d.ts';

// Default toast options
const defaultToast: CommonOptions = {
    position: POSITION.BOTTOM_RIGHT,
    timeout: 5000,
    closeOnClick: true,
    pauseOnFocusLoss: true,
    pauseOnHover: true,
    draggable: true,
    draggablePercent: 0.6,
    showCloseButtonOnHover: true,
    hideProgressBar: false,
    icon: true,
};

const defaultOptions: PluginOptions = {
    toastDefaults: {
        [TYPE.SUCCESS]: {
            ...defaultToast,
            type: TYPE.SUCCESS,
            toastClassName: '!bg-green-500 !text-white !md:rounded !shadow-lg',
        },
        [TYPE.INFO]: {
            ...defaultToast,
            type: TYPE.INFO,
            toastClassName: '!bg-gray-800 !text-white !md:rounded !shadow-lg',
        },
        [TYPE.ERROR]: {
            ...defaultToast,
            type: TYPE.ERROR,
            toastClassName: '!bg-red-500 !text-white !md:rounded !shadow-lg',
        },
        [TYPE.WARNING]: {
            ...defaultToast,
            type: TYPE.WARNING,
            toastClassName: '!bg-yellow-400 !text-white !md:rounded !shadow-lg',
        },
    },
};

export default defaultOptions;
