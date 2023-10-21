import type { App } from 'vue';
import filters from '@/ts/filters';
import type { PiniaPluginContext } from 'pinia';

type FilterFunctions = typeof filters;

type FilterNames = keyof FilterFunctions;
type FilterArgs<T extends FilterNames> = Parameters<FilterFunctions[T]>;

declare module 'pinia' {
    export interface PiniaCustomProperties {
        /**
         * $filter - A function that takes a filter name and arguments and returns the result of the filter
         *
         * @param name - The name of the filter to use
         * @param args - The arguments to pass to the filter
         * @returns The result of the filter
         */
        $filter: <T extends FilterNames>(
            name: T,
            ...args: FilterArgs<T>
        ) => ReturnType<FilterFunctions[T]>;

        /**
         * $filters - A function that takes an array of filter names and arguments and returns the result of the filters chained together
         *
         * @param {Array<FilterNames>} names - The names of the filters to use
         * @param {FilterArgs} args - The arguments to pass to the filters
         * @returns The result of the filters chained together
         */
        $filters: <T extends FilterNames[]>(
            names: T,
            ...args: FilterArgs<T[number]>
        ) => ReturnType<FilterFunctions[T[number]]>;
    }
}

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        /**
         * $filter - A function that takes a filter name and arguments and returns the result of the filter
         *
         * @param name - The name of the filter to use
         * @param args - The arguments to pass to the filter
         * @returns The result of the filter
         */
        $filter: <T extends FilterNames>(
            name: T,
            ...args: FilterArgs<T>
        ) => ReturnType<FilterFunctions[T]>;

        /**
         * $filters - A function that takes an array of filter names and arguments and returns the result of the filters chained together
         *
         * @param {Array<FilterNames>} names - The names of the filters to use
         * @param {FilterArgs} args - The arguments to pass to the filters
         * @returns The result of the filters chained together
         */
        $filters: <T extends FilterNames[]>(
            names: T,
            ...args: FilterArgs<T[number]>
        ) => ReturnType<FilterFunctions[T[number]]>;
    }
}

const getFilterFunction = <T extends FilterNames>(
    name: T,
): FilterFunctions[T] => {
    return filters[name];
};

const filter = <T extends FilterNames>(
    name: T,
    ...args: FilterArgs<T>
): ReturnType<FilterFunctions[T]> => {
    // @ts-ignore
    return getFilterFunction(name)(...args) as ReturnType<FilterFunctions[T]>;
};

const filtersChained = <T extends FilterNames[]>(
    names: T,
    ...args: FilterArgs<T[number]>
): ReturnType<FilterFunctions[T[number]]> => {
    // @ts-ignore
    return names.reduce(
        (acc, name) => getFilterFunction(name)(acc, ...args),
        args[0],
    ) as ReturnType<FilterFunctions[T[number]]>;
};

const useFilters = () => {
    return filter;
};

const piniaPluginFilters = (context: PiniaPluginContext) => {
    context.store.$filter = filter;
    context.store.$filters = filtersChained;
};

const vuePluginFilters = {
    install: (app: App) => {
        app.config.globalProperties.$filter = filter;
        app.config.globalProperties.$filters = filtersChained;
    },
};

export default vuePluginFilters;
export { useFilters, piniaPluginFilters, vuePluginFilters };
