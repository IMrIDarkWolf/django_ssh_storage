# -*- coding: utf-8 -*-

# Storage class for SSH
# It uses SFTP protocol
#
# Code inspired from https://bitbucket.org/david/django-storages
#
# A SSH_STORAGE_LOCATION dictionary is expected in settings.
# This dictionary must have the following KEYs:
# - HOSTNAME: The remote server hostname
# - USERNAME: The username under which we want to store the files
# - BASEPATH: The base path on the remote server where to store the files
#
# Optionally:
# - PROTOCOL: Must be http:// or https://, default is http://
# - PASSWORD: The password for the user in the remote server. Must be given if there's no RSA_KEY specified
# - RSA_KEY: The path to the private rsa key linked to the remote server
# - PORT: If the SSH port is not the default 22
# - STATIC_PROXY_PROTOCOL: http:// or https:// protocol for user with the proxy serving static assets. If empty or not
#                          provided its value will be the same as PROTOCOL
# - STATIC_PROXY_HOSTNAME: Name of the proxy serving static assets. If empty or not provided its value will be the same
#                          as HOSTNAME
# - STATIC_PROXY_PORT: Port number of the proxy serving static assets. If empty or not provided its value
#                      will 80

import logging
import os
import posixpath
import stat
import copy

from datetime import datetime

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage, default_storage
from django.core.exceptions import ImproperlyConfigured
from six import BytesIO

from .sshclientmanager import SSHClientManager


logger = logging.getLogger('ssh-storage')


class SSHStorageException(Exception):
    pass


