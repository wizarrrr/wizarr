# Custom HTML

{% hint style="warning" %}
NOT YET IMPLEMENTED
{% endhint %}

With the ability to add a custom HTML section to the setup wizard for Plex and Jellyfin, you can create a custom page that will be automatically centred and placed in a div with a background, making it a seamless addition to your setup process

### Adding Custom HTML

Adding custom HTML to your setup wizard is a simple process. All you need to do is follow these steps:

1. Go to the Settings page and navigate to the HTML section
2. Paste in your custom HTML code

That's it! Your custom HTML section will be automatically added to the setup wizard, centered and styled with a background, thanks TailwindCSS.

### Using TailwindCSS

TailwindCSS is the underlying framework of Wizarr. As a result, users are free to use TailwindCSS syntax in their HTML code for the custom section. This allows for greater flexibility in designing and customizing the appearance of the section.

{% hint style="danger" %}
Javascript will not function inside Custom HTML, for more advanced functionality we advise you fork your own copy of Wizarr. This is to prevent XSS vulnerabilities being introduced.
{% endhint %}
