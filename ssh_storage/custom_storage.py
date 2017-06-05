# -*- coding: utf-8 -*-

#
# Idea for custom separation of static and media folders on a remote server taken from
# https://www.caktusgroup.com/blog/2014/11/10/Using-Amazon-S3-to-store-your-Django-sites-static-and-media-files/
#

import logging

from django.conf import settings
from .storage import SSHStorage


logger = logging.getLogger('ssh-storage')


class StaticStorage(SSHStorage):
    def __init__(self, *args, **kwargs):
        super(StaticStorage, self).__init__(*args, **kwargs)
        location = settings.STATICFILES_LOCATION
        self._add_to_basepath(location)


class MediaStorage(SSHStorage):
    def __init__(self, *args, **kwargs):
        super(MediaStorage, self).__init__(*args, **kwargs)
        location = settings.MEDIAFILES_LOCATION
        self._add_to_basepath(location)
