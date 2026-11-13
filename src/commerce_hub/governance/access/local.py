"""Single local administrator, backed by G01 sessions and current grants."""
from datetime import datetime,timedelta,timezone
import hashlib,hmac,secrets
from threading import BoundedSemaphore
from uuid import uuid4
import jwt
from sqlalchemy import Table,Column,String,Integer,MetaData,select,insert,update,func
from sqlalchemy.dialects.mysql import DATETIME
from .tables import principals,grants,sessions
from .service import AccessDenied,ALLOWED_ACTIONS

metadata=MetaData()
admins=Table('g01_local_admin',metadata,
    Column('tenant_id',String(64),primary_key=True),Column('principal_id',String(64),nullable=False),
    Column('password_hash',String(256),nullable=False),Column('failures',Integer,nullable=False),
    Column('locked_until',DATETIME(fsp=6)),
    mysql_engine='InnoDB',mysql_charset='utf8mb4',mysql_collate='utf8mb4_bin')


_hash_slots=BoundedSemaphore(2)


def derive(password,salt):
    with _hash_slots:return hashlib.scrypt(password.encode(),salt=salt,n=2**17,r=8,p=1,maxmem=256*1024*1024,dklen=64)


def password_hash(password):
    if not isinstance(password,str) or not 6<=len(password)<=256:raise ValueError('PASSWORD_LENGTH_INVALID')
    salt=secrets.token_bytes(32)
    digest=derive(password,salt)
    return 'scrypt-v1$'+salt.hex()+'$'+digest.hex()


def verify_password(password,encoded):
    try:
        version,salt,expected=encoded.split('$')
        if version!='scrypt-v1' or len(salt)!=64 or len(expected)!=128 or not 1<=len(password)<=256:return False
        actual=derive(password,bytes.fromhex(salt))
        return hmac.compare_digest(actual.hex(),expected)
    except (ValueError,TypeError):return False


class LocalAdmin:
    def __init__(self,access,tenant,scope,seconds=28800):
        self.access,self.engine,self.tenant,self.scope,self.seconds=access,access.engine,tenant,scope,seconds

    def initialized(self):
        with self.engine.connect() as c:return c.execute(select(admins.c.tenant_id).filter_by(tenant_id=self.tenant)).first() is not None

    def initialize(self,password,*,reset=False):
        encoded=password_hash(password) # CPU work outside the short SQL transaction.
        with self.engine.connect() as c:
            # Serialize init/reset with login and session mutations using principal-first lock order.
            lock='g01local:'+hashlib.sha256(self.tenant.encode()).hexdigest()[:48]
            if c.scalar(select(func.get_lock(lock,5)))!=1:raise ValueError('ADMIN_INITIALIZATION_BUSY')
            c.commit()
            try:
                current=c.execute(select(admins).filter_by(tenant_id=self.tenant)).mappings().first()
                if current and not reset:raise ValueError('ADMIN_ALREADY_INITIALIZED')
                if not current:
                    pid='local-admin'
                    if c.execute(select(principals).filter_by(tenant_id=self.tenant,principal_id=pid)).first():raise ValueError('ADMIN_PRINCIPAL_CONFLICT')
                    c.execute(insert(principals).values(tenant_id=self.tenant,principal_id=pid,active=True,revision=1))
                    for action in ALLOWED_ACTIONS:c.execute(insert(grants).values(tenant_id=self.tenant,principal_id=pid,action=action,scope=self.scope))
                    c.execute(insert(admins).values(tenant_id=self.tenant,principal_id=pid,password_hash=encoded,failures=0))
                else:
                    pid=current['principal_id']
                    c.execute(select(principals).filter_by(tenant_id=self.tenant,principal_id=pid).with_for_update()).one()
                    c.execute(update(principals).filter_by(tenant_id=self.tenant,principal_id=pid).values(active=True,revision=principals.c.revision+1))
                    c.execute(update(sessions).filter_by(tenant_id=self.tenant,principal_id=pid).values(active=False))
                    c.execute(update(admins).filter_by(tenant_id=self.tenant).values(password_hash=encoded,failures=0,locked_until=None))
                c.commit()
            finally:
                if c.in_transaction():c.rollback()
                c.scalar(select(func.release_lock(lock)));c.commit()

    def login(self,username,password):
        with self.engine.connect() as c:
            stored=c.execute(select(admins).filter_by(tenant_id=self.tenant)).mappings().first()
        if not stored:raise AccessDenied('LOGIN_REJECTED')
        valid=verify_password(password,stored['password_hash']) and username=='admin'
        rejected=False;result=None
        with self.engine.begin() as c:
            principal=c.execute(select(principals).filter_by(tenant_id=self.tenant,principal_id=stored['principal_id']).with_for_update()).mappings().one()
            row=c.execute(select(admins).filter_by(tenant_id=self.tenant).with_for_update()).mappings().one()
            now=c.scalar(select(func.utc_timestamp(6)))
            if row['password_hash']!=stored['password_hash'] or not principal['active'] or row['locked_until'] and row['locked_until']>now:
                rejected=True
            elif not valid:
                failures=row['failures']+1
                c.execute(update(admins).filter_by(tenant_id=self.tenant).values(failures=failures if failures<5 else 0,locked_until=now+timedelta(seconds=30) if failures>=5 else None))
                rejected=True
            else:
                stamp=int(now.replace(tzinfo=timezone.utc).timestamp());expires=stamp+self.seconds;jti=uuid4().hex
                c.execute(update(admins).filter_by(tenant_id=self.tenant).values(failures=0,locked_until=None))
                c.execute(insert(sessions).values(tenant_id=self.tenant,principal_id=principal['principal_id'],token_id=jti,active=True,expires_at=datetime.fromtimestamp(expires,timezone.utc).replace(tzinfo=None)))
                claims=dict(iss=self.access.issuer,aud=self.access.audience,sub=principal['principal_id'],tid=self.tenant,jti=jti,rev=principal['revision'],iat=stamp,nbf=stamp,exp=expires)
                result=(jwt.encode(claims,self.access._key,algorithm='HS256'),datetime.fromtimestamp(expires,timezone.utc).isoformat())
        if rejected:raise AccessDenied('LOGIN_REJECTED')
        return result
