import LivechatClient from '@rocket.chat/sdk/lib/clients/Livechat';

const host = 'https://chat.wizarr.dev';
export const useSsl = host && host.match(/^https:/) !== null;

export const Livechat = new LivechatClient({ host, protocol: 'ddp', useSsl });
