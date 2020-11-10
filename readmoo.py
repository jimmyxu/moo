#!/usr/bin/env python3

import datetime
import os
import requests
import subprocess
import uuid
import tqdm

CLIENT_ID = ''
TOKEN = ''
DIR = os.path.expanduser('~/src/readmoo/')
UDID = None
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
PUBKEY = None

def init_udid():
    global UDID
    try:
        with open(DIR + 'udid.txt') as f:
            UDID = f.read().strip()
    except IOError:
        pass
    if not UDID:
        UDID = str(uuid.uuid4())
        with open(DIR + 'udid.txt', 'w') as f:
            f.write(UDID)

def init_pubkey():
    global PUBKEY
    ret = False
    if not os.path.exists(DIR + 'rsa.pub'):
        subprocess.run(['openssl', 'genrsa', '-out', DIR + 'rsa.key', '1024'], check=True)
        subprocess.run(['openssl', 'rsa', '-in', DIR + 'rsa.key', '-pubout', '-out', DIR + 'rsa.pub'], check=True)
        ret = True
    with open(DIR + 'rsa.pub') as f:
        PUBKEY = f.read()
    return ret

def main():
    init_udid()

    if not TOKEN:
        oauthURL = f'https://member.readmoo.com/oauth?client_id={CLIENT_ID}&redirect_uri=http://localhost:3300&response_type=token&scope=me,reading,highlight,like,comment,library,book,subscription,forever,wishlist&state=&udid={UDID}'
        print(oauthURL)
        return
    s = requests.Session()
    s.headers.update({
        'User-Agent': USER_AGENT,
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/vnd.api+json',
        })

    books = []
    offset = 0
    while True:
        r = s.get(f'https://api.readmoo.com/store/v3/me/library_items', params={'page[count]': 100, 'page[offset]': offset}).json()
        if not r['data']:
            break
        if 'included' in r:
            books += [x['id'] for x in r['included'] if x['type'] == 'books']
        offset += 100

    if init_pubkey():
        s.patch(f'https://api.readmoo.com/store/v3/me/devices/{UDID}',
                json={'data': {
                    'type': 'devices',
                    'id': UDID,
                    'attributes': {
                        'name': 'MacIntel',
                        'info': 'MacIntel',
                        'device_type': 'desktop',
                        'user_agent': USER_AGENT,
                        'registered_at': datetime.datetime.now().isoformat()[:-3] + 'Z',
                        'key': {
                            'algorithm': 'http://www.w3.org/2001/04/xmlenc#rsa-1_5',
                            'name': UDID,
                            'value': PUBKEY,
                            },
                        },
                    }})

    try:
        ls = os.listdir(DIR + 'books')
    except FileNotFoundError:
        os.mkdir(DIR + 'books')
        ls = []
    for book in books:
        if book in ls or f'{book}.zip' in ls:
            continue
        print(book)
        lcpl = s.get(f'https://api.readmoo.com/lcpl/{book}').json()
        ck = lcpl['encryption']['content_key']['encrypted_value']
        with open(DIR + f'books/{book}.key', 'w') as f:
            f.write(ck)
        url = {x['rel']: x['href'] for x in lcpl['links']}['publication']
        r = s.get(url, stream=True)
        with tqdm.tqdm(total=int(r.headers.get('content-length', 0)), unit='iB', unit_scale=True, unit_divisor=1024) as t, open(DIR + f'books/{book}.zip', 'wb') as f:
            for d in r.iter_content(1024):
                t.update(len(d))
                f.write(d)

    subprocess.run([DIR + 'epub.sh'], check=True)


if __name__ == '__main__':
    main()
