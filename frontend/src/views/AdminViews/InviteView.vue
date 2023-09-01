<template>
    <AdminTemplate :header="__('Create Invitation')" :subheader="__('Create an invitation to your server')" class="md:max-w-md">
        <form class="space-y-5" onsubmit="event.preventDefault(); createInvite(this);">
            <!-- Invite Code -->
            <DefaultInput v-model:value="inviteCode" placeholder="XMFGEJI" label="Invite Code" sublabel="(optional)" min="6" max="6" :uppercase="true" />

            <!-- Select Expiration -->
            <SelectInput tooltip-title="Expiration" tooltip="How long before the invite expires and it can no longer be used!" v-model:value="expiration" label="Expiration" name="expiration" :options="expirationOptions" />

            <!-- Custom Expiration -->
            <date-input v-if="expiration == 'custom'" v-model:value="customExpiration" label="Custom Expiration" name="custom-expiration" parsed-output="minutes" :future="true" />

            <!-- ADVANCED OPTIONS -->
            <button @click="advancedOptions = !advancedOptions" type="button" class="block mb-2 text-sm font-medium text-secondary dark:text-primary">
                {{ __("Advanced Options") }}
            </button>

            <Transition :name="advancedOptions ? 'expand' : 'collapse'">
                <div class="space-y-3" v-if="advancedOptions">
                    <div class="space-y-2">
                        <!-- TOGGLE UNLIMITED INVITE USAGE -->
                        <div class="flex items-center justify-start space-x-2">
                            <input id="unlimited" name="unlimited" type="checkbox" class="w-4 h-4 text-primary bg-gray-100 rounded border-gray-300 focus:ring-primary dark:focus:ring-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600" />
                            <label for="unlimited" class="ml-2 text-sm font-medium text-gray-900 dark:text-gray-300">
                                {{ __("Unlimited Usages") }}
                            </label>
                        </div>

                        <!-- TOGGLE PLEX HOME -->
                        <div class="flex items-center justify-start space-x-2">
                            <input id="plex_home" name="plex_home" type="checkbox" class="w-4 h-4 text-primary bg-gray-100 rounded border-gray-300 focus:ring-primary dark:focus:ring-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600" />
                            <label for="plex_home" class="ml-2 text-sm font-medium text-gray-900 dark:text-gray-300">
                                {{ __("Invite to Plex Home") }}
                            </label>
                        </div>

                        <!-- TOGGLE PLEX ALLOW DOWNLOADS -->
                        <div class="flex items-center justify-start space-x-2">
                            <input id="plex_allow_sync" name="plex_allow_sync" type="checkbox" class="w-4 h-4 text-primary bg-gray-100 rounded border-gray-300 focus:ring-primary dark:focus:ring-primary dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600" />
                            <label for="plex_allow_sync" class="ml-2 text-sm font-medium text-gray-900 dark:text-gray-300">
                                {{ __("Allow Downloads") }}
                            </label>
                        </div>
                    </div>

                    <!-- SET DURATION USERS ALIVE -->
                    <!-- ;-) dw we're not killing anyone, just deleting there accounts -->
                    <div>
                        <label for="select-duration" class="flex justify-start items-center mb-2 text-sm font-medium text-gray-900 dark:text-white">
                            <p class="mr-2">
                                {{ __("Duration") }}
                            </p>
                            <span class="relative">
                                <button id="popover-button" type="button">
                                    <svg class="w-4 h-4 text-gray-400 hover:text-gray-500" aria-hidden="true" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path>
                                    </svg>
                                    <span class="sr-only">
                                        {{ __("Show Information") }}
                                    </span>
                                </button>
                                <div id="popover-content" role="tooltip" class="hidden w-1/2 absolute top-15 left-0 p-2 text-sm font-light text-gray-500 bg-white border border-gray-200 rounded shadow-sm w-72 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-400">
                                    <div class="p-3 space-y-2">
                                        <h3 class="font-semibold text-gray-900 dark:text-white">{{ __("Duration") }}</h3>
                                        <p>{{ __("When set, invited user(s) will be removed from the server after the set number of days. (1-999)") }}</p>
                                    </div>
                                </div>
                            </span>
                        </label>

                        <!-- SELECT DURATION -->
                        <!-- (Value is in minutes) -->
                        <select id="select-duration" onchange="selectDuration(this)" class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded focus:ring-primary focus:border-primary block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary dark:focus:border-primary">
                            <option value="null">{{ __("Unlimited") }}</option>
                            <option value="1440">{{ __("1 Day") }}</option>
                            <option value="10080">{{ __("1 Week") }}</option>
                            <option value="43800">{{ __("1 Month") }}</option>
                            <option value="262800">{{ __("6 Months") }}</option>
                            <option value="525600">{{ __("1 Year") }}</option>
                            <option>{{ __("Custom") }}</option>
                        </select>
                    </div>

                    <!-- CUSTOM DURATION -->
                    <!-- (Hidden by default, only shown when "Custom" is selected) -->
                    <div class="hidden" id="custom-duration-container">
                        <label for="custom-duration" class="block mb-2 text-sm font-medium text-gray-900 dark:text-gray-400">
                            {{ __("Custom Duration") }}
                        </label>
                        <input id="custom-duration" type="datetime-local" onchange="customDuration(this)" class="bg-gray-50 border border-gray-300 text-gray-900 sm:text-sm rounded focus:ring-primary focus:border-primary block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary dark:focus:border-primary" />
                    </div>

                    <!-- SELECT SPECIFIC LIBRARIES -->
                    <div>
                        <label for="plex_libraries" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
                            {{ __("Specific Libraries") }}
                        </label>

                        <button id="dropdownSearchButton" onclick="loadLibraries()" data-dropdown-toggle="dropdownSearch" class="inline-flex items-center px-4 py-2 text-sm font-medium text-center text-white bg-primary rounded hover:bg-primary focus:ring-0 focus:outline-none focus:ring-primary dark:bg-primary dark:hover:bg-primary dark:focus:ring-primary" type="button">
                            {{ __("Select Libraries") }}
                            <svg class="w-2.5 h-2.5 ml-2.5" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 10 6">
                                <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m1 1 4 4 4-4" />
                            </svg>
                        </button>

                        <!-- Dropdown menu -->
                        <div id="dropdownSearch" class="z-10 hidden bg-white rounded shadow w-60 dark:bg-gray-700">
                            <div class="p-3">
                                <label for="libraries-group-search" class="sr-only">Search</label>
                                <div class="relative">
                                    <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                                        <svg class="w-4 h-4 text-gray-500 dark:text-gray-400" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 20">
                                            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m19 19-4-4m0-7A7 7 0 1 1 1 8a7 7 0 0 1 14 0Z" />
                                        </svg>
                                    </div>
                                    <input type="text" id="libraries-group-search" onfocus="searchLibraries(this, true)" onchange="searchLibraries(this, false)" class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded focus:ring-primary focus:border-primary block w-full pl-10 p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary dark:focus:border-primary" placeholder="Search user" />
                                </div>
                            </div>
                            <span id="libraries">
                                <input type="hidden" id="libraries-count" value="0" />
                                <div id="loader" class="text-center" role="status">
                                    <i class="text-gray-900 dark:text-white fa-solid fa-spinner fa-spin fa-2xl"></i>
                                </div>
                                <ul id="libraries-list" class="max-h-44 px-3 pb-3 overflow-y-auto text-sm text-gray-700 dark:text-gray-200" aria-labelledby="dropdownSearchButton"></ul>
                            </span>
                            <!-- Toggle All -->
                            <label for="toggle-all-libraries" class="flex w-full items-start p-3 text-sm font-medium text-gray-900 border-t border-gray-200 rounded-b-lg bg-gray-50 dark:border-gray-600 hover:bg-gray-100 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300">
                                {{ __("Select All") }}
                            </label>
                            <input id="toggle-all-libraries" type="checkbox" class="hidden" onchange="toggleAllLibraries(this)" />
                        </div>
                    </div>
                </div>
            </Transition>

            <button type="submit" class="w-full text-white bg-primary hover:bg-primary_hover focus:ring-4 focus:outline-none focus:ring-amber-300 font-medium rounded text-sm px-5 py-2.5 text-center dark:bg-primary dark:hover:bg-primary_hover dark:focus:ring-primary_hover">
                {{ __("Create Invitation") }}
            </button>
        </form>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import AdminTemplate from "@/templates/AdminTemplate.vue";

