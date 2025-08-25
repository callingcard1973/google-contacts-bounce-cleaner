# Google Contacts Bounce Cleaner

⚠️ **STATUS: DEVELOPMENT VERSION - NOT YET TESTED** ⚠️

A Python tool to automatically remove bounced/invalid email addresses from your Google Contacts using the Google People API with OAuth2 authentication.

## Features

- 🔍 **Safe scanning** - Find contacts with bounced emails
- 🛡️ **Dry-run mode** - Preview what will be deleted before taking action
- 📊 **Statistics** - Get insights about your contacts and bounces
- 📤 **Export capability** - Save list of contacts to be deleted
- 🔐 **Secure OAuth2** - Uses Google's official authentication
- ⚡ **Batch processing** - Efficient handling of large contact lists

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv google_contacts_venv
source google_contacts_venv/bin/activate

# Install required packages
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 2. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **People API**:
   - APIs & Services → Enable APIs
   - Search "People API" → Enable
4. Create OAuth 2.0 credentials:
   - APIs & Services → Credentials
   - CREATE CREDENTIALS → OAuth client ID
   - Application type: Desktop app
5. Download `credentials.json` to the script directory

### 3. Prepare Bounced Emails List

Create a file `bounced_emails.txt` with bounced emails (one per line):

```
invalid@example.com
bounced@domain.com
baduser@company.com
```

## Usage

### Check Statistics
```bash
./clean_bounced_contacts.py --stats
```

### Dry Run (Preview Only)
```bash
./clean_bounced_contacts.py --load-file bounced_emails.txt
```

### Export Contacts to Delete
```bash
./clean_bounced_contacts.py --load-file bounced_emails.txt --export
```

### Actually Delete Contacts
```bash
./clean_bounced_contacts.py --load-file bounced_emails.txt --no-dry-run
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--load-file` | File containing bounced emails (default: bounced_emails.txt) |
| `--no-dry-run` | Actually delete contacts (default is dry run) |
| `--export` | Export list of contacts to be deleted to JSON |
| `--stats` | Show statistics only |
| `--credentials` | Path to Google OAuth credentials file |
| `--token` | Path to token file for storing auth |

## Safety Features

- **Dry-run by default** - Never deletes without explicit confirmation
- **Detailed preview** - Shows exactly what will be deleted
- **Batch processing** - Handles large lists efficiently
- **Error handling** - Graceful handling of API errors
- **Authentication caching** - Saves auth token for future runs

## Output Example

```
🧹 Google Contacts Cleanup Tool
============================================================
✅ Successfully authenticated with Google

📄 Loading bounced emails from bounced_emails.txt...
Loaded 15 emails from file

🔍 Searching contacts for 15 bounced emails...
  Processed 1000 contacts so far...
  Processed 2000 contacts so far...

✅ Scanned 2847 total contacts
📊 Found 12 contacts with bounced emails

🔍 DRY RUN - Would delete 12 contacts:
  1. John Doe (john.doe@invalid.com)
  2. Jane Smith (jane@bounced.org)
  ...

💡 To actually delete these contacts, run with --no-dry-run
⚠️  WARNING: This action cannot be undone!
```

## Requirements

- Python 3.7+
- Google account with contacts
- Google Cloud project with People API enabled
- OAuth2 credentials

## Security Notes

- `credentials.json` and `token.pickle` contain sensitive data - keep secure
- The tool only requests permissions for contacts (no email access)
- Authentication tokens are stored locally for convenience
- Always backup your contacts before running deletions

## License

MIT License - See LICENSE file for details

## Contributing

Pull requests welcome! Please ensure:
- Code follows existing style
- Add tests for new features
- Update documentation as needed

## Troubleshooting

### "credentials.json not found"
Download OAuth2 credentials from Google Cloud Console

### "Permission denied" errors
Ensure the People API is enabled in your Google Cloud project

### "Authentication failed"
Delete `token.pickle` and re-authenticate

### Rate limiting
The script includes built-in rate limiting and retry logic