"""Explicit standalone per-user installer/uninstaller; never invoked by a build."""
import argparse
import json
from setup_core import register_host, unregister, import_legacy

def main():
    p=argparse.ArgumentParser(description='NoYouPub Core setup')
    p.add_argument('action',choices=('install','uninstall','import-legacy'))
    p.add_argument('--payload');p.add_argument('--home');p.add_argument('--data-root')
    p.add_argument('--confirm',action='store_true');p.add_argument('--remove-data',action='store_true')
    a=p.parse_args()
    if not a.confirm:p.error('No changes made. Run with --confirm after reviewing the installation guide.')
    if a.action=='install':r=register_host(a.home,a.payload,a.data_root)
    elif a.action=='uninstall':r=unregister(a.home,a.data_root,a.remove_data)
    else:r=import_legacy(a.home,a.data_root)
    print(json.dumps(r,ensure_ascii=False))
if __name__=='__main__':main()
