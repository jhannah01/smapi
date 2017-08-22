import os
import os.path
import logging
import csv

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
            (addr,dom) = usr.lower().split('@')
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
        print "imapsync --dry --host1 hotdesmail.media3.net --host2 imappro.zoho.com --ssl2 --user1 '%(addr)s' --user2 '%(addr)s' --password1 '%(passwd)s' --password2 '%(passwd)s'" % {'addr': addr, 'passwd': passwd}

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

__all__ = ['get_domains', 'get_users', 'get_user', 'get_logger', 'build_zoho_csv', 'build_imapsync_commands']
