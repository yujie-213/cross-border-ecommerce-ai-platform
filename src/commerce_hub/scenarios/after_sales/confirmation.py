"""Durable human confirmation; ERP IO is outside aggregate transactions."""
from copy import deepcopy
from sqlalchemy import update

from commerce_hub.adapters.erp import ERPError
from commerce_hub.orchestration.service import TaskError
from .common import digest, now, require
from .tables import commands

ACTIVE = {'PREPARED', 'SENDING', 'PENDING'}


class Confirmation:
    def __init__(self, domain):
        self.domain, self.store = domain, domain.store

    def confirm(self, actor, rid, key, revision, data):
        d, s = self.domain, self.store
        require(getattr(d.source_reader, 'voice_client_factory', None) is not None, 'ERP_HANDLING_NOT_CONFIGURED', 503)
        def prepare(conn):
            row = s.get(conn, actor, 'CASE', rid, 'b:case:review', lock=True)
            require(row['revision'] == revision, 'REVISION_CONFLICT', 409)
            b = row['body']
            require(b.get('erpVoiceId') and b.get('erpVoiceKind') in {'reviews', 'feedback'}, 'SOURCE_KIND_INVALID')
            require((b.get('confirmation') or {}).get('status') not in ACTIVE, 'CONFIRMATION_PENDING', 409)
            require(row['state'] != 'HANDLED', 'ALREADY_HANDLED', 409)
            require(isinstance(data.get('text'), str) and 0 < len(data['text'].strip()) <= 1900, 'REPLY_LENGTH_INVALID')
            final, state = d._case_command(conn, actor, row, 'reviews', data)
            require(state == 'HANDLED', 'REVIEW_INVALID')
            request_key = 'b-voice-' + digest([actor.tenant_id, actor.principal_id, key])[:48]
            intent = dict(status='PREPARED', key=key, actor=actor.principal_id, confirmedAt=now(),
                requestKey=request_key, note=data['text']+'\n\n处理编号：'+request_key,
                review=final['reviews'][-1], originalMessages=deepcopy(b['messages']),
                aiOriginal=deepcopy(b['advice'][-1]) if b['advice'] else None)
            body = deepcopy(b); body['confirmation'] = intent
            return dict(kind='CASE', **s.save(conn, actor, row, body), handlingStatus='PENDING')
        result = s.command(actor, key, 'confirm-'+rid, dict(expectedRevision=revision, data=data), prepare)
        if result.get('handlingStatus') in {'CONFIRMED', 'REJECTED'}: return result
        return self.recover(actor, key, rid)

    def recover(self, actor, key, rid):
        s, d = self.store, self.domain
        with s.engine.begin() as conn:
            row = s.get(conn, actor, 'CASE', rid, 'b:case:review', lock=True)
            b = row['body']; intent = b.get('confirmation') or {}
            require(intent.get('key') == key and intent.get('actor') == actor.principal_id, 'COMMAND_CONFLICT', 409)
            if intent['status'] in {'CONFIRMED', 'REJECTED'}:
                return dict(kind='CASE', id=rid, revision=row['revision'], state=row['state'], handlingStatus=intent['status'])
            # Claim once. Even a crash before POST becomes read-only recovery.
            send = intent['status'] == 'PREPARED'
            if send:
                body = deepcopy(b); body['confirmation']['status'] = 'SENDING'
                s.save(conn, actor, row, body)
        def check():
            with s.engine.begin() as conn: s.get(conn, actor, 'CASE', rid, 'b:case:review')
        client = d.source_reader.voice_client_factory()
        store_id = d.source_reader._store(b['erpStoreName'])['storeId']
        kind, voice_id = b['erpVoiceKind'], b['erpVoiceId']
        receipt = None; status = 'PENDING'; error = None; posting = False
        try:
            d.source_reader.voice_evidence(voice_id, kind, b['erpStoreName'], check, 'confirm-'+intent['requestKey'])
            if send:
                history = client.history(kind, voice_id, store_id)
                version = max((int(r['version']) for r in history), default=0)
                check()
                posting = True
                client.append(kind, voice_id, version, intent['note'], intent['requestKey'])
            check()
            history = client.history(kind, voice_id, store_id)
            matches = [r for r in history if r.get('note') == intent['note'] and r.get('handling_status') == 'resolved'
                and r.get('kind') == kind and str(r.get('record_id')) == voice_id and type(r.get('version')) is int and r['version'] > 0]
            if len(matches) == 1: receipt = matches[0]; status = 'CONFIRMED'
        except ERPError as exc:
            error = exc.code
            if exc.code == 'ERP_WRITE_REJECTED' or send and not posting: status = 'REJECTED'
        except TaskError as exc:
            error = exc.code
            if send and not posting: status = 'REJECTED'
        with s.engine.begin() as conn:
            row = s.get(conn, actor, 'CASE', rid, 'b:case:review', lock=True)
            body = deepcopy(row['body']); current = body['confirmation']
            require(current['key'] == key, 'COMMAND_CONFLICT', 409)
            if current['status'] == 'CONFIRMED': status = 'CONFIRMED'
            else:
                current.update(status=status, checkedAt=now(), error=error)
                if receipt:
                    current['erpRecord'] = receipt
                    review = deepcopy(current['review']); review.update(externalAction='ERP_INTERNAL_HANDLING', erpRecord=receipt)
                    body['reviews'].append(review)
                result = s.save(conn, actor, row, body, 'HANDLED' if status == 'CONFIRMED' else row['state'])
                row = dict(row, **result)
            result = dict(kind='CASE', id=rid, revision=row['revision'], state=row['state'], handlingStatus=status)
            conn.execute(update(commands).filter_by(tenant_id=actor.tenant_id, actor=actor.principal_id, command_key=key).values(result=result))
            return result
