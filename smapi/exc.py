'''Defines the basic Exception objects used by SMAPI

All Exceptions are defined here for the whole of the SMAPI package.

'''

import sys

class SMAPIError(Exception):
    '''A general error related to the SMAPI library.

    This class is the base Exception class within SMAPI and provides extended functionality
    to the Exception class. It is a subclass of Exception as well and treatable as such.

    '''

    _values = {'message': None, 'base_ex': None, 'dump_objs': None}

    def __init__(self, message, base_ex=None, dump_objs=None):
        '''Initializes a new SMAPI Error Exception

        Note:
            Once the object is instantiated the values cannot be modified.

        Args:
            message (str): Human-readable error message
            base_ex (`Exception`, optional): Base Exception (if any)
            dump_objs (dict, optional): Objects to associated with this Exception (if any)

        '''
        super(SMAPIError, self).__init__(message)
        self._values = {'message': message, 'base_ex': base_ex, 'dump_objs': dump_objs}

    def dump_objects(self, print_objects=True, use_stderr=True):
        '''Dumps the objects provided to the exception upon creation.

        Dumps objects passed to exception when it was created, optionally printing them out to
        either STDERR or STDOUT. Returns the same textual representation as a list of strings.

        Args:
            print_objects (bool): Determines if the result should be printed to the screen.
            use_stderr (bool): Indicates if the output should be sent to STDERR instead of STDOUT.

        Returns:
            list: The strings textually representing the dumped objects.

        '''
        print_to = sys.stdout
        if use_stderr:
            print_to = sys.stderr

        if not self.dump_objs:
            return None

        obj_names = self.dump_objs.keys()
        cnt = len(self.dump_objs)
        res = '--- Begin Dumped Objects ---\n'

        for obj in obj_names:
            res = '%s -> Object: "%s":\n\t%r\n' % (res, obj, self.dump_objs[obj])
            if cnt - obj_names.index(obj) < 1:
                res = '%s%s\n' % (res, ('-'*30))

        res = '%s%s' % (res, '--- End Dumped Objects ---')

        if print_objects:
            print >>print_to, res

        return res.split('\n')

    def __str__(self):
        return self.message

    def __repr__(self):
        res = '<SMAPIError(message="%s"' % self.message

        if self.base_ex:
            res = '%s, base_ex="%s"' % (res, str(self.base_ex))

        if self.dump_objs:
            res = '%s, dump_objs="%s"' % (res, '", "'.join(self.dump_objs.keys()))

        res = '%s)>' % res

        return res

    message = property(fget=lambda self: self._options['message'],
                       doc='Human-readable error message')
    base_ex = property(fget=lambda self: self._options['base_ex'],
                       doc='Base Exception (if any)')
    dump_objs = property(fget=lambda self: self._options['dump_objs'],
                         doc='Associated dumped objects (if any)')

class ZohoError(SMAPIError):
    '''An error related to calling the Zoho API

    Indicates there was an error while using the `ZohoAPI` class. If possible, the
    :obj:`requests.Response` object is included with this Exception as well.

    Attributes:
        http_response (:obj:`requests.Response`, optional): The HTTP response used
        to make the API request (if available).

    '''

    _options = {}

    def __init__(self, message, base_ex=None, dump_objs=None, http_response=None):
        '''Initializes a new ZohoError Exception indicating an error working with the Zoho API.

        This Exception class is associated with any Zoho-related errors and provides the
        `requests.Response` object when possible as the attribute :obj:`http_response`.

        Args:
            message (str): Human-readable error message
            base_ex (`Exception`, optional): Base Exception (if any)
            dump_objs (dict, optional): Objects to associated with this Exception (if any)
            http_response (`requests.Response`, optional): HTTP response object (if any)

        '''
        super(ZohoError, self).__init__(message, base_ex=base_ex, dump_objs=dump_objs)
        if not http_response and ('http_response' in dump_objs):
            http_response = dump_objs['http_response']
        self._options['http_response'] = http_response

    @property
    def http_response(self):
        '''The `requests.Response` HTTP response object associated with the API (if available)

        If the Response object responsible for making the Zoho API call was available when
        instancing this Exception it will be available as this attribute.

        '''
        return self._options.get('http_response', None)


__all__ = ['SMAPIError', 'ZohoError']
