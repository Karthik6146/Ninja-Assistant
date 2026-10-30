from datetime import date
from typing import Literal
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from . import db, youtube as yt, youtube_auth as auth

router = APIRouter()


@router.get('/api/youtube')
def overview():
    return {'connection': auth.status(), 'profile': yt.profile(), 'operations': yt.listing()}


class Client(BaseModel):
    installed: dict


@router.post('/api/youtube/client')
def client(body: Client):
    if len(db.encode(body.installed)) > 64000:
        raise ValueError('OAuth client document is too large')
    return auth.configure(body.model_dump())


class Connect(BaseModel):
    manage: bool = True
    analytics: bool = False


@router.post('/api/youtube/connect')
def connect(body: Connect):
    return auth.begin(body.manage, body.analytics)


@router.get('/oauth/youtube/callback', response_class=HTMLResponse)
def callback(state: str = '', code: str = '', error: str = ''):
    try:
        if error or not code or len(code) > 8000 or len(state) > 200:
            raise ValueError('Google sign-in was not completed. Start Connect again.')
        if db.stopped():
            raise ValueError('Emergency stop is active. Resume before connecting.')
        from . import gmail
        if gmail.owns(state):
            gmail.callback(state, code)
            message = 'Gmail connected. Return to Ninja Assistant.'
        else:
            auth.callback(state, code)
            message = 'YouTube connected. Return to Ninja Assistant and select Refresh YouTube.'
    except ValueError:
        message = 'Sign-in was not completed. Check the selected channel, permissions and OAuth configuration, then start Connect again.'
    return HTMLResponse('<!doctype html><title>Ninja Assistant YouTube</title><h1>' + message + '</h1><a href="/">Return to Ninja Assistant</a>',
        headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
                 'Content-Security-Policy': "default-src 'none'; base-uri 'none'; frame-ancestors 'none'"})


@router.get('/api/gmail')
def gmail_status():
    from . import gmail
    return gmail.status()


@router.post('/api/gmail/connect')
def gmail_connect():
    from . import gmail
    return gmail.begin()


class GmailAccount(BaseModel):
    email: str = Field(min_length=3, max_length=200)


@router.post('/api/gmail/disconnect')
def gmail_disconnect(body: GmailAccount):
    from . import gmail
    return gmail.disconnect(body.email)


@router.post('/api/youtube/disconnect')
def disconnect():
    # Forget credentials locally. Google-side revocation is available in the user's Google account.
    auth.vault('tokens', delete=True)
    auth.vault('flow', delete=True)
    return auth.status()


class Profile(BaseModel):
    audience: str = Field(default='', max_length=2000)
    language: str = Field(default='Hinglish', max_length=100)
    pillars: str = Field(default='', max_length=2000)
    tone: str = Field(default='clear and practical', max_length=1000)


@router.put('/api/youtube/profile')
def profile(body: Profile):
    return yt.profile(body.model_dump())


class Generate(BaseModel):
    package: str
    brief: str = Field(min_length=1, max_length=4000)
    evidence: str = Field(default='', max_length=6000)
    scene: str | None = None
    provider: Literal['ollama', 'cloud'] = 'ollama'


@router.post('/api/youtube/generate')
def generate(body: Generate):
    return {'job': db.queue(body.package, 'youtube_generate', body.model_dump())}


@router.post('/api/youtube/operations/{id}/apply')
def apply(id: str):
    return yt.apply_draft(id)


class Prepare(BaseModel):
    package: str
    made_for_kids: bool
    synthetic_media: bool


@router.post('/api/youtube/prepare')
def prepare(body: Prepare):
    return {'job': db.queue(body.package, 'youtube_prepare', body.model_dump())}


@router.post('/api/youtube/operations/{id}/approve')
def approve(id: str):
    return yt.approve(id)


@router.post('/api/youtube/operations/{id}/resume')
def resume(id: str):
    return yt.resume(id)


class Reconcile(BaseModel):
    video: str = Field(pattern=r'^[A-Za-z0-9_-]{11}$')


@router.post('/api/youtube/operations/{id}/reconcile')
def reconcile(id: str, body: Reconcile):
    return yt.reconcile(id, body.video)


class Visibility(BaseModel):
    visibility: Literal['private', 'unlisted', 'public']
    publish_at: str | None = None


@router.post('/api/youtube/operations/{id}/visibility')
def visibility(id: str, body: Visibility):
    return yt.prepare_status(id, body.visibility, body.publish_at)


class Analytics(BaseModel):
    start: date
    end: date


@router.post('/api/youtube/operations/{id}/analytics')
def analytics(id: str, body: Analytics):
    if body.start > body.end or body.end > date.today() or (body.end - body.start).days > 366:
        raise ValueError('Choose an ordered date range up to 366 days ending today or earlier')
    return {'job': db.queue(id, 'youtube_analytics', body.model_dump(mode='json'))}
