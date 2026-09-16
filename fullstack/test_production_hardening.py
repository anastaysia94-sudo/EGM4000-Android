#!/usr/bin/env python3
import os
from production_readiness import evaluate,require_production_ready,session_token_hash


def main():
    base={
      'EGM_ENV':'production','EGM_SECURE_COOKIES':'1','EGM_PUBLIC_BASE_URL':'https://egm.example.test',
      'EGM_OWNER_PASSWORD':'O'*24,'EGM_VISITOR_SECRET':'V'*40,'EGM_OWNER_RECOVERY_TOKEN':'R'*40,
      'EGM_OWNER_TOTP_SECRET':'JBSWY3DPEHPK3PXP','DATABASE_URL':'postgresql://user:pass@db.example.test:5432/egm?sslmode=require',
      'EGM_TRUST_PROXY':'1','EGM_MANAGED_DATABASE_BACKUPS':'1'
    }
    ready=evaluate(base);assert ready['ready'] and not ready['missing']
    assert session_token_hash('abc')!='abc' and len(session_token_hash('abc'))==64
    bad=dict(base);bad['EGM_SECURE_COOKIES']='0';bad['EGM_VISITOR_SECRET']=bad['EGM_OWNER_PASSWORD'];bad.pop('EGM_OWNER_TOTP_SECRET')
    result=evaluate(bad);assert not result['ready'];assert {'secure_cookies','visitor_secret_separate','owner_totp'}<=set(result['missing'])
    try:require_production_ready(bad);raise AssertionError('production gate did not fail')
    except RuntimeError as exc:assert 'production_readiness_failed' in str(exc)
    dev=evaluate({'EGM_ENV':'development'});assert dev['ready'] and not dev['production']
    billing=dict(base);billing['EGM_BILLING_WEBHOOK_SECRET']='short';assert 'billing_signing_secret' in evaluate(billing)['missing']
    print('C003 production hardening verified')

if __name__=='__main__':main()
