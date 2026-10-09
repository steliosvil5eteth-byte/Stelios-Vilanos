#!/usr/bin/env python3
"""Read back explicitly staged public assets and verify the sealed byte hashes."""
import argparse, hashlib, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--spec',required=True)
    p.add_argument('--receipts',required=True)
    a=p.parse_args()
    spec=json.loads(Path(a.spec).read_text())
    out=Path(a.receipts)
    receipts=json.loads(out.read_text()) if out.exists() else []
    for item in spec['items']:
        expected=item.get('checksum_sha256',item.get('sha256'))
        size=item.get('size_bytes',item.get('bytes'))
        existing=next((x for x in receipts if x['asset_id']==item['asset_id'] and x.get('matches') and x['sha256']==expected and x['bytes']==size),None)
        if existing:
            print(json.dumps({'asset_id':item['asset_id'],'already_verified':True}),flush=True)
            continue
        digest=hashlib.sha256(); count=0
        with urllib.request.urlopen(item['url'],timeout=180) as response:
            status=response.status
            while True:
                chunk=response.read(1024*1024)
                if not chunk: break
                count+=len(chunk); digest.update(chunk)
        got=digest.hexdigest()
        if status!=200 or count!=size or got!=expected:
            raise RuntimeError('Staged byte verification mismatch for '+item['asset_id'])
        receipt={'asset_id':item['asset_id'],'job_id':item['job_id'],'url':item['url'],'http_status':status,'bytes':count,'sha256':got,'matches':True,'verified_at_utc':datetime.now(timezone.utc).isoformat()}
        receipts.append(receipt)
        out.write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in receipt.items() if k!='url'}),flush=True)

if __name__=='__main__': main()
