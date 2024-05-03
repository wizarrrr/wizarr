<template>
    <div class="flex flex-col items-center space-y-4">
        <!-- Share Data -->
        <div class="flex flex-col items-center space-y-2">
            <div
                class="group relative rounded-md w-[156px] h-[156px] overflow-hidden cursor-pointer"
                @click="downloadQRCode"
            >
                <img class="absolute" :src="QRcode" alt="Share QRcode" />
                <span
                    class="group-hover:bg-black opacity-[65%] absolute w-full h-full"
                ></span>
                <i
                    class="group-hover:block hidden fa-solid fa-download text-white absolute bottom-0 right-0 m-2"
                ></i>
            </div>
            <div
                class="border border-gray-200 dark:border-gray-700 rounded p-2 text-xs text-gray-500 dark:text-gray-400 cursor-pointer"
                @click="copyToClipboard"
            >
                <span>{{ invitationLink }}</span>
            </div>
        </div>

        <!-- Share Message -->
        <div class="flex flex-col items-center space-y-1 w-2/3 text-center">
            <div class="text-xs text-gray-500 dark:text-gray-400">
                {{
                    __(
                        'Share this link with your friends and family to invite them to join your media server.',
                    )
                }}
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useQRCode } from '@vueuse/integrations/useQRCode';
import type { QRCodeToDataURLOptions } from 'qrcode';
import colors from 'tailwindcss/colors';
import { useClipboard } from '@vueuse/core/index.mjs';

export default defineComponent({
    name: 'ShareSheet',
    props: {
        code: {
            type: String,
            required: true,
        },
        qrCodeOptions: {
            type: Object as () => QRCodeToDataURLOptions,
            default: () => {
                return {
                    type: 'image/png',
                    errorCorrectionLevel: 'H',
                    margin: 3,
                    color: {
                        dark: colors.black,
                        light: colors.white,
                    },
                } as QRCodeToDataURLOptions;
            },
        },
    },
    data() {
        return {
            invitationLink: `${window.location.origin}/i/${this.code}`,
            QRcode: useQRCode(
                `${window.location.origin}/i/${this.code}`,
                this.qrCodeOptions,
            ),
            clipboard: useClipboard({
                legacy: true,
            }),
        };
    },
    methods: {
        downloadQRCode() {
            const link = document.createElement('a');
            link.download = `qrcode-${this.code}.png`;
            link.href = this.QRcode;
            link.click();
        },
        copyToClipboard() {
            if (this.clipboard.isSupported) {
                this.clipboard.copy(this.invitationLink);
                this.$toast.info(this.__('Copied to clipboard'));
            } else {
                this.$toast.error(
                    this.__(
                        'Your browser does not support copying to clipboard',
                    ),
                );
            }
        },
    },
});
</script>
