#!/usr/bin/env python
"""
C01_download_source_data_template.py

Module C: Published raw-data extraction module.
Purpose:
- Template downloader for paper source datasets.

Important:
- Many paper datasets require manual download, agreement pages, or different formats.
- This script records the manifest and downloads direct URLs only when possible.
"""
from pathlib import Path
import argparse
import pandas as pd
import urllib.request


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest_csv', required=True)
    p.add_argument('--download_dir', required=True)
    args=p.parse_args()
    out=Path(args.download_dir); out.mkdir(parents=True, exist_ok=True)
    manifest=pd.read_csv(args.manifest_csv)
    statuses=[]
    for _, r in manifest.iterrows():
        url=str(r.get('data_url',''))
        paper_id=str(r.get('paper_id','paper'))
        status='not_attempted'
        local_path=''
        if url.startswith('http') and not url.endswith('.html'):
            fname=url.split('/')[-1] or f'{paper_id}_downloaded_file'
            dest=out/fname
            try:
                urllib.request.urlretrieve(url, dest)
                status='downloaded'
                local_path=str(dest)
            except Exception as e:
                status=f'failed_direct_download: {e}'
        else:
            status='manual_download_required_or_landing_page'
        statuses.append({**r.to_dict(), 'download_status':status, 'local_path':local_path})
    pd.DataFrame(statuses).to_csv(out/'Paper_Dataset_Manifest_Checked.csv', index=False)
    print('[DONE] Paper_Dataset_Manifest_Checked.csv')

if __name__ == '__main__':
    main()
