.. :changelog:

History
-------

0.2.0 (2017-06-05)
++++++++++++++++++

* Password takes precedence over rsa-key. If both are given only the password is taken into account.
* Checks RSA key file realy exists. Otherwise raises an ImproperlyConfigured exception.

0.1.0 (2017-06-02)
++++++++++++++++++

* First release on PyPI.
