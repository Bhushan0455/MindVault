"""Create local configuration without including credentials in shared files."""
import argparse
import getpass
import secrets
from pathlib import Path
from dotenv import dotenv_values, set_key

parser=argparse.ArgumentParser()
parser.add_argument('--ai',action='store_true')
args=parser.parse_args()
path=Path(__file__).resolve().parents[1]/'.env'
if not path.exists():
    values={'DATABASE_URL':'sqlite:///./mindvault.sqlite','JWT_SECRET':secrets.token_urlsafe(48),
            'DEMO_MODE':'true','ENABLE_SEMANTIC':'false','GEMINI_API_KEY':'','GEMINI_MODEL':'',
            'ALLOWED_ORIGINS':'http://127.0.0.1:5174,http://localhost:5174','MAX_UPLOAD_MB':'5'}
    path.touch()
    for name,value in values.items(): set_key(str(path),name,value)
    print('Created private local settings. Fictional demo data is enabled.')
else: print('Keeping existing private local settings.')
if args.ai:
    key=getpass.getpass('Gemini API key (hidden): ').strip()
    model=input('Exact model ID already verified for your account: ').strip()
    if not key or not model: raise SystemExit('Key and model are required. Existing AI settings were preserved.')
    for name,value in {'GEMINI_API_KEY':key,'GEMINI_MODEL':model,'ENABLE_SEMANTIC':'true'}.items():set_key(str(path),name,value)
    print('AI settings saved privately. Restart the website to use them; results show actual AI/fallback status.')
