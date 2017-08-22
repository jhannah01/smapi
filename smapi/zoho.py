import re
import logging

from smapi.helpers import get_logger
from smapi.exc import ZohoError

import requests
from contextlib import closing
from simplejson import JSONDecodeError


logger = get_logger('smapi.zoho')


class ZohoAPI(object):
    '''Provides an interface to the Zoho REST API interface.

    This class takes care of interacting with the Zoho API as well as creating new API tokens
    given the correct Zoho credentials (see the `fetch_token` class method).

    Attributes:
        token (str): The API token for communicating with the Zoho API.
        email_id (str, optional): The e-mail account associated with the API token.
        org_id (int): The Zoho Organization ID (fetched if not already determined).

    '''

    _SCOPES = {'mail': 'ZohoMail/ZohoMailAPI', 'crm': 'ZohoCRM/crmapi'}
    _API_BASE_URI = 'https://mail.zoho.com/api'
    _TOKEN_BASE_URI = 'https://accounts.zoho.com/apiauthtoken/nb/create'
    _options = {'email_id': None, 'token': None, 'org_id': None}

    @classmethod
    def _log(cls, error_message, log_level=logging.ERROR, dump_objs=None, throw_exception=False, exception=None,
             exception_args=None):
        '''Internal method for logging and optionally throwing a `ZohoError` exception.

        This method will use the class-specific logger and log any error messages. If also
        indicated, this method will generate a `ZohoError` Exception based on the provided
        parameters.

        Args:
            error_message (str): Message to log (this also becomes the `ZohoError.message` value)
            log_level (int, optional): Determines which log level to use (defaults to ERROR). This
            value should be one of the log levels defined in `logging`.
            dump_objs (dict, optional): An optional dict to dump along with the log message. If
            a ZohoError exception is generated these are passed along as well.
            throw_exception (bool, optional): Indicates if a ZohoError Exception should be generated. This
            defaults to False.
            exception (:obj:`ZohoError`, optional): A pre-created ZohoError Exception to use explicitly.
            exception_args (dict, optional): This dict will be passed as keyword arguments to the
            ZohoError Exception, if created.


        '''
        logger.log(log_level, error_message)

        if dump_objs and isinstance(dump_objs, dict):
            logger.log(log_level, '-- Begin Dumped Objects --')
            cnt = len(dump_objs)
            obj_names = dump_objs.keys()
            for obj_name in obj_names:
                logger.log(log_level, '- %s:' % obj_name)
                logger.log(log_level, '\t%r' % dump_objs[obj_name])
                if ((cnt - obj_names.index(obj_name)) < 1):
                    logger.log(log_level, '------------------')
            logger.log(log_level, '-- End Dumped Objects --')

        if throw_exception:
            if exception and isinstance(exception, Exception):
                raise exception

            ex_args = {}

            if exception_args:
                ex_args = exception_args

            raise ZohoError(error_message, **ex_args)

    @classmethod
    def fetch_token(cls, email_id, password, use_exceptions=True, scope_name=None):
        token = None
        scope = cls._SCOPES['mail']

        if scope_name:
            if re.match(r'^Zoho\w+\/\w+$', scope_name):
                scope = scope_name
            else:
                scope_name = scope_name.lower()
                scope = cls._SCOPES.get(scope_name, None)
                if not scope:
                    _err_msg = 'Invalid scope_name: "%s". Must be one of "%s"' % (scope_name,
                                                                                  '", "'.join(cls._SCOPES.keys()))
                    cls._log(_err_msg, throw_exception=use_exceptions)
                    return None

        params = {'EMAIL_ID': email_id, 'PASSWORD': password, 'SCOPE': scope}
        token = None
        with closing(requests.get(cls._TOKEN_BASE_URI, params=params)) as resp:
            try:
                if not resp:
                    cls._log('No response from API token request', throw_exception=use_exceptions,
                             exception_args={'http_response': resp})
                    return None

                if resp.status_code != 200:
                    cls._log('HTTP Error %d (%s): %s' % (resp.status_code, resp.reason, resp.content),
                             throw_exception=use_exceptions, exception_args={'http_response': resp})
                    return None

                ents = resp.json()

                if not ents:
                    cls._log('Unable to fetch API token, invalid response: "%r"' % resp.content,
                             throw_exception=use_exceptions, exception_args={'http_response': resp})
                    return None

                if 'RESULT' not in ents or (ents['RESULT'] != 'TRUE'):
                    cls._log('Invalid AUTHTOKEN response: %r' % ents, throw_exception=use_exceptions,
                             exception_args={'http_response': resp})
                    return None

                return ents.get('AUTHTOKEN', None)
            except JSONDecodeError as ex:
                ents = dict(re.findall(r'^(?!#)(?P<key>.*)=(?P<value>.*)$', resp.content, re.MULTILINE))
                if not ents:
                    cls._log('Unable to fetch API token, invalid response: "%r"' % resp.content,
                             throw_exception=use_exceptions, exception_args={'http_response': resp, 'base_ex': ex})
                    return None

                if 'RESULT' not in ents or (ents['RESULT'] != 'TRUE'):
                    cls._log('Invalid AUTHTOKEN response: %r' % ents, throw_exception=use_exceptions,
                             exception_args={'http_response': resp})
                    return None

                return ents.get('AUTHTOKEN', None)
            except requests.exceptions.HTTPError as ex:
                _err_msg = 'HTTP Error: %s' % str(ex)
                if ex.response:
                    _err_msg = '%s [%s %s]' % (_err_msg, ex.response.status_code, ex.response.reason)
                cls._log(_err_msg, throw_exception=use_exceptions, exception_args={'http_response': resp})
                return None

            if not token:
                cls._log('No AUTHTOKEN was returned by API', throw_exception=use_exceptions,
                         exception_args={'http_response': resp})
                return None

            return token

    @classmethod
    def _get_scope(cls, scope_name, use_exceptions=True):
        scope = cls._SCOPES['mail']

        if not scope_name:
            return scope

        if re.match(r'^Zoho\w+\/\w+$', scope_name):
            return scope_name

        scope_name = scope_name.lower()
        scope = cls._SCOPES.get(scope_name, None)
        if not scope:
            _err_msg = 'Invalid scope_name: "%s". Must be one of "%s"' % (scope_name,
                                                                          '", "'.join(cls._SCOPES.keys()))
            cls._log(_err_msg, throw_exception=use_exceptions)
            return None

        return scope

    @classmethod
    def from_email_id(cls, email_id, password, scope_name=None):
        token = cls.fetch_token(email_id, password, scope_name=scope_name, use_exceptions=False)
        if not token:
            cls._log('Unable to generate API token for "%s"' % email_id, log_level=logging.WARN)
            return None
        return ZohoAPI(token, email_id=email_id, scope_name=scope_name)

    def __init__(self, token, email_id=None, scope_name=None, fetch_token=False):
        scope = self._SCOPES['mail']
        if scope_name:
            scope = self._get_scope(scope_name)

        if fetch_token or not re.match(r'^[a-z0-9]{32}$', token):
            if not email_id:
                self._log('Unable to fetch a token without specifying an email_id', throw_exception=True)
            token = self.fetch_token(email_id, token)
            if not token:
                self._log('No Zoho API Token Provided', throw_exception=True)
                return None # Never reached, exception thrown above

        self._options.update({'email_id': email_id, 'token': token, 'scope': scope})

    def _call_zoho(self, path, params=None, method='GET', use_exceptions=True):
        method = method.upper()
        if method not in ['GET', 'POST', 'PUT', 'DELETE']:
            self._log('Invalid HTTP method: "%s"' % method, throw_exception=use_exceptions)
            return None

        u = '%s/%s' % (self._API_BASE_URI, path)

        req_args = {'headers': {'Authorization': 'Zoho-authtoken %s' % self.token}}
        if not params:
            params = {}

        #params.update({'AUTHTOKEN': token})

        if params:
            req_args['params'] = params

        res = None

        with closing(requests.request(method, u, **req_args)) as resp:
            try:
                if not resp:
                    self._log('No HTTP response', throw_exception=use_exceptions)
                    return None

                res_json = resp.json()
                if not res_json:
                    self._log('No valid response from Zoho API', throw_exception=use_exceptions)
                    return None

                res = res_json.get('data', None)

                res_status = res_json.get('status', None)
                if res_status and (resp.status_code != 200):
                    err_description = res_status.get('description', 'Unknown Error')
                    if res:
                        log_level = logging.WARN
                        throw_exception = False
                        exception_args = None
                        err_message = 'Non-fatal HTTP warning: %s (HTTP Code: %s - %s)'
                    else:
                        log_level = logging.ERROR
                        throw_exception = True
                        exception_args = {'http_response': resp}
                        err_message = 'HTTP Error from Zoho API: %s (HTTP Code: %s - %s)'
                    self._log(err_message % (err_description, resp.status_code, resp.reason), log_level=log_level,
                              throw_exception=throw_exception, exception_args=exception_args)
            except JSONDecodeError as ex:
                self._log('JSON Decoding Error: %s' % str(ex), throw_exception=use_exceptions,
                          exception_args={'http_response': resp, 'base_ex': ex})
                return None
            except RequestException as ex:
                _err_msg = 'HTTP Error: %s' % str(ex)
                if ex.response:
                    _err_msg = '%s [%s %s]' % (_err_msg, ex.response.status_code, ex.response.reason)
                self._log(_err_msg, throw_exception=use_exceptions, exception_args={'http_response': resp,
                                                                                    'base_ex': ex})
                return None
            except Exception as ex:
                self._log('General Error calling API: %s' % str(ex), throw_exception=use_exceptions,
                          exception_args={'http_response': resp, 'base_ex': ex})
                return None

        if not res:
            self._log('No valid response from Zoho API', throw_exception=use_exceptions)

        return res

    #@property
    #def org_id(self):
    #    _org_id = self._options.get('org_id', None)
    #    if not _org_id:
    #        return self.get_organization_id()
    #    return _org_id

    email_id = property(fget=lambda self: self._options.get('email_id', None), doc='Zoho email ID')
    token = property(fget=lambda self: self._options.get('token', None), doc='Zoho API Token')

__all__ = ['ZohoAPI']
