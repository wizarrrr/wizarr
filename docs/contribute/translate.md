# Translate

Thanks for your interest in contributing to Wizarr!

### Weblate

We use Weblate to help translate Wizarr!&#x20;

{% embed url="https://hosted.weblate.org/engage/wizarr/" %}



### Testing Translations

After you have saved a translation, it will be pushed to the `master` branch directly. The `dev` docker image will then be automatically compiled shortly thereafter.&#x20;

To test it out, simply add the `dev` label to the Docker Image, and you can use the `FORCE_LANGUAGE` environment variable to force a language to Wizarr.

{% tabs %}
{% tab title="Docker Compose" %}
```yaml
---
version: "3.8"
services:
  wizarr:
    container_name: wizarr
    image: ghcr.io/wizarrrr/wizarr:dev
    [...]
    environment:
      - FORCE_LANGUAGE=en
```
{% endtab %}

{% tab title="Docker CLI" %}
```
docker run -d \
  -e FORCE_LANGUAGE=en
  [...]
  ghcr.io/wizarrrr/wizarr:dev
```
{% endtab %}
{% endtabs %}



