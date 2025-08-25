# Google Contacts Cleanup Setup Guide

## Your OAuth Client ID
```
976881542294-rirnjufeg6khcq9k4rqbhpnqlbdvhdgr.apps.googleusercontent.com
```

## Setup Steps

### 1. Download OAuth Credentials
1. Go to https://console.cloud.google.com/
2. Select your project (or create new one)
3. Go to **APIs & Services** → **Credentials**
4. Find your OAuth 2.0 Client ID (the one ending with the ID above)
5. Click the download button (⬇) to download `credentials.json`
6. Save it to `/home/tudor/credentials.json`

### 2. Enable Required API
1. Go to **APIs & Services** → **Enable APIs**
2. Search for "**People API**"
3. Click on it and press **Enable**

### 3. Run the Script

First test run (dry run - won't delete anything):
```bash
cd /home/tudor
./clean_bounced_contacts.py --load-file bounced_emails.txt
```

When first run, it will:
1. Open a browser for authentication
2. Ask you to login to your Google account
3. Grant permissions to manage contacts
4. Save authentication token locally

### 4. Add Bounced Emails
Edit `/home/tudor/bounced_emails.txt` and add the emails that bounced, one per line:
```
baduser@example.com
invalid@domain.com
bounced@email.com
```

### 5. Run Operations

**Check statistics:**
```bash
./clean_bounced_contacts.py --stats
```

**Dry run (see what would be deleted):**
```bash
./clean_bounced_contacts.py --load-file bounced_emails.txt
```

**Export list of contacts to be deleted:**
```bash
./clean_bounced_contacts.py --load-file bounced_emails.txt --export
```

**Actually delete the contacts:**
```bash
./clean_bounced_contacts.py --load-file bounced_emails.txt --no-dry-run
```

## Important Notes
- Always do a dry run first to see what will be deleted
- The deletion cannot be undone
- Keep backups of your contacts (Google Contacts → Export)
- The script uses batch processing for efficiency
- Authentication token is saved locally for future runs