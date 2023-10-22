<template>
    <div class="flex flex-col space-y-4">
        <!-- Server Item List -->
        <div class="flex flex-col space-y-1">
            <template
                v-for="server in servers"
                :key="index"
                v-if="servers && servers.length > 0"
            >
                <ScanServerItem
                    :serverUrl="serverURL(server.host, server.port)"
                    :serverType="server.server_type"
                />
            </template>
        </div>

        <!-- No Servers Found -->
        <template v-if="servers == null">
            <div
                class="flex flex-col items-center space-y-2 text-gray-900 dark:text-white"
            >
                <i class="fas fa-exclamation-triangle fa-2x"></i>
                <span class="text-sm text-gray-900 dark:text-gray-400">
                    {{ __('No servers could be found.') }}
                </span>
            </div>
        </template>

        <!-- Select Subnet -->
        <SelectInput
            v-model:value="selectedSubnet"
            :options="subnetMasksOptions"
            placeholder="Select IPv4 subnet"
        />

        <!-- Don't see your server? -->
        <div
            v-if="servers && servers.length > 0"
            class="flex flex-row justify-start items-start text-xs text-gray-900 dark:text-gray-400 mt-2 w-full"
        >
            <button
                class="hover:text-primary dark:hover:text-primary transition duration-150 ease-in-out"
            >
                {{ __("Don't see your server?") }}
            </button>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import ScanServerItem from './ScanServersItem.vue';
import SelectInput from '@/components/Inputs/SelectInput.vue';

import type { OptionHTMLAttributes } from 'vue';

export default defineComponent({
    name: 'ScanServers',
    components: {
        ScanServerItem,
        SelectInput,
    },
    props: {
        tryAgain: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            servers: null as Array<{
                host: string;
                port: string;
                server_type: string;
            }> | null,
            subnets: {
                ipv4: [
                    '192.168.0.0',
                    '192.168.1.0',
                    '192.168.2.0',
                    '192.168.3.0',
                    '192.168.4.0',
                    '172.16.0.0',
                    '172.17.0.0',
                    '172.18.0.0',
                    '172.19.0.0',
                    '172.20.0.0',
                    '10.0.0.0',
                    '10.1.0.0',
                    '10.2.0.0',
                    '10.3.0.0',
                    '10.4.0.0',
                ],
                mask: ['24'],
            },
            selectedSubnet: 'disabled',
        };
    },
    computed: {
        subnetMasks() {
            return this.subnets.ipv4.map((ip) => {
                return this.subnets.mask.map((mask) => {
                    return `${ip}/${mask}`;
                });
            });
        },
        subnetMasksOptions(): OptionHTMLAttributes[] {
            const options = this.subnetMasks.map((subnet) => {
                return subnet.map((mask) => {
                    return { value: mask, label: mask };
                });
            });

            return options.flat();
        },
    },
    methods: {
        async scanServers() {
            const response = await this.$axios
                .get('/api/utilities/scan-servers')
                .catch(() => {
                    this.$toast.error('Could not scan for servers');
                });

            if (!response?.data) {
                this.$toast.error('Could not scan for servers');
                return;
            }

            this.servers = response.data.servers;
        },
        async tryAgainScan() {
            const response = await this.$axios
                .get('/api/utilities/scan-servers', {
                    params: { subnet: this.selectedSubnet },
                })
                .catch(() => {
                    this.$toast.error('Could not scan for servers');
                });

            if (!response?.data) {
                this.$toast.error('Could not scan for servers');
                return;
            }

            this.servers = response.data.servers;
        },
        serverURL(host: string, port: string) {
            return `http://${host}:${port}/`;
        },
    },
    watch: {
        selectedSubnet: {
            immediate: false,
            handler() {
                this.$emit('update:subnet', this.selectedSubnet);
            },
        },
        tryAgain: {
            immediate: false,
            handler() {
                this.tryAgainScan();
            },
        },
    },
});
</script>
