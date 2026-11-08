from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app import app


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.path=str(Path(self.directory.name)/'accounts.sqlite3')
        self.previous={k:app.config.get(k) for k in ['TESTING','SECRET_KEY','NEXO_DATABASE_URL','NEXO_AUTH_SQLITE','_NEXO_SCHEMA_READY','SESSION_COOKIE_SECURE']}
        app.config.update(TESTING=True,SECRET_KEY='test-only-secret',NEXO_DATABASE_URL='',NEXO_AUTH_SQLITE=self.path,_NEXO_SCHEMA_READY=None,SESSION_COOKIE_SECURE=False)
        self.client=app.test_client()

    def tearDown(self):
        app.config.update(self.previous)
        self.directory.cleanup()

    def csrf(self,client=None):
        return (client or self.client).get('/api/auth/me').json['csrf']

    def post(self,path,data=None,client=None):
        c=client or self.client
        return c.post('/api/auth/'+path,json=data or {},headers={'X-CSRF-Token':self.csrf(c)})

    def register(self,name='Ana María',username='ana_test',client=None):
        return self.post('register',{'name':name,'username':username,'password':'Correcta_12345'},client)

    def test_registration_and_personalized_name(self):
        initial=self.client.get('/api/auth/me')
        self.assertIsNone(initial.json['user'])
        self.assertIn('HttpOnly',initial.headers['Set-Cookie'])
        self.assertIn('SameSite=Lax',initial.headers['Set-Cookie'])
        r=self.register();self.assertEqual(r.status_code,201)
        self.assertEqual(r.json['user']['name'],'Ana María')
        self.assertNotIn('password',r.text)
        self.assertEqual(self.client.get('/api/auth/me').json['user']['username'],'ana_test')
        with closing(sqlite3.connect(self.path)) as db, db:
            stored=db.execute('SELECT password_hash FROM nexo_lab_users').fetchone()[0]
        self.assertTrue(stored.startswith('scrypt:'))
        self.assertNotIn('Correcta_12345',stored)

    def test_csrf_is_required_and_rotates(self):
        old=self.csrf()
        bad=self.client.post('/api/auth/register',json={'name':'Ana','username':'ana','password':'Correcta_12345'})
        self.assertEqual(bad.status_code,403)
        r=self.register();self.assertEqual(r.status_code,201);self.assertNotEqual(old,r.json['csrf'])
        self.assertEqual(self.client.post('/api/auth/logout',json={},headers={'X-CSRF-Token':old}).status_code,403)

    def test_login_logout_and_separate_accounts(self):
        self.register()
        bob=app.test_client();r=self.register('Bruno','bruno_test',bob)
        self.assertEqual(r.status_code,201)
        self.assertEqual(self.client.get('/api/auth/me').json['user']['name'],'Ana María')
        self.assertEqual(bob.get('/api/auth/me').json['user']['name'],'Bruno')
        with self.client.session_transaction() as s: old_token=s['auth_token']
        self.assertEqual(self.post('logout').status_code,200)
        self.assertIsNone(self.client.get('/api/auth/me').json['user'])
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertIsNone(db.execute('SELECT user_id FROM nexo_lab_sessions WHERE token_hash=?',(hashlib.sha256(old_token.encode()).hexdigest(),)).fetchone())
        self.assertEqual(self.post('login',{'username':'ana_test','password':'wrong'}).status_code,401)
        self.assertEqual(self.post('login',{'username':'ANA_TEST','password':'Correcta_12345'}).status_code,200)

    def test_duplicate_and_invalid_input(self):
        self.register()
        self.assertEqual(self.register(username='ANA_TEST').status_code,409)
        for values in [{'name':'A','username':'short','password':'Correcta_12345'},
                       {'name':'Ana','username':"a' OR 1=1--",'password':'Correcta_12345'},
                       {'name':'Ana','username':'new_user','password':'short'},
                       {'name':[],'username':'new_user','password':'Correcta_12345'}]:
            self.assertEqual(self.post('register',values).status_code,400)
        self.assertEqual(self.post('login',{'username':"' OR 1=1--",'password':'x'}).status_code,401)

    def test_expiry_and_session_persistence(self):
        self.register()
        # Reinicializar el esquema no borra cuentas ni sesiones existentes.
        app.config['_NEXO_SCHEMA_READY']=None
        self.assertEqual(self.client.get('/api/auth/me').json['user']['username'],'ana_test')
        with closing(sqlite3.connect(self.path)) as db, db:db.execute('UPDATE nexo_lab_sessions SET expires_at=0')
        self.assertIsNone(self.client.get('/api/auth/me').json['user'])

    def test_rate_limit_and_other_tables_untouched(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE existing_project_notes (note TEXT)')
            db.execute("INSERT INTO existing_project_notes VALUES ('keep me')")
        for i in range(25):
            self.assertEqual(self.post('login',{'username':'missing','password':'x'}).status_code,401)
        self.assertEqual(self.post('login',{'username':'missing','password':'x'}).status_code,429)
        with closing(sqlite3.connect(self.path)) as db, db:self.assertEqual(db.execute('SELECT note FROM existing_project_notes').fetchone()[0],'keep me')

    def test_unconfigured_production_fails_without_ephemeral_accounts(self):
        app.config.update(NEXO_AUTH_SQLITE=None,NEXO_DATABASE_URL='',_NEXO_SCHEMA_READY=None)
        self.assertFalse(self.client.get('/api/auth/me').json['accounts_available'])
        self.assertEqual(self.register().status_code,503)


if __name__=='__main__':unittest.main()
