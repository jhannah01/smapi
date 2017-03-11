'''The inner framework necessary for interacting with SmarterMail's web services'''

import requests
import bs4
from contextlib import closing

from smapi.exc import SMAPIError

class SMAPI(object):
    _options = {'server': None, 'username': None, 'password': None,
                'use_ssl': None, 'port': None}

    SERVICES = ['DomainAdmin', 'UserAdmin', 'ProductInfo', 'DomainAliasAdmin', 'MailListAdmin',
                'AliasAdmin', 'GlobalUpdate']

    '''
    SERVICES = {'AliasAdmin': ['DeleteAlias', 'UpdateAlias', 'GetAlias', 'AddAlias', 'GetAliases', 'SetCatchAll'],
                'DomainAdmin': ['RenameDomain', 'GetDomainSettings', 'GetDomainInfo', 'AddDomain', 'UpdateDomain',
                                'GetAllDomains', 'GetDomainDefaults', 'UpdateDomainNameAndPath', 'DeleteDomain',
                                'GetDomainStatistics', 'ReloadDomain', 'SetPrimaryDomainAdmin'],
                'MailListAdmin': ['DeleteAllLists'],
                'ProductInfo': ['ActivateLicenseKey', 'GetLicenseInfo', 'GetProductInfo', 'SetLicenseKey'],
                'GlobalUpdate': ['UpdateAllDomainSettings', 'ListGlobalUpdateFields', 'GetGlobalUpdateStatus'],
                'DomainAliasAdmin': ['DeleteDomainAlias', 'GetAliases', 'AddDomainAlias',
                                     'AddDomainAliasWithoutMxCheck'],
                'UserAdmin': ['AddUser', 'GetUserStats', 'GetUser', 'UpdateUserAutoResponseInfo',
                              'UpdateUserForwardingInfo', 'GetUsers', 'DeleteUser', 'GetUserAutoResponseInfo',
                              'GetUserForwardingInfo', 'AuthenticateUser', 'LoginValidated']}
    '''

    def __init__(self, server, username, password, use_ssl=False, port=None):
        if not server:
            raise SMAPIError('No server hostname provided')

        if not username:
            raise SMAPIError('No username provided')

        if not password:
            raise SMAPIError('No password provided')

        self._options = {'server': server, 'username': username,
                         'password': password, 'use_ssl': use_ssl}

        if port:
            try:
                self._options['port'] = int(port)
            except ValueError:
                raise SMAPIError('Invalid port provided: "%s"' % port)
        else:
            self._options['port'] = None

    def _get_option(self, option, **kwargs):
        if option not in self._options:
            options = '", "'.join(self._options.keys())
            raise SMAPIError('Invalid option: "%s". Must be one of "%s"' % (option, options))

        if not self._options[option]:
            if 'default' in kwargs:
                return kwargs['default']
            raise SMAPIError('Invalid value for option "%s"' % option)

        return self._options[option]

    @property
    def server(self):
        return self._get_option('server')

    @property
    def username(self):
        return self._get_option('username')

    @property
    def password(self):
        return self._get_option('password')

    @property
    def use_ssl(self):
        return self._get_option('use_ssl', default=False)

    @property
    def port(self):
        return self._get_option('port', default=None)

    def _get_service_url(self, srv_name, method):
        if srv_name not in self.SERVICES:
            services = '", "'.join(SERVICES.keys())
            raise SMAPIError('Invalid service requested: "%s". Must be one of: "%s"' % (srv_name, services))

        res = 'http'
        if self.use_ssl:
            res = '%ss' % res

        res = '%s://%s' % (res, self.server)

        if self.port:
            res = '%s:%d' % (res, int(self.port))

        return '%s/Services/svc%s.asmx/%s' % (res, srv_name, method)

    def call(self, srv_name, method, params={}, response_handler=None, use_post=True):
        http_method = 'POST'
        if use_post:
            http_method = 'GET'

        srv_url = self._get_service_url(srv_name, method)
        params.update({'AuthUserName': self.username, 'AuthPassword': self.password})

        try:
            with closing(requests.request(http_method, srv_url, params=params)) as req:
                bs = bs4.BeautifulSoup(req.content)
                return bs
        except requests.HTTPError,ex:
            raise SMAPIError('Error calling service: "%s"' % str(ex), base_ex=ex)

__all__ = ['SMAPI']
