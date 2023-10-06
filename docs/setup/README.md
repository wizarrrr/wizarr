# Setup Wizarr V3
#### This document will help you with setting up Wizarr V3, please read thoroughly

## Welcome Page
The refresh icon will wipe everything you have done and restart you back to the beginning.
*Restart Button is currently not working, still in development*

![Screenshot 2023-08-17 at 3 36 31 pm](https://github.com/Wizarrrr/wizarr/assets/16636012/495ee8cb-ece6-4d85-806d-538a87489eb7)

<hr>

## Database Setup
Database setup is not currently required but will be a future update to allow for custom database connection.

![Screenshot 2023-08-17 at 3 36 37 pm](https://github.com/Wizarrrr/wizarr/assets/16636012/c2eb3765-1546-48fe-8e47-b11b2a344cfd)

<hr>

## Account Setup
This is where you will setup your first Wizarr Admin account, your welcome to use the username `admin`, please ensure you use a real email address and also a strong password, something with special characters, numbers and uppercase and lowercase letters.

![Screenshot 2023-08-17 at 3 36 44 pm](https://github.com/Wizarrrr/wizarr/assets/16636012/b518e742-6a29-46ed-8ae4-c76af2edd5b7)

<hr>

## Media Server Setup
Here we need to configure the media server, this can either be `Jellyfin` or `Plex`, what you would use for Server URL will depend on your setup.

<hr>

### Public Hosted Media Server
If your media server is hosted at a public facing domain, for example http://plex.wizarr.dev or https://plex.wizarr.dev then you may use this address to point to your media server.

<strong>DO NOT LEAVE A TRAILING SLASH ON YOUR URL</strong><br>
<em>Example: https://plex.wizarr.dev/</em>

![Screenshot 2023-08-17 at 3 40 01 pm](https://github.com/Wizarrrr/wizarr/assets/16636012/5d3304e2-2963-4519-b7a5-656b0fcf31de)

<hr>

### Media Server Hosted in Docker on same machine
If your media server is hosted inside Docker on the same machine that Wizarr is running on then you can take advantage of Dockers internal DNS routing.

Docker will use your media servers container name as a host address, if you look in the below screenshot you will see that I ran a `docker ps` command and in the last column of the result you can see the container names. For my plex container it's named `plex`.

![Screenshot 2023-08-17 at 3 39 31 pm 1](https://github.com/Wizarrrr/wizarr/assets/16636012/ad1829c2-f2dd-425b-9eb8-1319cb714603)

So we can use this address to point to our media server, you will see in the below screenshot I have set the Server URL to `http://plex:32400`.
1. `http://` - We want to use an unencrypted connection to Plex, this is secure because we are on a sub network inside of Docker.
2. `plex` - This is our docker container name for the chosen media server, this could be any name that you chose when creating your docker container.
3. `:32400` - The port that Plex is running at, Jellyfin would use `8096` for the port number, so if your Jellyfin container name was `jellyfin` you could use the Server URL `http://jellyfin:8096`

<strong>DO NOT LEAVE A TRAILING SLASH ON YOUR URL</strong><br>
<em>Example: http://plex:32400/</em>

![Screenshot 2023-08-17 at 3 37 35 pm](https://github.com/Wizarrrr/wizarr/assets/16636012/5d85d773-9329-427e-bad4-2a55ea70f7f7)

<hr>

### IP Addresses
*THERE IS CURRENTLY AN UNRESOLVED BUG IN WIZARR V3 BETA THAT DOES NOT ALLOW YOU TO USE IP ADDRESSES. THIS SHOULD BE FIXED SOON.

CURRENT WORKAROUND
If you need to use an IP Address then please use the below workaround, you will need to add the below setting to your Wizarr V3's Docker Compose file.

````
extra_hosts:
  - "mediaserver:your-ip-address"
````

KEEP `mediaserver` the same, but replace `your-ip-address` with the IP address of your Media Server you are attempting to point to.

Now save the file and restart Wizarr V3 with the updated changes, you can now set Server URL to `http://mediaserver:32400`, remember `32400` is the port for Plex, if you are using Jellyfin then you would use the port number `8096`

DO NOT USE THE ABOVE `EXTRA_HOSTS` method if your Plex or Jellyfin server is running in Docker on the same machine as Wizarr, instead please refer to using the `Media Server Hosted in Docker on same machine` method.

<strong>DO NOT LEAVE A TRAILING SLASH ON YOUR URL</strong><br>
<em>Example: http://mediaserver:32400/</em>

<hr>

### Libraries Setup
If your Media Server is successfully detected then you will see a button show called `Configure Libraries`, click this to select which Libraries by default Wizarr will allow invited users to be apart of.

![Screenshot 2023-08-17 at 3 40 29 pm](https://github.com/Wizarrrr/wizarr/assets/16636012/0e5fbac5-c11f-4be2-87c6-ec3a086ed385)

For example, if you create an Invite to your Jellyfin server but you do not wish under any circumstance invited users to have access to your `Home Movies` Library then you would select all Libraries <strong>EXCEPT</strong> the `Home Movies` Library.

![Screenshot 2023-08-17 at 3 40 35 pm](https://github.com/Wizarrrr/wizarr/assets/16636012/31bed2bf-deb9-42d8-8058-3ebbf9a9bf28)

<hr>

### All Done
After saving your Libraries (if you chose to configure it now, can be configured later on if you wish), you can click `Save` to be brought to the last step.

Just click `Go to Login` and you will be ready to Login to Wizarr.

![Screenshot 2023-08-17 at 3 40 49 pm](https://github.com/Wizarrrr/wizarr/assets/16636012/3116622d-1dec-499a-a2d3-c5dce9af74c4)
