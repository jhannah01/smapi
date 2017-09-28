import os
import os.path
import sys
import re
import logging
import csv
import imaplib2

from smapi import __do_debug__, SMAPIError


def get_domains(sm):
    bs = sm.call('DomainAdmin', 'GetAllDomains')
    return map(lambda ent: str(ent.text).lower(), bs.find_all('string'))


def get_users(sm, domain, requested_settings=None, require_extra_info=False):
    bs = sm.call('UserAdmin', 'GetUsers', params={'DomainName': domain})
    users = {}

    for ent in bs.find_all('userinfo'):
        info = dict(map(lambda ent: (str(ent.name), str(ent.text)), ent.find_all()))
        users[info['username']] = info

    if not requested_settings:
        return users

    for usr in users:
        usr_info = None
        try:
            usr_info = get_user(sm, usr, requested_settings=requested_settings)
            users[usr].update(usr_info)
        except SMAPIError as ex:
            if require_extra_info:
                raise ex
            continue
        except Exception as ex:
            _err_msg = 'Unable to determine extra user info for "%s"' % usr
            logger.warn(_err_msg)
            if require_extra_info:
                raise SMAPIError(_err_msg, base_ex=ex)
            continue

    return users


def get_user(sm, address, requested_settings=None):
    if not requested_settings:
        requested_settings = ['isenabled', 'password', 'isdomainadmin', 'enableimapretrieval',
                              'displayname', 'fullname']

    params = {'EmailAddress': address}

    if requested_settings:
        params['requestedSettings'] = map(str.lower, requested_settings)

    bs = sm.call('UserAdmin', 'GetRequestedUserSettings', params)
    return dict(map(lambda ent: str(ent.text).split('='), bs.find('settingvalues').find_all()))


def build_zoho_csv(sm, domain, csv_filename, allow_overwrite=False, include_header=True, create_migration_csv=True):
    if os.path.exists(csv_filename) and not allow_overwrite:
        raise SMAPIError('CSV file "%s" already exists' % csv_filename)

    csv_migration_filename = '%s-mig%s' % os.path.splitext(csv_filename)
    if os.path.exists(csv_migration_filename) and not allow_overwrite:
        raise SMAPIError('CSV migration file "%s" already exists' % csv_migration_filename)

    dom_users = get_users(sm, domain, requested_settings=['password', 'displayname', 'firstname', 'lastname'])
    if not dom_users:
        return None

    rows = []
    csv_header = ['Username', 'Password', 'Firstname', 'Lastname', 'Displayname']
    with open(csv_filename, 'w') as csv_f:
        csv_w = csv.writer(csv_f)
        if include_header:
            csv_w.writerow(csv_header)
            rows.append(csv_header)
        for usr, ent in dom_users.items():
            (addr, dom) = usr.lower().split('@')
            if not ent['firstname']:
                ent['firstname'] = addr.title()
            if not ent['lastname']:
                ent['lastname'] = '(%s)' % dom
            if not ent['displayname']:
                ent['displayname'] = '%s %s' % (ent['firstname'], ent['lastname'])
            row = [addr, ent['password'], ent['firstname'], ent['lastname'], ent['displayname']]
            csv_w.writerow(row)
            rows.append(row)

    if not create_migration_csv:
        return {'sm_accounts': dom_users, 'accounts': rows}

    mig_rows = []
    csv_migration_header = ['Source', 'Password', 'Destination']
    with open(csv_migration_filename, 'w') as csv_f:
        csv_w = csv.writer(csv_f)
        if include_header:
            csv_w.writerow(csv_migration_header)
            mig_rows.append(csv_migration_header)
        for usr, ent in dom_users.items():
            addr = usr.lower()
            row = [addr, ent['password'], addr]
            csv_w.writerow(row)
            mig_rows.append(row)

    return {'sm_accounts': dom_users, 'accounts': rows, 'migration': mig_rows}


def build_imapsync_commands(domain_users, do_dry_run=False):
    for usr in domain_users:
        addr = usr.lower()
        passwd = domain_users[usr].get('password', None)
        if not passwd:
            raise SMAPIError('Unable to find password for account "%s"' % addr)
        print "imapsync --dry --host1 hotdesmail.media3.net --host2 imappro.zoho.com --ssl2 --user1 '%(addr)s'" \
            "--user2 '%(addr)s' --password1 '%(passwd)s' --password2 '%(passwd)s'" % {'addr': addr, 'passwd': passwd}


def parse_imap_folders(folders):
    results = []
    for fdr in folders:
        if '"/"' not in fdr:
            print 'Error on "%s". Cannot parse. Skipping...' % fdr
            continue
        fdr = fdr.split('"/"')[-1]
        m = re.search(r' ?"(?P<folder>.*?)"$', fdr)
        if not m:
            print 'Cannot find match for folder name in "%s". Skipping..' % fdr
            continue
        results.append(m.group('folder'))
    return results


