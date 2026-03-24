# Cloudflare R2 Setup Guide

## 1. Get Cloudflare R2 Credentials

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Navigate to **R2 Object Storage**
3. Create a new bucket (e.g., "meditations")
4. Go to **Manage R2 API Tokens**
5. Create an API token with:
   - Permissions: Object Read & Write
   - Bucket permissions: Select your bucket

## 2. Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```env
   R2_ACCOUNT_ID=your-actual-account-id
   R2_ACCESS_KEY_ID=your-actual-access-key-id
   R2_SECRET_ACCESS_KEY=your-actual-secret-access-key
   R2_BUCKET_NAME=meditations
   R2_BUCKET_URL=https://your-account.r2.cloudflarestorage.com/meditations
   ```

## 3. Install Dependencies

```bash
pip install --break-system-packages python-dotenv boto3
```

## 4. Upload Files to R2

```bash
python3 upload_to_r2.py
```

## 5. Update JSON with R2 URLs

```bash
python3 update_meditations.py
```

## 6. Build and Deploy

```bash
npm run build
```

## Security Notes

- ✅ `.env` is ignored by Git
- ✅ `.env.example` shows the structure
- ✅ Never commit actual credentials
- ✅ Use different tokens for dev/prod

## File Structure After Setup

```
web-ui/
├── .env                  # Your secret credentials (ignored)
├── .env.example          # Template for others
├── public/data/
│   ├── meditations.json   # Generated with R2 URLs
│   └── *.wav           # Local backup
├── upload_to_r2.py       # Upload script
└── update_meditations.py  # JSON generator
```
