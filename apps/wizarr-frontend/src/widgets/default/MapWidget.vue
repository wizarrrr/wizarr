<template>
    <ol-map
        ref="map"
        :loadTilesWhileAnimating="true"
        :loadTilesWhileInteracting="true"
        class="absolute w-full h-full"
    >
        <ol-view
            ref="view"
            :center="center"
            :rotation="rotation"
            :zoom="zoom"
            :projection="projection"
        />

        <ol-tile-layer>
            <ol-source-xyz crossOrigin="anonymous" :url="mapTheme" />
        </ol-tile-layer>
    </ol-map>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useGeolocation } from '@vueuse/core';
import { useThemeStore } from '@/stores/theme';
import { mapState } from 'pinia';
import { getTheme, type THEME } from '@/ts/utils/darkMode';

export default defineComponent({
    name: 'MapWidget',
    data() {
        return {
            currentLocation: useGeolocation({ immediate: true }),
            center: [40, 40],
            rotation: 0,
            zoom: 8,
            projection: 'EPSG:4326',
            mapTheme: '',
            mapStyle: {
                light: 'https://tile.jawg.io/jawg-streets/{z}/{x}/{y}.png?access-token=1VhtIV9KpAPP5AYqldYs0bIUI0Ap63FKA1NVLOMcrKHjFNljzfwg9dfkNkk6D8fg',
                dark: 'https://tile.jawg.io/jawg-dark/{z}/{x}/{y}.png?access-token=1VhtIV9KpAPP5AYqldYs0bIUI0Ap63FKA1NVLOMcrKHjFNljzfwg9dfkNkk6D8fg',
            } as Record<THEME, string>,
        };
    },
    computed: {
        ...mapState(useThemeStore, ['theme']),
    },
    watch: {
        'currentLocation.coords': {
            immediate: true,
            handler(coords: GeolocationCoordinates) {
                this.center = [coords.longitude, coords.latitude];
            },
        },
        theme: {
            immediate: true,
            handler() {
                const theme = getTheme(this.theme);
                this.mapTheme = this.mapStyle[theme];
            },
        },
    },
});
</script>
