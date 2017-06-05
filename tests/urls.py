# -*- coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.conf.urls import url, include

from ssh_storage.urls import urlpatterns as ssh_storage_urls

urlpatterns = [
    url(r'^', include(ssh_storage_urls, namespace='ssh_storage')),
]