class SSHStorage(Storage):
    def __init__(self, location=settings.SSH_STORAGE_LOCATION, *args, **kwargs):
        logger.debug("__init__")
        super(SSHStorage, self).__init__(*args, **kwargs)
        self._config = self._decode_location(location)
        self._ssh_client_manager = None
        self._pathmod = posixpath

    def _decode_location(self, location):
        logger.debug("_decode_location")
        # Mandatory attributes
        if location.get('HOSTNAME', '') == '':
            logger.fatal('A hostname must be provided.')
            raise ImproperlyConfigured(
                'A hostname must be provided.'
            )

        if location.get('USERNAME', '') == '':
            logger.fatal('A username must be provided.')
            raise ImproperlyConfigured(
                'A username must be provided.'
            )

        if location.get('BASEPATH', '') == '':
            logger.fatal('A basepath must be provided.')
            raise ImproperlyConfigured(
                'A basepath must be provided.'
            )

        if location.get('PASSWORD', '') == '' and location.get('RSA_KEY', '') == '':
            logger.fatal('A password or rsa_key must be provided.')
            raise ImproperlyConfigured(
                'A password or rsa_key must be provided.'
            )

        config = dict()
        config['hostname'] = location['HOSTNAME']
        config['username'] = location['USERNAME']
        config['basepath'] = location['BASEPATH']

        # Optional attributes
        protocol = location.get('PROTOCOL', '')
        if protocol == '' or protocol.lower() != 'http://' and protocol.lower() != 'https://':
            config['protocol'] = 'http://'
        else:
            config['protocol'] = protocol.lower()

        if location.get('PASSWORD', '') == '':
            config['password'] = None
            config['rsa_key'] = location['RSA_KEY']
            if not os.path.exists(config['rsa_key']):
                raise ImproperlyConfigured(
                    "The file '{}' has not been found.".format(config['rsa_key'])
                )
        else:
            config['password'] = location['PASSWORD']
            config['rsa_key'] = None

        if location.get('PORT', '') == '':
            config['port'] = 22
        else:
            try:
                config['port'] = int(location['PORT'])
            except ValueError:
                config['port'] = 22

        static_proxy_protocol = location.get('STATIC_PROXY_PROTOCOL', '')
        if static_proxy_protocol == '' or static_proxy_protocol.lower() != 'http://'\
                and static_proxy_protocol.lower() != 'https://':
            config['static_proxy_protocol'] = config['protocol']
        else:
            config['static_proxy_protocol'] = static_proxy_protocol

        static_proxy_hostname = location.get('STATIC_PROXY_HOSTNAME', '')
        if static_proxy_hostname == '':
            config['static_proxy_hostname'] = config['hostname']
        else:
            config['static_proxy_hostname'] = static_proxy_hostname

        static_proxy_port = location.get('STATIC_PROXY_PORT', '')
        if static_proxy_port == '':
            config['static_proxy_port'] = '80'
        else:
            try:
                int(static_proxy_port)
                config['static_proxy_port'] = static_proxy_port
            except ValueError:
                config['static_proxy_port'] = '80'

        return config

    def _add_to_basepath(self, location):
        logger.debug("_add_to_basepath")
        self._config['location'] = location
        _path = self._config['basepath']
        _path = os.path.join(_path, location)
        self._config['basepath'] = _path

    def _start_connection(self):
        logger.debug("_start_connection")
        # Check if connection is still alive and if not, drop it.
        if self._ssh_client_manager is not None:
            try:
                self._ssh_client_manager.check()
            except:
                try:
                    self._ssh_client_manager.close_connection()
                except:
                    pass
                self._ssh_client_manager = None

        # Real reconnect
        if self._ssh_client_manager is None:
            self._ssh_client_manager = SSHClientManager(
                hostname=self._config['hostname'],
                username=self._config['username'],
                basepath=self._config['basepath'],
                password=self._config['password'],
                rsa_key=self._config['rsa_key'],
                port=self._config['port']
            )
            if not self._ssh_client_manager.setup():
                logger.error("Connection or login error using data {}".format(
                        repr(self._config)
                    )
                )
                raise SSHStorageException(
                    "Connection or login error using data {}".format(
                        repr(self._config)
                    )
                )

    @property
    def ssh_client_manager(self):
        logger.debug("ssh_client_manager")
        # Lazy initializer
        if self._ssh_client_manager is None:
            self._start_connection()
        return self._ssh_client_manager

    def _join(self, *args):
        logger.debug("_join")
        # Use the path module for the remote host type to join a path together
        return self._pathmod.join(*args)

    def _remote_path(self, name):
        logger.debug("_remote_path")
        return self._join(self._config['basepath'], name)

    def _isdir_attr(self, item):
        logger.debug("_isdir_attr")
        # Return whether an item in sftp.listdir_attr results is a directory
        if item.st_mode is not None:
            return stat.S_IFMT(item.st_mode) == stat.S_IFDIR
        else:
            return False

    def exists(self, name):
        logger.debug("exists")
        # Try to retrieve file info.  Return true on success, false on failure.
        remote_path = self._remote_path(name)
        try:
            self.ssh_client_manager.sftp.stat(remote_path)
            return True
        except IOError:
            return False

    def listdir(self, path):
        logger.debug("listdir")
        remote_path = self._remote_path(path)
        logger.debug("REMOTE PATH: {}".format(remote_path))
        dirs, files = [], []
        for item in self.ssh_client_manager.sftp.listdir_attr(remote_path):
            if self._isdir_attr(item):
                dirs.append(item.filename)
            else:
                files.append(item.filename)
        return dirs, files

    def disconnect(self):
        logger.debug("disconnect")
        if self._ssh_client_manager:
            self._ssh_client_manager.close_connection()
            self._ssh_client_manager = None

    def _put_file(self, name, content):
        logger.debug("_put_file")
        # Connection must be open!
        path, destname = os.path.split(name)
        logger.debug("PATH: {}, DESTNAME: {}".format(
            path,
            destname
        ))
        result = self._ssh_client_manager.upload(
            sourcefile=content,
            destname=destname,
            path=path if path != '' else None
        )

        if not result:
            logger.error("Error writing file {}".format(name))
            raise SSHStorageException("Error writing file {}".format(name))

    def _read(self, name):
        logger.debug("_read")
        remote_path = self._remote_path(name)
        return self.ssh_client_manager.sftp.open(remote_path, 'rb')

    def _open(self, name, mode='rb'):
        logger.debug("_open")
        return SSHStorageFile(name, self, mode)

    def _save(self, name, content):
        logger.debug("_save")
        content.open()
        self._start_connection()
        self._put_file(name, content)
        content.close()
        return name

    def delete(self, name):
        logger.debug("delete")
        remote_path = self._remote_path(name)
        self.ssh_client_manager.sftp.remove(remote_path)

    def size(self, name):
        logger.debug("size")
        remote_path = self._remote_path(name)
        return self.ssh_client_manager.sftp.stat(remote_path).st_size

    def get_modified_time(self, name):
        logger.debug("modified_time")
        remote_path = self._remote_path(name)
        utime = self.ssh_client_manager.sftp.stat(remote_path).st_mtime
        return datetime.fromtimestamp(utime)

    def get_accessed_time(self, name):
        logger.debug("accessed_time")
        remote_path = self._remote_path(name)
        utime = self.ssh_client_manager.sftp.stat(remote_path).st_atime
        return datetime.fromtimestamp(utime)

    def get_created_time(self, name):
        logger.debug("created_time")
        pass

    def path(self, name):
        logger.debug("path")
        pass

    def url(self, name):
        logger.debug("url")
        hostname_aux = self._config['static_proxy_hostname']
        if self._config['static_proxy_port'] != '80':
            hostname_aux = "{}:{}".format(hostname_aux, self._config['static_proxy_port'])
        the_url = os.path.join(
            self._config['static_proxy_protocol'],
            hostname_aux,
            self._config['location'],
            name
        ).replace('\\', '/')
        logger.debug("URL: {}".format(the_url))
        return the_url


