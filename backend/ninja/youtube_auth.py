"""Desktop Google OAuth. Secrets stay encrypted for the current Windows user."""
import base64
import ctypes
import hashlib
import json
import logging
import os
import re
import secrets
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from urllib.parse import urlencode, urlsplit

import httpx
from filelock import FileLock
from .config import DATA
from . import db

_target=ContextVar('youtube_target',default=('legacy',None))

def token_key(connection):
    if connection!='legacy' and not re.fullmatch(r'[a-f0-9]{32}',connection):raise ValueError('Invalid YouTube connection')
    return 'tokens' if connection=='legacy' else 'tokens-'+connection

@contextmanager
def target(connection='legacy',channel=None):
    tokens=vault(token_key(connection))
    if not tokens or (channel and tokens['channel']['id']!=channel):raise ValueError('Reconnect the authorized Google connection for this exact channel in Settings')
    marker=_target.set((connection,channel or tokens['channel']['id']))
    try:yield
    finally:_target.reset(marker)

def binding():
    connection,channel=_target.get()
    return {'connection':connection,'channel':channel or status()['channel']['id']}

def remember(connection,tokens):
    channel=tokens['channel'];body={**channel,'verified':True,'connected':True,'connection':connection,'defaults':{}}
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        old=c.execute('SELECT body FROM youtube_channels WHERE id=?',(channel['id'],)).fetchone()
        if old:
            saved=json.loads(old[0]);body['defaults']=saved.get('defaults',{})
            if 'profile' in saved:body['profile']=saved['profile']
        c.execute('INSERT OR REPLACE INTO youtube_channels VALUES(?,?,?)',(channel['id'],connection,db.encode(body)))

def channels():
    legacy=vault('tokens')
    if legacy:
        with db.connect() as c:exists=c.execute('SELECT 1 FROM youtube_channels WHERE id=?',(legacy['channel']['id'],)).fetchone()
        if not exists:remember('legacy',legacy)
    with db.connect() as c:rows=c.execute('SELECT body FROM youtube_channels ORDER BY rowid').fetchall()
    result=[]
    for row in rows:
        value=json.loads(row[0]);tokens=vault(token_key(value['connection']))
        value['connected']=bool(tokens and tokens['channel']['id']==value['id'])
        value['health']='Connected; token refreshes when needed' if value['connected'] else 'Reconnect this channel in Settings'
        result.append(value)
    return result

def connection_for(channel):
    for item in channels():
        if item['id']==channel and item['connected']:return item['connection']
    raise ValueError('Connect and verify this YouTube channel in Settings first')

SCOPES = {
    'upload': 'https://www.googleapis.com/auth/youtube.upload',
    'read': 'https://www.googleapis.com/auth/youtube.readonly',
    'manage': 'https://www.googleapis.com/auth/youtube.force-ssl',
    'analytics': 'https://www.googleapis.com/auth/yt-analytics.readonly',
}
REDIRECT = 'http://127.0.0.1:8000/oauth/youtube/callback'


class HideOAuthQuery(logging.Filter):
    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            if str(args[2]).startswith('/oauth/youtube/callback'):
                args[2] = '/oauth/youtube/callback'
                record.args = tuple(args)
        return True


logging.getLogger('uvicorn.access').addFilter(HideOAuthQuery())


def _crypt(raw, decrypt=False):
    if os.name != 'nt':
        raise ValueError('YouTube credential storage currently requires Windows DPAPI')
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

    buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    source, target = Blob(len(raw), buffer), Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ValueError('Windows could not unlock/store the YouTube credentials')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))


def vault(name, value=None, delete=False):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', name):
        raise ValueError('Invalid credential key')
    folder = DATA / 'youtube-secrets'
    folder.mkdir(exist_ok=True)
    path = folder / (name + '.bin')
    with FileLock(str(path) + '.lock', timeout=15):
        if delete:
            path.unlink(missing_ok=True)
            return None
        if value is not None:
            temp = path.with_suffix('.tmp')
            temp.write_bytes(_crypt(json.dumps(value).encode()))
            temp.replace(path)
            return value
        return json.loads(_crypt(path.read_bytes(), True)) if path.exists() else None


def request(method, url, **kwargs):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in
        {'oauth2.googleapis.com', 'www.googleapis.com', 'youtube.googleapis.com', 'youtubeanalytics.googleapis.com', 'gmail.googleapis.com'}
        or parsed.port not in (None, 443) or parsed.username or parsed.password):
        raise ValueError('Invalid Google API destination')
    try:
        response = httpx.request(method, url, timeout=90, follow_redirects=False, **kwargs)
    except httpx.HTTPError:
        raise ValueError('Google connection interrupted; retry or reconcile the existing operation') from None
    return response


def checked(response):
    if not 200 <= response.status_code < 300:
        # Never echo tokens, upload-session URLs, or provider response bodies to logs/UI.
        raise ValueError(f'Google API returned HTTP {response.status_code}; check permissions, quota and account access')
    return response.json()


