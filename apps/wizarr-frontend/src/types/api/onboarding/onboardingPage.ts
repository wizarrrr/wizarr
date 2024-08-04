/**
 * Interface for the Onboarding page
 * @interface OnboardingPage
 * @property {number} id - The id of the onboarding page
 * @property {string} value - The content for the onboarding page
 * @property {number} order - The order of the onboarding page
 * @property {boolean} enabled - If the onboarding page is enabled
 */
export interface OnboardingPage {
    id: number;
    value: string;
    order: number;
    enabled: boolean;
    template?: number;
    editable?: boolean;
}