class MultipleSSHStorages(SSHStorage):

    def __init__(self, location=settings.SSH_STORAGE_LOCATION, *args, **kwargs):
        super(MultipleSSHStorages, self).__init__(location, *args, **kwargs)
        self._ssh_client_managers = dict()

        for host in self._config['hostnames']:
            self._ssh_client_managers[host] = None

    def _decode_location(self, location):
        if location.get('HOSTNAMES', '') == '':
            logger.fatal('A hostname must be provided.')
            raise ImproperlyConfigured(
                'A hostname must be provided.'
            )
        location['HOSTNAME'] = 'localhost'
        config = super(MultipleSSHStorages, self)._decode_location(location)

        config['hostnames'] = location['HOSTNAMES']
        return config

    def _start_connection(self):
        logger.debug("_start_connection")
        # Check if connection is still alive and if not, drop it.
        managers = self._ssh_client_managers
        for host, manager in managers.items():
            if manager is not None:
                try:
                    manager.check()
                except:
                    try:
                        manager.close_connection()
                    except:
                        pass
                    manager = None

            # Real reconnect
            if manager is None:
                manager = SSHClientManager(
                    hostname=host,
                    username=self._config['username'],
                    basepath=self._config['basepath'],
                    password=self._config['password'],
                    rsa_key=self._config['rsa_key'],
                    port=self._config['port']
                )
                if not manager.setup():
                    logger.error("Connection or login error using data {}".format(
                            repr(self._config)
                        )
                    )
                    raise SSHStorageException(
                        "Connection or login error using data {}".format(
                            repr(self._config)
                        )
                    )
                self._ssh_client_managers[host] = manager

    def _put_file(self, name, content):
        logger.debug("_put_file")
        # Connection must be open!
        path, destname = os.path.split(name)
        logger.debug("PATH: {}, DESTNAME: {}".format(
            path,
            destname
        ))

        for manager in self._ssh_client_managers.values():
            result = manager.upload(
                sourcefile=content,
                destname=destname,
                path=path if path != '' else None
            )

            if not result:
                logger.error("Error writing file {}".format(name))
                # raise SSHStorageException("Error writing file {}".format(name))

    def exists(self, name):
        logger.debug("exists")
        # Try to retrieve file info.  Return true on success, false on failure.
        remote_path = self._remote_path(name)

        try:
            for manager in self._ssh_client_managers.values():
                manager.sftp.stat(remote_path)
            return True
        except IOError:
            return False

    def get_modified_time(self, name):
        logger.debug("modified_time")
        remote_path = self._remote_path(name)
        # utime = self.ssh_client_manager.sftp.stat(remote_path).st_mtime
        # return datetime.fromtimestamp(utime)
        return datetime.now()

    def get_accessed_time(self, name):
        logger.debug("accessed_time")
        remote_path = self._remote_path(name)
        # utime = self.ssh_client_manager.sftp.stat(remote_path).st_atime
        # return datetime.fromtimestamp(utime)
        return datetime.now()

    def get_created_time(self, name):
        logger.debug("created_time")
        pass


class SSHStorageFile(File):
    def __init__(self, name, storage, mode):
        self._name = name
        self._storage = storage
        self._mode = mode
        self._is_dirty = False
        self.file = BytesIO()
        self._size = None

    @property
    def size(self):
        logger.debug("I am the size")
        if not hasattr(self, '_size'):
            self._size = self._storage.size(self._name)
        return self._size

    def read(self, num_bytes=None):
        logger.debug("I am the read")
        self.file = self._storage._read(self._name)

        return self.file.read(num_bytes)

    def write(self, content):
        logger.debug("I am the write")
        if 'w' not in self._mode:
            raise AttributeError("File was opened for read-only access.")
        self.file = BytesIO(content)
        self._is_dirty = True

    def close(self):
        logger.debug("I am the close")
        if self._is_dirty:
            self._storage._save(self._name, self.file.getvalue())
        self.file.close()