class IMAP_Connection(object):
    _options = {'hostname': None, 'username': None, 'password': None, 'use_ssl': True}
    _imap_conn = None

    def __init__(self, hostname, username=None, password=None, use_ssl=True, do_login=True):
        self._options = {'hostname': hostname, 'username': username, 'password': password, 'use_ssl': use_ssl}
        if do_login:
            self.imap_connection.login(username, password)

    @property
    def imap_connection(self):
        if not self._imap_conn:
            if self._options.get('use_ssl', True):
                self._imap_conn = imaplib2.IMAP4_SSL(self._options['hostname'])
            else:
                self._imap_conn = imaplib2.IMAP4(self._options['hostname'])

        return self._imap_conn

    @property
    def hostname(self):
        return self._options['hostname']

    def login(self, username=None, password=None):
        if not username:
            username = self._options['username']
            if not username:
                raise SMAPIError('No username provided or stored for this connection')

        if not password:
            password = self._options['password']
            if not password:
                raise SMAPIError('No passworde provided or stored for this connection')

        if self.is_authenticated:
            self.logout()

        (typ, data) = self.imap_connection.login(username, password)

        if typ != 'OK':
            if isinstance(data, list) and (len(data) == 1):
                data = data[0]
            raise SMAPIError('Unable to login to IMAP server: "%s"' % data)

        self._options['username'] = username
        self._options['password'] = password

        return True

    def logout(self):
        if self.is_authenticated:
            self._imap_conn.logout()
        self._imap_conn = None

    @property
    def is_connected(self):
        if not self._imap_conn or not self._imap_conn.state:
            return False

        return True

    @property
    def is_authenticated(self):
        if not self._imap_conn:
            return False

        if not self.is_connected:
            return False

        return (self._imap_conn.state is not None)

    def get_folders(self):
        folder_list_re = r'\((?P<flags>.*?)\) "(?P<sep>.*)" "(?P<name>.*)"'
        folders = []

        if not self.is_authenticated:
            self.login()

        (typ, data) = self.imap_connection.list()

        for mbox in data:
            m = re.match(folder_list_re, mbox)
            if not m:
                print >>sys.stderr, 'Warning: Skipping mailbox "%s". Cannot parse.' % mbox
                continue

            folders.append(m.group('name'))

        return folders

    def find_messages(self, mailbox=None):
        messages = {}

        if not self.is_connected or not self.is_authenticated:
            self.login()

        if not mailbox:
            if not (self.imap_connection.state == 'SELECTED'):
                raise SMAPIError('No mailbox provided or previously selected')
        else:
            (typ, data) = self.imap_connection.select(mailbox)
            if (typ != 'OK'):
                if isinstance(data, list) and (len(data) == 1):
                    data = data[0]
                raise SMAPIError('Unable to select mailbox "%s": %s' % (mailbox, data))

        (typ, data) = self.imap_connection.search(None, 'ALL')

        if (typ != 'OK'):
            if isinstance(data, list) and (len(data) == 1):
                data = data[0]
            raise SMAPIError('Unable to search for messages in mailbox: %s' % data)

        for msg in data[0].split(' '):
            (typ, data) = self.imap_connection.fetch(msg, '(BODY[HEADER.FIELDS (MESSAGE-ID)] RFC822)')
            if (typ != 'OK'):
                print >>sys.stderr, 'Warning: Unable to fetch message "%s" from mailbox: %s' % (msg, data)
                continue

            (req, msg_id) = data[0]
            m = re.match(r'Message-ID: <(?P<msg_id>.*)>', msg_id, re.IGNORECASE)
            if not m:
                print >>sys.stderr, 'Warning: Unable to determine message ID for "%s" (Got: %r -> %r)' % (msg, req,
                                                                                                          msg_id)
                continue

            (req, contents) = data[1]
            messages[m.group('msg_id')] = {'id': msg, 'contents': contents}

        return messages


log_level = logging.INFO
if __do_debug__ or os.environ.get('SMAPI_DEBUG', True):
    log_level = logging.DEBUG


def get_logger(name, log_fmt=None):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    handler = logging.StreamHandler()
    handler.setLevel(log_level)

    if not log_fmt:
        log_fmt = logging.Formatter('[%(name)-12s: %(levelname)-8s] %(message)s')

    handler.setFormatter(log_fmt)
    logger.addHandler(handler)

    return logger


logger = get_logger('smapi.helpers')

__all__ = ['get_domains', 'get_users', 'get_user', 'get_logger', 'build_zoho_csv', 'build_imapsync_commands',
           'parse_imap_folders', 'IMAP_Connection']