import DefaultInput from "@/components/Inputs/DefaultInput.vue";
import SelectInput from "@/components/Inputs/SelectInput.vue";
import DateInput from "@/components/Inputs/DateInput.vue";

export default defineComponent({
    name: "InviteView",
    components: {
        AdminTemplate,
        DefaultInput,
        SelectInput,
        DateInput,
    },
    data() {
        return {
            inviteCode: "",
            expiration: 1440 as number | string,
            expirationOptions: [
                {
                    label: "1 Day",
                    value: 1440,
                },
                {
                    label: "1 Week",
                    value: 10080,
                },
                {
                    label: "1 Month",
                    value: 43800,
                },
                {
                    label: "6 Months",
                    value: 262800,
                },
                {
                    label: "1 Year",
                    value: 525600,
                },
                {
                    label: "Never",
                    value: null,
                },
                {
                    label: "Custom",
                    value: "custom",
                },
            ],
            customExpiration: "",
            duration: "unlimited",
            durationOptions: [
                {
                    label: "Unlimited",
                    value: "unlimited",
                },
                {
                    label: "1 Day",
                    value: 1440,
                },
                {
                    label: "1 Week",
                    value: 10080,
                },
                {
                    label: "1 Month",
                    value: 43800,
                },
                {
                    label: "6 Months",
                    value: 262800,
                },
                {
                    label: "1 Year",
                    value: 525600,
                },
                {
                    label: "Custom",
                    value: "custom",
                },
            ],
            advancedOptions: false,
        };
    },
});
</script>
