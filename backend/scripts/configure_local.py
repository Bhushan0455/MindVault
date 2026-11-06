"""Create isolated local demo settings without installing a system database."""
from pathlib import Path
import secrets

if __name__ == '__main__':
    root=Path(__file__).resolve().parents[1]
    target=root/'.env'
    if target.exists():
        raise SystemExit('An .env file already exists; it was left unchanged.')
    target.write_text('DATABASE_URL=sqlite:///./mindvault_local.sqlite\n'
        +f'JWT_SECRET={secrets.token_urlsafe(48)}\n'
        +'DEMO_MODE=true\nENABLE_SEMANTIC=false\nGEMINI_MODEL=\nGEMINI_API_KEY=\n'
        +'ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000\nMAX_UPLOAD_MB=5\n',encoding='utf-8')
    print('Local demo configured. Start with: python -m uvicorn app.main:app --port 8000')
