#!/usr/bin/env python3
"""Deployment-side A084 API client administration.

This CLI intentionally keeps API-key creation/rotation out of the browser UI.
Run it only in an authorized deployment shell. Newly created or rotated keys are
printed once; the database stores only the SHA-256 hash and a non-secret prefix.
"""
from __future__ import annotations
import argparse
import json
from storage import connect
from commercial_access import admin_api_clients,archive_api_client,migrate_commercial_access,rotate_api_client_key,save_api_client


def main():
    parser=argparse.ArgumentParser(description='EGM4000 A084 API access administration')
    sub=parser.add_subparsers(dest='command',required=True)
    create=sub.add_parser('create');create.add_argument('--name',required=True);create.add_argument('--plan',choices=['developer','pro','enterprise'],default='developer');create.add_argument('--scopes',default='summary');create.add_argument('--daily-quota',type=int)
    rotate=sub.add_parser('rotate');rotate.add_argument('client_id')
    archive=sub.add_parser('archive');archive.add_argument('client_id')
    sub.add_parser('list')
    args=parser.parse_args();con=connect()
    try:
        migrate_commercial_access(con)
        if args.command=='create':
            payload={'name':args.name,'plan':args.plan,'scopes':[x.strip() for x in args.scopes.split(',') if x.strip()]}
            if args.daily_quota is not None:payload['daily_quota']=args.daily_quota
            result=save_api_client(con,payload)
        elif args.command=='rotate':result=rotate_api_client_key(con,args.client_id)
        elif args.command=='archive':result=archive_api_client(con,args.client_id)
        else:result=admin_api_clients(con)
        print(json.dumps(result,indent=2))
    finally:con.close()

if __name__=='__main__':main()
