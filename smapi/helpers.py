def get_domains(sm):
    bs = sm.call('DomainAdmin', 'GetAllDomains')
    return map(lambda ent: str(ent.text).lower(), bs.find_all('string'))

def get_users(sm, domain):
    bs = sm.call('UserAdmin', 'GetUsers', params={'DomainName': domain})
    users = {}

    for ent in bs.find_all('userinfo'):
        info = dict(map(lambda ent: (str(ent.name), str(ent.text)), u.find_all()))
        users[info['username']] = info

    return users

def get_user(sm, address, requested_settings=None):
    if not requested_settings:
        requested_settings = ['isenabled', 'password', 'isdomainadmin', 'enableimapretrieval',
                              'displayname', 'fullname']

    params = {'EmailAddress': address}

    if requested_settings:
        params['requestedSettings'] = map(str.lower, requested_settings)

    bs = sm.call('UserAdmin', 'GetRequestedUserSettings', params)
    return map(lambda ent: str(ent.text).split('='), bs.find('settingvalues').find_all())

__all__ = ['get_domains', 'get_users', 'get_user']
