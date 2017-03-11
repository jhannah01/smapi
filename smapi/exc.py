'''Defines the basic Exception objects used by smapi'''

class SMAPIError(Exception):
    '''A general error related to the smapi library'''

    def __init__(self, message, base_ex=None):
        super(SMAPIError, self).__init__(message)
        self.message = message
        self.base_ex = base_ex

__all__ = ['SMAPIError']
