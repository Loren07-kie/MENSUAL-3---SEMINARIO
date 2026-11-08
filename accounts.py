"""Cuentas de Nexo Lab: tablas propias, sesiones revocables y CSRF."""
from contextlib import contextmanager
from datetime import timedelta
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
import uuid

from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

auth = Blueprint('accounts', __name__, url_prefix='/api/auth')
SCHEMA_LOCK = threading.Lock()


class DatabaseUnavailable(Exception):
    pass


def configure_accounts(app):
    url = os.environ.get('NEXO_DATABASE_URL', '')
    secret = os.environ.get('NEXO_SECRET_KEY')
    # La URL contiene una contraseña aleatoria; separación de dominio para
    # derivar una clave de sesión sin publicar ni duplicar esa credencial.
    if not secret and url:
        secret = hashlib.sha256(('nexo-lab-session-v1\0'+url).encode()).hexdigest()
    app.config.update(
        SECRET_KEY=secret or secrets.token_hex(32), NEXO_DATABASE_URL=url,
        NEXO_AUTH_SQLITE=None if os.environ.get('RENDER') else str(Path(__file__).parent/'data'/'accounts.sqlite3'),
        SESSION_COOKIE_NAME='nexo_session', SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=bool(os.environ.get('RENDER')),
        SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        SESSION_REFRESH_EACH_REQUEST=False,
    )
    app.register_blueprint(auth)


class Queries:
    def __init__(self, connection, postgres):
        self.connection, self.postgres = connection, postgres

    def execute(self, sql, args=()):
        if self.postgres:
            sql = sql.replace('?', '%s')
        return self.connection.execute(sql, args)


@contextmanager
def database():
    url = current_app.config.get('NEXO_DATABASE_URL')
    local = current_app.config.get('NEXO_AUTH_SQLITE')
    try:
        if url:
            import psycopg
            from psycopg.rows import dict_row
            con = psycopg.connect(url, connect_timeout=8, row_factory=dict_row)
        elif local:
            con = sqlite3.connect(local, timeout=8)
            con.row_factory = sqlite3.Row
            con.execute('PRAGMA foreign_keys=ON')
        else:
            raise DatabaseUnavailable()
    except Exception as exc:
        raise DatabaseUnavailable() from exc
    try:
        yield Queries(con, bool(url))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def ensure_schema():
    config = current_app.config
    identity = config.get('NEXO_DATABASE_URL') or config.get('NEXO_AUTH_SQLITE')
    if identity and config.get('_NEXO_SCHEMA_READY') == identity:
        return
    with SCHEMA_LOCK:
        if identity and config.get('_NEXO_SCHEMA_READY') == identity:
            return
        try:
            with database() as db:
                db.execute('''CREATE TABLE IF NOT EXISTS nexo_lab_users (
                    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
                    created_at BIGINT NOT NULL)''')
                db.execute('''CREATE TABLE IF NOT EXISTS nexo_lab_sessions (
                    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES nexo_lab_users(id) ON DELETE CASCADE,
                    expires_at BIGINT NOT NULL)''')
                db.execute('''CREATE TABLE IF NOT EXISTS nexo_lab_auth_limits (
                    bucket_key TEXT PRIMARY KEY, hits INTEGER NOT NULL, expires_at BIGINT NOT NULL)''')
                db.execute('CREATE INDEX IF NOT EXISTS nexo_lab_session_expiry ON nexo_lab_sessions(expires_at)')
            config['_NEXO_SCHEMA_READY'] = identity
        except Exception as exc:
            raise DatabaseUnavailable() from exc


def csrf_token():
    if not session.get('csrf'):
        session['csrf'] = secrets.token_urlsafe(32)
    return session['csrf']


@auth.before_request
def protect_auth():
    if request.method == 'POST':
        if request.content_length and request.content_length > 8192:
            return jsonify(error='El formulario supera el tamaño permitido.'), 413
        actual = request.headers.get('X-CSRF-Token', '')
        expected = session.get('csrf', '')
        if not expected or not hmac.compare_digest(actual, expected):
            return jsonify(error='La sesión del formulario cambió. Actualiza la página e inténtalo otra vez.', code='csrf'), 403


@auth.errorhandler(DatabaseUnavailable)
def database_error(_error):
    return jsonify(error='Las cuentas aún no están disponibles. Falta completar o revisar la conexión de la base de datos.', code='database_unavailable'), 503


def public_user(row):
    return {'id':row['id'], 'username':row['username'], 'name':row['display_name']}


def current_user():
    token = session.get('auth_token')
    if not token:
        return None
    ensure_schema()
    hashed = hashlib.sha256(token.encode()).hexdigest()
    with database() as db:
        user = db.execute('''SELECT u.id,u.username,u.display_name FROM nexo_lab_users u
            JOIN nexo_lab_sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>?''',
            (hashed,int(time.time()))).fetchone()
    if not user:
        session.pop('auth_token',None)
        return None
    return public_user(user)


