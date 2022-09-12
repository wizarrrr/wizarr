Translations
============

WTForms uses gettext to provide translations. Translations for various
strings rendered by WTForms are created and updated by the community. If
you notice that your locale is missing, or find a translation error,
please submit a fix.


Create
------

To create a translation, initialize a catalog in the new locale:

```
$ python setup.py init_catalog --locale <your locale>
```

This will create some folders under the locale name and copy the
template.

Edit
----

After creating a translation, or to edit an existing translation, open
the ``.po`` file. While they can be edited by hand, there are also tools
that make working with gettext files easier.

Make sure the `.po` file:

- Is a valid UTF-8 text file.
- Has the header filled out appropriately.
- Translates all messages.


Verify
------

After working on the catalog, verify that it compiles and produces the
correct translations.

```
$ python setup.py compile_catalog
```

Try loading your translations into some sample code to verify they look
correct.


Submit
------

To submit your translation, create a pull request on GitHub.
