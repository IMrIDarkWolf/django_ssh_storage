=============================
django_ssh_storage
=============================

.. image:: https://badge.fury.io/py/django_ssh_storage.svg
    :target: https://badge.fury.io/py/django_ssh_storage

.. image:: https://travis-ci.org/easydevmixin/django_ssh_storage.svg?branch=master
    :target: https://travis-ci.org/easydevmixin/django_ssh_storage

.. image:: https://codecov.io/gh/easydevmixin/django_ssh_storage/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/easydevmixin/django_ssh_storage

Simple Django app allowing you to store static and media assets on a remote server using SSH.

Documentation
-------------

The full documentation is at https://django_ssh_storage.readthedocs.io.

Quickstart
----------

Install django_ssh_storage::

    pip install django_ssh_storage

Add it to your `INSTALLED_APPS` settings::

    INSTALLED_APPS = (
        ...
        'ssh_storage.apps.SshStorageConfig',
    )

Set up the `SSH_STORAGE_LOCATION` dictionary in settings::

    SSH_STORAGE_LOCATION = {
        "HOSTNAME": "10.0.0.101",
        "USERNAME": "ausername",
        "BASEPATH": "/home/ausername/www-data",
        "PASSWORD": "MySuperSecret",
        "RSA_KEY": "/home/ausername/.ssh/id_rsa_key",
        "PORT": "22",
        "STATIC_PROXY_PROTOCOL": "https://",
        "STATIC_PROXY_HOSTNAME": "my.website.com",
        "PROXY_PORT": "443",
    }

Set up `media` and `static` files location in settings::

    # Static files (CSS, JavaScript, Images)
    STATICFILES_LOCATION = 'static'
    STATIC_URL = '/static/'
    STATICFILES_STORAGE = 'ssh_storage.custom_storage.StaticStorage'

    # Media files
    MEDIAFILES_LOCATION = "media"
    MEDIA_URL = '/media/'
    DEFAULT_FILE_STORAGE = 'ssh_storage.custom_storage.MediaStorage'

Your Django app is ready to save/load files remotely.

Features
--------

* TODO

Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox

Credits
-------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
