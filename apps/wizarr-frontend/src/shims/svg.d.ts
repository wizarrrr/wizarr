declare module '*.svg' {
    const filePath: string;
    export default filePath;
}

declare module '*.svg?component' {
    import { DefineComponent } from 'vue';
    const component: DefineComponent;
    export default component;
}
