#!/usr/bin/env python3

import os
import requests
import subprocess
import uuid
import tqdm

CLIENT_ID = ''
TOKEN = ''
DIR = os.path.expanduser('~/src/readmoo/')
UDID = None
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.76 Safari/537.36'
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
        oauthURL = f'https://member.readmoo.com/oauth?client_id={CLIENT_ID}&redirect_uri=app://readmoo/login.html&udid={UDID}&response_type=token&scope=reading,highlight,like,comment,me,library&custom_layout=desktop'
        print(oauthURL)
        return
    s = requests.Session()
    s.headers.update({'User-Agent': USER_AGENT, 'Authorization': f'Client {CLIENT_ID}'})
    me = s.get(f'https://api.readmoo.com/me?access_token={TOKEN}').json()
    user_id = me['user']['id']
    tags = s.get(f'https://api.readmoo.com/me/tags?access_token={TOKEN}').json()
    for tag in tags['items']:
        if tag['tag']['id'] == 'all':
            books = tag['tag']['books']
            break

    if init_pubkey():
        s.post(f'https://api.readmoo.com/me/devices/{UDID}/publickey',
                params={'access_token': TOKEN, 'client_id': CLIENT_ID},
                data={'KeyName': user_id, 'KeyValue': PUBKEY})

    try:
        ls = os.listdir(DIR + 'books')
    except FileNotFoundError:
        os.mkdir(DIR + 'books')
        ls = []
    for book in books:
        if book in ls or f'{book}.zip' in ls:
            continue
        url = f'https://api.readmoo.com/epub/{book}?client_id={CLIENT_ID}&access_token={TOKEN}'
        print(book)
        r = s.get(url, stream=True)
        with tqdm.tqdm(total=int(r.headers.get('content-length', 0)), unit='iB', unit_scale=True, unit_divisor=1024) as t, open(DIR + f'books/{book}.zip', 'wb') as f:
            for d in r.iter_content(1024):
                t.update(len(d))
                f.write(d)

    subprocess.run(['bash', DIR + 'epub.sh'], check=True)


if __name__ == '__main__':
    main()
