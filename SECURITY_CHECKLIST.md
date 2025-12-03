# Security Checklist Before Deployment

## Before Pushing to GitHub

Check for exposed secrets:

```bash
# Search for MongoDB connection strings
grep -r "mongodb+srv://" . --exclude-dir=.git --exclude-dir=__pycache__

# Search for passwords
grep -r "n1a32gnRzcEvhnbZ" . --exclude-dir=.git --exclude-dir=__pycache__

# Check what will be committed
git status
```

## Files That Should NOT Be Committed

- [ ] `.env` files
- [ ] `test_api_mongodb.py` (if it has hardcoded credentials)
- [ ] `TEST_RESULTS.md` (if it has connection strings)
- [ ] Any files with actual passwords

## Verify .gitignore

Make sure `.gitignore` includes:
- `.env*`
- `*.log`
- `test_api_mongodb.py`
- Files with secrets

## Environment Variables (Render Only)

Store these in Render's environment variables:
- ✅ `MONGODB_URL` - Store in Render, not in code
- ✅ `MONGODB_DATABASE` - Optional, can be in code
- ✅ `CORS_ORIGINS` - Can be in code or env var

## Quick Security Test

Before pushing to GitHub:
```bash
# This should NOT show any actual connection strings
grep -r "mongodb+srv://" .git --exclude-dir=.git
```

If it shows anything, remove those files before committing!
