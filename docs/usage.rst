=====
Usage
=====

To use django_ssh_storage in a project, add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'ssh_storage.apps.SshStorageConfig',
        ...
    )

Set up the `SSH_STORAGE_LOCATION` dictionary in settings:

.. code-block:: python

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

Set up `media` and `static` files location in settings:

.. code-block:: python

    # Static files (CSS, JavaScript, Images)
    STATICFILES_LOCATION = 'static'
    STATIC_URL = '/static/'
    STATICFILES_STORAGE = 'ssh_storage.custom_storage.StaticStorage'

    # Media files
    MEDIAFILES_LOCATION = "media"
    MEDIA_URL = '/media/'
    DEFAULT_FILE_STORAGE = 'ssh_storage.custom_storage.MediaStorage'

Your Django app is ready to save/load files remotely.
