---
description: BETA ONLY FEATURE
---

# Discord Integration

#### Find your Discord Server ID

1. In Discord, go to your **Server Settings**
2. Select the **Widget** tab
3. Enable Server Widget
4. Choose an Invite Channel (`general` for example)
5. Copy your **Server ID**

#### Toggle the Discord Widget

Wizarr supports using either the standard Discord widget, or a custom widget utilizing the Discord API. The custom widget is enabled by default, and provides a more integrated look and feel, however if this is not desired you can toggle the standard widget on in Wizarr's settings.

{% hint style="warning" %}
If your Discord information is not showing, this maybe because Discord has flagged your IP for too many requests. Please try again later.
{% endhint %}

{% tabs %}
{% tab title="Custom Widget" %}
<figure><img src="../.gitbook/assets/custom-widget.png" alt=""><figcaption><p>Custom Discord Widget</p></figcaption></figure>
{% endtab %}

{% tab title="Standard Widget" %}
<figure><img src="../.gitbook/assets/default-widget.png" alt=""><figcaption><p>Standard Discord Widget</p></figcaption></figure>
{% endtab %}
{% endtabs %}

{% hint style="info" %}
**Why not use an invitation link?**

Enabling the widget and the invite channel makes the Discord API dynamically generate an invitation link for the purpose of the widget.

This means that to use this integration, you don't need to generate a Never expiring invitation, which some users might want to avoid.
{% endhint %}
