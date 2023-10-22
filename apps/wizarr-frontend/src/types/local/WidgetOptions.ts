import type { Component } from 'vue';

export interface WidgetOptions<T = Promise<Component>> {
    id: string;
    type: string;
    component?: T;
    grid: {
        x?: number;
        y?: number;
        w: number;
        h: number;
    };
}
