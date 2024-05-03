<template>
    <div ref="jellyForm">
        <FormKit type="form" id="jellyfinForm" v-model="form" @submit="submit()" submit-label="Create Account" :submit-attrs="{ wrapperClass: 'flex justify-end' }">
            <FormKit type="text" label="Username" name="username" placeholder="marvin" validation="required:trim|alphanumeric" required autocomplete="off" />
            <FormKit type="email" label="Email" name="email" placeholder="marvin@wizarr.dev" validation="required:trim|email" required autocomplete="email" />
            <FormKit type="password" label="Password" name="password" placeholder="••••••••" validation="required:trim" required autocomplete="new-password" :classes="{ outer: form.password ? '!mb-0' : '' }" />
            <PasswordMeter :password="form.password" class="mb-[23px] mt-1 px-[2px]" v-if="form.password" />
            <FormKit type="password" label="Confirm Password" name="password_confirm" placeholder="••••••••" validation="required|confirm" required autocomplete="new-password" />
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useResizeObserver } from "@vueuse/core";

import type { Emitter, EventType } from "mitt";
import type { JellyfinForm } from "../../types/JellyfinForm";

import PasswordMeter from "vue-simple-password-meter";

export default defineComponent({
    name: "JellyfinSetupView",
    components: {
        PasswordMeter,
    },
    props: {
        eventBus: {
            type: Object as () => Emitter<Record<EventType, unknown>>,
            required: false,
        },
    },
    data() {
        return {
            observer: null as { stop: () => void } | null,
            form: {
                username: "",
                email: "",
                password: "",
                password_confirm: "",
            } as JellyfinForm,
        };
    },
    methods: {
        submit() {
            this.eventBus?.emit("jellyfinCreateAccount", this.form);
        },
    },
    mounted() {
        setTimeout(() => {
            this.observer = useResizeObserver(this.$refs.jellyForm as HTMLElement, () => {
                this.$emit("height");
            });
        }, 500);
    },
    beforeUnmount() {
        this.observer?.stop();
    },
});
</script>