def configure(document):
    client = document.get('installed', {})
    if not (isinstance(client.get('client_id'), str) and client['client_id'].endswith('.apps.googleusercontent.com')
            and isinstance(client.get('client_secret'), str) and 0 < len(client['client_secret']) < 1000):
        raise ValueError('Choose the Google OAuth Desktop app client JSON downloaded from Google Cloud')
    if vault('tokens'):
        raise ValueError('Disconnect the current channel before replacing its OAuth client')
    vault('client', {'client_id': client['client_id'], 'client_secret': client['client_secret']})
    vault('flow', delete=True)
    return status()


def status():
    tokens = vault(token_key(_target.get()[0]))
    return {'configured': bool(vault('client')), 'connected': bool(tokens),
            'channel': tokens.get('channel') if tokens else None,
            'permissions': [k for k, v in SCOPES.items() if tokens and v in tokens.get('scope', '').split()]}


def begin(manage=False, analytics=False, additional=False):
    client = vault('client')
    if not client:
        raise ValueError('Import a Google Desktop OAuth client JSON first')
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    scopes = [SCOPES['upload'], SCOPES['read']]
    scopes += [SCOPES[k] for k, enabled in [('manage', manage), ('analytics', analytics)] if enabled]
    vault('flow-'+hashlib.sha256(state.encode()).hexdigest() if additional else 'flow', {'state': state, 'verifier': verifier, 'expires': time.time() + 600, 'scopes': scopes,'connection':uuid.uuid4().hex if additional else 'legacy','client':client})
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    return {'url': 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
        'client_id': client['client_id'], 'redirect_uri': REDIRECT, 'response_type': 'code',
        'scope': ' '.join(scopes), 'state': state, 'code_challenge': challenge,
        'code_challenge_method': 'S256', 'access_type': 'offline', 'prompt': 'consent'})}


def callback(state, code):
    with FileLock(DATA / 'youtube-oauth.lock', timeout=15):
        key='flow-'+hashlib.sha256(state.encode()).hexdigest()
        flow=vault(key)
        if not flow:key='flow';flow=vault(key)
        if not flow or flow['expires'] < time.time() or not secrets.compare_digest(state.encode(), flow['state'].encode()):
            raise ValueError('Expired or invalid sign-in. Start Connect again in Ninja Assistant.')
        vault(key, delete=True)
        client = flow.get('client') or vault('client')
        tokens = checked(request('POST', 'https://oauth2.googleapis.com/token', data={
            **client, 'code': code, 'code_verifier': flow['verifier'], 'redirect_uri': REDIRECT,
            'grant_type': 'authorization_code'}))
        if not tokens.get('access_token') or not tokens.get('refresh_token'):
            raise ValueError('Google did not grant offline access; reconnect and consent again')
        tokens['expires'] = time.time() + tokens.get('expires_in', 3600)
        tokens['scope'] = tokens.get('scope', '')
        if not {SCOPES['upload'], SCOPES['read']} <= set(tokens['scope'].split()):
            raise ValueError('YouTube upload and read permissions are required')
        result = checked(request('GET', 'https://www.googleapis.com/youtube/v3/channels',
            params={'part': 'snippet', 'mine': 'true'}, headers={'Authorization': 'Bearer ' + tokens['access_token']}))
        channels = result.get('items', [])
        if len(channels) != 1:
            raise ValueError('Select an account with exactly one YouTube channel, then reconnect')
        tokens['channel'] = {'id': channels[0]['id'], 'title': channels[0]['snippet']['title'],'avatar':channels[0]['snippet'].get('thumbnails',{}).get('default',{}).get('url','')}
        tokens['client']=client
        connection=flow.get('connection','legacy')
        vault(token_key(connection), tokens);remember(connection,tokens)
    with target(connection,tokens['channel']['id']):return status()


def headers(permission='read'):
    with FileLock(DATA / 'youtube-oauth.lock', timeout=15):
        connection,expected=_target.get();key=token_key(connection);tokens = vault(key)
        if tokens and expected and tokens['channel']['id']!=expected:raise ValueError('Authorized connection no longer matches the immutable upload target')
        if not tokens or SCOPES[permission] not in tokens.get('scope', '').split():
            raise ValueError(f'Connect YouTube with {permission} permission first')
        if tokens['expires'] < time.time() + 120:
            refreshed = checked(request('POST', 'https://oauth2.googleapis.com/token', data={
                **(tokens.get('client') or vault('client')), 'refresh_token': tokens['refresh_token'], 'grant_type': 'refresh_token'}))
            tokens.update(refreshed)
            tokens['expires'] = time.time() + refreshed.get('expires_in', 3600)
            vault(key, tokens)
        return {'Authorization': 'Bearer ' + tokens['access_token']}


def api(method, resource, permission='read', **kwargs):
    return checked(request(method, 'https://www.googleapis.com/youtube/v3/' + resource,
                           headers=headers(permission), **kwargs))
