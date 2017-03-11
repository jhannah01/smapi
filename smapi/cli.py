#!/usr/bin/env python2.7

import argparse
import sys
import os
import getpass

from smapi.exc import SMAPIError
from smapi.base import SMAPI

class CLIError(SMAPIError):
    '''An exception that occured as part of the CLI
    portion of this application'''
    pass


class CLITool(object):
    _smapi = None
    _is_verbose = False

    def __init__(self, args=None, run_app=False):
        if not args:
            args = self._parse_arguments()

        if isinstance(args, argparse.Namespace):
            if args.port:
                port = int(port)
            else:
                port = None
            options = {'username': args.username, 'password': args.password,
                       'server': args.server, 'port': port, 'use_ssl': args.use_ssl}

            self._is_verbose = args.is_verbose
        elif isinstance(args, dict):
            if 'is_verbose' in args:
                self._is_verbose = args['is_verbose']
                del args['is_verbose']
            options = args.copy()
        else:
            raise CLIError('Unknown arguments object provided: "%r"' % args)

        opts = {}
        server = options.get('server', os.environ.get('SMAPI_HOST', None))
        username = options.get('username', os.environ.get('SMAPI_USER', None))
        password = options.get('password', os.environ.get('SMAPI_PASSWD', None))

        opts['server'] = self._get_setting(server, prompt='Server Hostname: ',
                                            error_message='Missing server hostname')
        opts['username'] = self._get_setting(username, prompt='Admin Username: ',
                                            error_message='Missing admin username')
        opts['password'] = self._get_setting(password, prompt='Admin Password: ',
                                            error_message='Missing admin password',
                                            is_password=True)
        opts['port'] = options.get('port', None)
        opts['use_ssl'] = options.get('use_ssl', False)

        self._options = opts
        self._is_verbose = options.get('is_verbose', False)
        self._smapi = SMAPI(**opts)

    def _parse_arguments(self):
        parser = argparse.ArgumentParser(description='Simple CLI tool for working with SmarterMail')
        parser.add_argument('-s', '--server', dest='server',
                            help='Server Hostname (otherwise use SMAPI_HOST or prompt')
        parser.add_argument('-u', '--user', dest='username',
                            help='Admin Username (otherwise use SMAPI_USER or prompt')
        parser.add_argument('-x', '--password', dest='password',
                            help='Admin Password (otherwise use SMAPI_PASSWD or prompt')
        parser.add_argument('-v', '--verbose', dest='is_verbose', action='store_true',
                            help='Be more verbose')
        parser.add_argument('-e', '--ssl', dest='use_ssl', action='store_true',
                            help='Force using HTTPS to connect')
        parser.add_argument('-p', '--port', dest='port', type=int, default=None)
        return parser.parse_args()

    def _get_setting(self, value, prompt=None, error_message=None, is_password=False):
        if value:
            return value

        if prompt:
            prompt = prompt.rstrip(' ') + ' '

            try:
                value = getpass.getpass(prompt) if is_password else raw_input(prompt)
            except EOFError,ex:
                if error_message is not None:
                    raise CLIError('Unable to read input value: %s' % error_message, ex)
                return None

        if value:
            return value

        if error_message is not None:
            raise CLIError(error_message)

        return None

    def run(self):
        if self._is_verbose:
            print '[--] SMAPI Tool - Using %s (User: %s)' % (self._smapi.server, self._smapi.username)

def run_clitool():
    try:
        cli_app = CLITool()
        exit_code = cli_app.run()
        sys.exit(exit_code)
    except CLIError,ex:
        print >>sys.stderr,str(ex)
        sys.exit(1)

if __name__ == '__main__':
    run_clitool()

__all__ = ['CLITool', 'CLIError', 'run_clitool']
