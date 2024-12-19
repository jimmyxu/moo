#!/usr/bin/env python3

import base64
import datetime
import json
import os
import requests
import subprocess
import tqdm
import uuid

CLIENT_ID = ''
AUTHORIZATION_CODE = ''
DIR = os.path.expanduser('~/src/readmoo/')
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

def init_udid():
    try:
        with open(DIR + 'udid.txt') as f:
            udid = f.read().strip()
    except IOError:
        pass
    if not udid:
        udid = str(uuid.uuid4())
        with open(DIR + 'udid.txt', 'w') as f:
            f.write(udid)
    return udid

def init_pubkey():
    if not os.path.exists(DIR + 'rsa.pub'):
        subprocess.run(['openssl', 'genrsa', '-out', DIR + 'rsa.key', '1024'], check=True)
        subprocess.run(['openssl', 'rsa', '-in', DIR + 'rsa.key', '-pubout', '-out', DIR + 'rsa.pub'], check=True)
    with open(DIR + 'rsa.pub') as f:
        return f.read()

def main():
    udid = init_udid()
    pubkey = init_pubkey()

    s = requests.Session()
    s.headers.update({
        'User-Agent': USER_AGENT,
        })

    token = input('access_token=')

    if not token:
        redirect_uri = 'readmoodesktoplogin://oauth2-login'
        scope = requests.utils.quote('aws.cognito.signin.user.admin email openid profile Galao/email Galao/profile Galao/user_id')
        state = json.dumps({'device_id': udid, 'device_name': 'Mac'});
        state = base64.urlsafe_b64encode(state.encode()).decode().rstrip('=')
        oauthURL = f'https://member.readmoo.com/oauth2/signin?client_id={CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={scope}&state={state}'

        print(oauthURL)
        code = input('code=')
        r = s.post('https://member.readmoo.com/oauth2/token',
                data={
                    'client_id': CLIENT_ID,
                    'redirect_uri': redirect_uri,
                    'code': code,
                    'grant_type': 'authorization_code'},
                headers={
                    'Authorization': AUTHORIZATION_CODE}).json()
        token = r['access_token']
        if not token:
            print(r)
            return
        print(token)

    s.headers.update({
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/vnd.api+json',
        })

    s.patch(f'https://api.readmoo.com/store/v3/me/devices/{udid}',
            json={'data': {
                'type': 'devices',
                'id': udid,
                'attributes': {
                    'name': 'MacIntel',
                    'info': 'MacIntel',
                    'device_type': 'desktop',
                    'user_agent': USER_AGENT,
                    'registered_at': datetime.datetime.now(datetime.UTC).isoformat()[:-9] + 'Z',
                    'key': {
                        'algorithm': 'http://www.w3.org/2001/04/xmlenc#rsa-1_5',
                        'name': udid,
                        'value': pubkey,
                        },
                    },
                }})

    books = []
    offset = 0
    while True:
        r = s.get(f'https://api.readmoo.com/store/v3/me/library_items', params={'page[count]': 100, 'page[offset]': offset}).json()
        if not r['data']:
            break
        if 'included' in r:
            books += [(x['id'], x['attributes']['epub']['latest_version'], x['attributes']['title']) for x in r['included'] if x['type'] == 'books']
        offset += 100

    try:
        ls = os.listdir(DIR + 'books')
    except FileNotFoundError:
        os.mkdir(DIR + 'books')
        ls = []
    for book in books:
        bookid, version, title = book
        fn = f'{bookid}-{version}' if version != '1.000' else bookid
        if any(x for x in ls if x.startswith(fn) and x.endswith(('.epub', '.zip'))):
            continue
        print(bookid, version, title)
        lcpl = s.get(f'https://api.readmoo.com/lcpl/{bookid}')
        try:
            lcpl = lcpl.json()
        except ValueError:
            print(lcpl, lcpl.text)
            continue
        ck = lcpl['encryption']['content_key']['encrypted_value']
        with open(DIR + f'books/{fn}.key', 'w') as f:
            f.write(ck)
        url = {x['rel']: x['href'] for x in lcpl['links']}['publication']
        r = s.get(url, stream=True)
        with tqdm.tqdm(total=int(r.headers.get('content-length', 0)), unit='iB', unit_scale=True, unit_divisor=1024) as t, open(DIR + f'books/{fn}.zip', 'wb') as f:
            for d in r.iter_content(1024):
                t.update(len(d))
                f.write(d)

    subprocess.run([DIR + 'epub.sh'], check=True)


if __name__ == '__main__':
    main()
