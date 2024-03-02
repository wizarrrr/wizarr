<template>
    <nav class="bg-white dark:bg-gray-900 absolute w-full z-20 top-0 left-0 border-b border-gray-200 dark:border-gray-600 md:h-[64px]">
        <div class="max-w-screen-xl flex flex-col md:flex-row items-start md:items-center justify-between mx-auto p-4">
            <!-- Left Side -->
            <div class="flex md:order-2 text-center justify-between w-full md:w-min">
                <router-link to="/" class="flex items-center">
                    <WizarrLogo class="mr-3" rounded />
                    <span class="self-center text-2xl font-semibold whitespace-nowrap dark:text-white">Wizarr</span>
                </router-link>
                <button data-collapse-toggle="navbar-default" aria-controls="navbar-default" aria-expanded="false" type="button" class="text-gray-500 dark:text-gray-400 focus:outline-none block md:hidden" @click="expanded = !expanded">
                    <i class="fa-solid fa-md fa-xl fa-bars"></i>
                </button>
            </div>

            <!-- Right Side -->
            <div class="flex md:order-2 text-center overflow-hidden justify-end w-full md:w-min mt-3 md:mt-0 md:block" :class="expanded ? 'block' : 'hidden'">
                <ul class="flex flex-col md:flex-row md:space-x-8 md:text-sm md:font-medium w-full md:w-min">
                    <!-- Page Links -->
                    <li v-for="page in pages" :key="page.name" class="flex text-center items-center">
                        <router-link :to="page.url" as="button" class="text-left md:text-center w-full md:w-auto block py-2 pl-3 pr-4 text-gray-700 rounded hover:bg-gray-100 md:hover:bg-transparent md:border-0 md:hover:text-primary md:p-0 dark:text-gray-400 md:dark:hover:text-white dark:hover:bg-gray-700 dark:hover:text-white md:dark:hover:bg-transparent" :class="$route.path == page.url || (page.url == '/admin/settings' && $route.path.includes('/admin/settings')) ? 'text-black dark:text-white' : ''">
                            {{ __(page.name) }}
                        </router-link>
                    </li>

                    <!-- Quick Actions -->
                    <li class="flex bg-gray-100 dark:bg-gray-800 md:bg-transparent md:dark:bg-transparent rounded text-center p-2 px-3 w-full mt-3 md:mt-0 md:justify-end md:px-0 md:p-0">
                        <div class="flex flex-column w-full space-x-3 justify-between">
                            <div class="flex flex-column space-x-1">
                                <AccountButton />
                                <LanguageSelector />
                                <ThemeToggle />
                                <ViewToggle />
                            </div>
                            <span class="inline-flex hidden md:block w-px h-6 bg-gray-200 dark:bg-gray-700"></span>
                            <LogoutButton />
                        </div>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useUserStore } from "@/stores/user";
import { mapState } from "pinia";

import WizarrLogo from "../WizarrLogo.vue";

import AccountButton from "@/components/Buttons/AccountButton.vue";
import LanguageSelector from "@/components/Buttons/LanguageSelector.vue";
import ThemeToggle from "@/components/Buttons/ThemeToggle.vue";
import ViewToggle from "@/components/Buttons/ViewToggle.vue";
import LogoutButton from "@/components/Buttons/LogoutButton.vue";

export default defineComponent({
    name: "AdminNavBar",
    components: {
        WizarrLogo,
        AccountButton,
        LanguageSelector,
        ThemeToggle,
        ViewToggle,
        LogoutButton,
    },
    computed: {
        activeLink() {
            return this.$route.path;
        },
        ...mapState(useUserStore, ["user"]),
    },
    data() {
        return {
            pages: [
                {
                    name: this.__("Home"),
                    url: "/admin",
                },
                {
                    name: this.__("Invitations"),
                    url: "/admin/invitations",
                },
                {
                    name: this.__("Users"),
                    url: "/admin/users",
                },
                {
                    name: this.__("Settings"),
                    url: "/admin/settings",
                },
            ],
            expanded: false,
        };
    },
    watch: {
        "$route.path"() {
            this.expanded = false;
        },
    },
});
</script>