def limit_attempts(action):
    ensure_schema()
    now = int(time.time())
    # Render termina TLS y entrega una sola IP de visitante en su proxy.
    address = request.remote_addr or 'unknown'
    digest = hmac.new(current_app.secret_key.encode(), (action+'|'+address+'|'+str(now//900)).encode(), hashlib.sha256).hexdigest()
    with database() as db:
        db.execute('DELETE FROM nexo_lab_auth_limits WHERE expires_at<?',(now,))
        row = db.execute('''INSERT INTO nexo_lab_auth_limits(bucket_key,hits,expires_at) VALUES(?,1,?)
            ON CONFLICT(bucket_key) DO UPDATE SET hits=nexo_lab_auth_limits.hits+1 RETURNING hits''',(digest,now+1800)).fetchone()
    return row['hits'] <= (10 if action=='register' else 25)


def establish_session(user_id):
    previous = session.get('auth_token')
    token = secrets.token_urlsafe(48)
    now = int(time.time())
    with database() as db:
        if previous:
            db.execute('DELETE FROM nexo_lab_sessions WHERE token_hash=?',(hashlib.sha256(previous.encode()).hexdigest(),))
        db.execute('DELETE FROM nexo_lab_sessions WHERE expires_at<?',(now,))
        db.execute('INSERT INTO nexo_lab_sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                   (hashlib.sha256(token.encode()).hexdigest(),user_id,now+7*86400))
    session.clear()
    session.permanent=True
    session['auth_token']=token
    session['csrf']=secrets.token_urlsafe(32)


@auth.get('/me')
def me():
    token=csrf_token()
    configured=bool(current_app.config.get('NEXO_DATABASE_URL') or current_app.config.get('NEXO_AUTH_SQLITE'))
    return jsonify(user=current_user(), csrf=token, accounts_available=configured)


@auth.post('/register')
def register():
    data=request.get_json(silent=True)
    if not isinstance(data,dict):
        return jsonify(error='Completa el formulario de registro.'),400
    name=data.get('name','');username=data.get('username','');password=data.get('password','')
    if not all(isinstance(v,str) for v in [name,username,password]):
        return jsonify(error='Revisa los campos del registro.'),400
    name=' '.join(name.split());username=username.strip().lower()
    if not 2 <= len(name) <= 60 or any(ord(c)<32 for c in name):
        return jsonify(error='Tu nombre debe tener entre 2 y 60 caracteres.'),400
    if not re.fullmatch(r'[a-z0-9_]{3,32}',username):
        return jsonify(error='Usa de 3 a 32 letras sin tildes, números o guion bajo para tu usuario.'),400
    if not 10 <= len(password) <= 128:
        return jsonify(error='La contraseña debe tener entre 10 y 128 caracteres.'),400
    if not limit_attempts('register'):
        return jsonify(error='Hubo muchos registros desde esta conexión. Inténtalo en 15 minutos.'),429
    with database() as db:
        if db.execute('SELECT id FROM nexo_lab_users WHERE username=?',(username,)).fetchone():
            return jsonify(error='Ese nombre de usuario ya está en uso. Prueba otro.'),409
    user_id=str(uuid.uuid4())
    try:
        with database() as db:
            db.execute('INSERT INTO nexo_lab_users(id,username,display_name,password_hash,created_at) VALUES(?,?,?,?,?)',
                (user_id,username,name,generate_password_hash(password,method='scrypt'),int(time.time())))
    except Exception as exc:
        if isinstance(exc,sqlite3.IntegrityError) or getattr(exc,'sqlstate',None)=='23505':
            return jsonify(error='Ese nombre de usuario ya está en uso. Prueba otro.'),409
        raise DatabaseUnavailable() from exc
    establish_session(user_id)
    return jsonify(user={'id':user_id,'username':username,'name':name},csrf=csrf_token()),201


@auth.post('/login')
def login():
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or not isinstance(data.get('username'),str) or not isinstance(data.get('password'),str):
        return jsonify(error='Introduce tu usuario y contraseña.'),400
    username=data['username'].strip().lower();password=data['password']
    if len(username)>32 or len(password)>128:
        return jsonify(error='Usuario o contraseña incorrectos.'),401
    if not limit_attempts('login'):
        return jsonify(error='Demasiados intentos. Espera 15 minutos antes de volver a probar.'),429
    with database() as db:
        row=db.execute('SELECT * FROM nexo_lab_users WHERE username=?',(username,)).fetchone()
    # Hash de igual costo también para usuarios inexistentes.
    if not row:
        generate_password_hash(password,method='scrypt')
        return jsonify(error='Usuario o contraseña incorrectos.'),401
    if not check_password_hash(row['password_hash'],password):
        return jsonify(error='Usuario o contraseña incorrectos.'),401
    establish_session(row['id'])
    return jsonify(user=public_user(row),csrf=csrf_token())


@auth.post('/logout')
def logout():
    token=session.get('auth_token')
    if token:
        ensure_schema()
        with database() as db:
            db.execute('DELETE FROM nexo_lab_sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
    session.clear()
    return jsonify(user=None,csrf=csrf_token())
