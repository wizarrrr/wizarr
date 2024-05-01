<template>
    <StripeElements
        v-if="stripe"
        v-slot="{ elements, instance }"
        ref="elms"
        :stripe-key="stripeKey"
    >
        <StripeElement ref="card" :elements="elements" />
    </StripeElements>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { loadStripe, type Stripe } from '@stripe/stripe-js';
import { StripeElements, StripeElement } from 'vue-stripe-js';

import type { Emitter } from 'mitt';
import type { EventRecords } from '../types/EventRecords';

export default defineComponent({
    name: 'Payment',
    components: {
        StripeElements,
        StripeElement,
    },
    props: {
        eventBus: {
            type: Object as () => Emitter<EventRecords>,
            required: true,
        },
        stripeKey: {
            type: String,
            default:
                'pk_live_51Ne7mhCnFDcey5iJiewrFHEOFhG0v2b0pAMbn5FRixynm8ywABLqH2i4BGMKqD4rUSXPIU4kyjN6XsPHiqj7dp9C00AqaOfTTy',
        },
    },
    data() {
        return {
            stripe: null as Stripe | null,
        };
    },
    async mounted() {
        this.$emit('pleaseWait', true);
        this.stripe = await loadStripe(this.stripeKey);
        this.$emit('pleaseWait', false);
    },
});
</script>
