# -*- coding: utf-8 -*-
# Part of the code inspired from https://gist.github.com/JordanReiter/3667759

import logging
import os

import paramiko


logger = logging.getLogger('ssh-storage')


class SSHClientManagerException(Exception):
    pass


class SSHClientManager:
    def __init__(self, hostname, username=None, password=None, port=22, rsa_key=None, basepath=None, *args, **kwargs):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.rsa_key = rsa_key
        self.basepath = basepath
        self.currentpath = basepath
        self._ssh = None
        self._sftp = None
        super(SSHClientManager, self).__init__(*args, **kwargs)

    def check(self):
        if not self.username:
            raise SSHClientManagerException()

        if not self.password and not self.rsa_key:
            raise SSHClientManagerException()

    def setup(self):
        self._ssh = paramiko.SSHClient()
        self.set_missing_host_key_policy()
        ssh_kwargs = {}
        ssh_kwargs['port'] = self.port
        if self.username:
            ssh_kwargs['username'] = self.username
        if self.password:
            ssh_kwargs['password'] = self.password
        if self.rsa_key:
            ssh_kwargs['key_filename'] = self.rsa_key
        return self.connect(**ssh_kwargs)

    def connect(self, **kwargs):
        try:
            self._ssh.connect(self.hostname, **kwargs)
            self._sftp = self._ssh.open_sftp()
            logger.debug("OK. Connection established!")
            return True
        except paramiko.SSHException:
            logger.debug("Connection Failed")
            return False

    @property
    def sftp(self):
        """Lazy SFTP connection"""
        if not hasattr(self, '_sftp'):
            self.setup()
        return self._sftp

    def set_missing_host_key_policy(self, policy=paramiko.AutoAddPolicy()):
        self._ssh.set_missing_host_key_policy(policy)

    def execute_command(self, command):
        stdin, stdout, stderr = self._ssh.exec_command(command)
        return stdin, stdout, stderr

    def mkdir(self, path, recursive=True):
        try:
            self._sftp.mkdir(path)
        except IOError:
            if recursive:
                pathdirs = path.split(os.path.sep)
                for pp in range(1, len(pathdirs)):
                    currentpath = os.path.join('/', *pathdirs[:pp + 1])
                    try:
                        self._sftp.lstat(currentpath)
                    except IOError:
                        self._sftp.mkdir(currentpath)
            else:
                raise
        return path

    def upload(self, sourcefile, path=None, destname=None, overwrite=True):
        is_file = False
        if hasattr(sourcefile, 'file'):
            is_file = True

        try:
            filename = sourcefile.name
        except AttributeError:
            filename = sourcefile

        if not destname:
            _, destname = os.path.split(filename)

        if not path:
            path = self.currentpath
        else:
            path = os.path.join(self.basepath, path)
        self.mkdir(path)

        destpath = os.path.join(path, destname)
        filename_prefix, filename_ext = os.path.splitext(destpath)

        counter = 0
        while True:
            try:
                self._sftp.lstat(destpath)
                if overwrite:
                    logger.debug("Filename found. Overwriting")
                    break
                counter += 1
                destpath = "{}_{}{}".format(
                    filename_prefix,
                    counter,
                    filename_ext
                )
                logger.debug("Filename found. Will try {}".format(destpath))
            except:
                break
        try:
            logger.debug("Uploading {} to {}".format(filename, destpath))
            if is_file:
                self._sftp.putfo(sourcefile, destpath)
            else:
                self._sftp.put(filename, destpath)
            return True
        except IOError as ioe:
            logger.error("There were problems uploading {} to {}.\n{}".format(
                filename,
                destpath,
                ioe
            ))

        return False

    def remove(self, filename, path=None):
        _, filename = os.path.split(filename)

        if not path:
            path = self.currentpath
        else:
            path = os.path.join(self.basepath, path)

        destpath = os.path.join(path, filename)
        logger.debug("Removing file: {}".format(destpath))
        try:
            self._sftp.remove(destpath)
            return True
        except IOError:
            logger.error("The path '{}' doesn't exist.".format(destpath))

        return False

    def close_connection(self):
        try:
            self.hostname = None
            self.username = None
            self.password = None
            self.port = 22
            self.rsa_key = None
            self.basepath = None
            self.currentpath = None
            self._sftp.close()
            self._ssh.close()
            self._sftp = None
            self._ssh = None
            return True
        except:
            return False
