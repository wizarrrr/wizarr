class CacheStorage implements Storage {
    public storage: any;
    public length: number;

    constructor(store: any) {
        this.storage = store;
        this.length = Object.keys(this.storage.cache).length;
    }

    clear(): void {
        this.storage.cache = {};
    }

    getItem(key: string): string | null {
        return this.storage.cache[key] ?? null;
    }

    key(index: number): string | null {
        return Object.keys(this.storage.cache)[index] ?? null;
    }

    removeItem(key: string): void {
        this.storage.cache = this.storage.cache.map((item: any) => {
            if (item.key === key) {
                return null;
            }
            return item;
        });
    }

    setItem(key: string, value: string): void {
        this.storage.cache = { ...this.storage.cache, [key]: value };
    }
}

export default CacheStorage;
