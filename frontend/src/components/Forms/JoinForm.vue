<template>
    <div class="block w-full">
        <FormKit type="form" @submit="submit" :submit-label="__('Join')" :submit-attrs="{ inputClass: 'w-full justify-center mt-2' }">
            <FormKit type="text" v-model="_code" :label="__('Invite Code')" :value="_code" placeholder="XMFGEJI" />
        </FormKit>
    </div>
</template>

<script lang="ts">
import type { Emitter, EventType } from "mitt";
import { defineComponent } from "vue";

export default defineComponent({
    name: "JoinForm",
    props: {
        code: {
            type: String,
            required: false,
        },
        eventBus: {
            type: Object as () => Emitter<Record<EventType, unknown>>,
            required: false,
        },
    },
    data() {
        return {
            _code: this.code,
        };
    },
    methods: {
        submit() {
            this.eventBus?.emit("join", this._code);
            this.$emit("join", this._code);
        },
    },
});
</script>
