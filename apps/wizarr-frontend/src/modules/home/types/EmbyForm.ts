/**
 * Interface for the Emby form
 * @interface EmbyForm
 * @property {string} username - The username of the Emby user
 * @property {string} email - The email of the Emby user
 * @property {string} password - The password of the Emby user
 * @property {string} password_confirm - The password confirmation of the Emby user
 */
export interface EmbyForm {
    username: string;
    email: string;
    password: string;
    password_confirm: string;
}
