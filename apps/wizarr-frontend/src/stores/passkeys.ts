import type { MFA, MFAList } from '@/types/api/auth/MFA';

import Auth from '@/api/authentication';
import browser from 'browser-detect';
import { defineStore } from 'pinia';

interface PasskeysStoreState {
    mfas: MFAList;
}

export const usePasskeysStore = defineStore('passkeys', {
    state: (): PasskeysStoreState => ({
        mfas: [],
    }),
    actions: {
        firstLetterUppercase(string: string) {
            return string.charAt(0).toUpperCase() + string.slice(1);
        },
        removeVersion(string: string) {
            return string.replace(/ \d+(\.\d+)*\s*/g, '');
        },
        async getMfas() {
            // Get the mfas from the API
            const mfa = await this.$axios.get('/api/mfa').catch((err) => {
                console.error(err);
                return null;
            });

            // If the mfas are null, return
            if (mfa === null) return;

            // Update the mfas that are already in the store
            // this.mfa.forEach((mfa, index) => {
            //     const new_mfa = mfa.find((new_mfa: Mfa) => new_mfa.id === mfa.id);
            //     if (new_mfa) this.mfa[index] = new_mfa;
            // });

            this.mfas = mfa.data as MFAList;
        },
        async createMfa() {
            // Create a new Auth instance and get the browser info
            const auth = new Auth();
            const browser_info = browser();

            // Get the browser name and os name
            const browser_name = this.firstLetterUppercase(
                browser_info.name ?? 'Unknown',
            );
            const os_name = this.firstLetterUppercase(
                this.removeVersion(browser_info.os ?? 'Unknown'),
            );

            // Create name for the new MFA
            const name = `${browser_name} on ${os_name}`;

            // Create the new MFA
            const response = await auth.mfaRegistration(name);

            // If the response is null, return
            if (response === null || response === undefined) return;

            // Get the MFA from the response
            const mfa = response.data as MFA;

            // Add the new MFA to the store
            if (!this.mfas.find((old_mfa: MFA) => old_mfa.id === mfa.id))
                this.mfas.push(mfa);

            // Show message to user
            this.$toast.info('Successfully created new Passkey');
        },
        async deleteMfa(id: string | number) {
            // Delete the MFA from the API
            await this.$axios.delete(`/api/mfa/${id}`).catch((err) => {
                console.error(err);
                return null;
            });

            // Remove the MFA from the store
            const index = this.mfas.findIndex((mfa: MFA) => mfa.id === id);
            if (index !== -1) this.mfas.splice(index, 1);
        },
    },
});
