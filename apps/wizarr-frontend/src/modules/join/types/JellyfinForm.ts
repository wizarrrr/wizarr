/**
 * Interface for the Jellyfin form
 * @interface JellyfinForm
 * @property {string} username - The username of the Jellyfin user
 * @property {string} email - The email of the Jellyfin user
 * @property {string} password - The password of the Jellyfin user
 * @property {string} password_confirm - The password confirmation of the Jellyfin user
 */
export interface JellyfinForm {
    username: string;
    email: string;
    password: string;
    password_confirm: string;
}
