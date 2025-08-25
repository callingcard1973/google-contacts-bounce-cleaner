#!/home/tudor/google_contacts_venv/bin/python3
"""
Google Contacts Cleanup Script
Removes bounced email addresses from Google Contacts
Uses OAuth2 for authentication with Google People API
"""

import os
import pickle
import base64
import re
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# OAuth scopes needed - Only People API for contacts
SCOPES = [
    'https://www.googleapis.com/auth/contacts'
]

class BounceContactCleaner:
    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.people_service = None
        self.bounced_emails = set()
        
    def authenticate(self):
        """Authenticate using OAuth2"""
        creds = None
        
        # Token file stores the user's access and refresh tokens
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"\n❌ ERROR: {self.credentials_file} not found!")
                    print("\n📋 To set up Google Cloud credentials:")
                    print("1. Go to https://console.cloud.google.com/")
                    print("2. Create a new project or select existing")
                    print("3. Enable the People API:")
                    print("   - Go to APIs & Services → Enable APIs")
                    print("   - Search for 'People API'")
                    print("   - Click Enable")
                    print("4. Create OAuth 2.0 credentials:")
                    print("   - Go to APIs & Services → Credentials")
                    print("   - Click '+ CREATE CREDENTIALS' → OAuth client ID")
                    print("   - Application type: Desktop app")
                    print("   - Name it (e.g., 'Contact Cleaner')")
                    print("5. Download the credentials.json file")
                    print("6. Place it in the same directory as this script")
                    return False
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build People API service
        self.people_service = build('people', 'v1', credentials=creds)
        print("✅ Successfully authenticated with Google")
        return True
    
    def load_bounced_from_file(self, filename='bounced_emails.txt'):
        """Load bounced emails from a file (one per line)"""
        if os.path.exists(filename):
            print(f"\n📄 Loading bounced emails from {filename}...")
            with open(filename, 'r') as f:
                for line in f:
                    email = line.strip().lower()
                    if email and '@' in email:
                        self.bounced_emails.add(email)
            print(f"Loaded {len(self.bounced_emails)} emails from file")
        else:
            print(f"\n⚠️  File {filename} not found")
            return False
        return True
    
    def save_bounced_to_file(self, filename='bounced_emails.txt'):
        """Save bounced emails to a file"""
        with open(filename, 'w') as f:
            for email in sorted(self.bounced_emails):
                f.write(f"{email}\n")
        print(f"\n💾 Saved {len(self.bounced_emails)} bounced emails to {filename}")
    
    def search_contacts(self):
        """Search all contacts and find those with bounced emails"""
        if not self.bounced_emails:
            print("\n⚠️  No bounced emails loaded. Please load from file first.")
            return []
        
        print(f"\n🔍 Searching contacts for {len(self.bounced_emails)} bounced emails...")
        
        contacts_to_process = []
        page_token = None
        total_contacts = 0
        
        try:
            while True:
                # Get batch of contacts
                results = self.people_service.people().connections().list(
                    resourceName='people/me',
                    pageSize=1000,  # Max allowed
                    pageToken=page_token,
                    personFields='names,emailAddresses,metadata'
                ).execute()
                
                connections = results.get('connections', [])
                total_contacts += len(connections)
                
                # Check each contact
                for person in connections:
                    emails = person.get('emailAddresses', [])
                    for email_obj in emails:
                        email = email_obj.get('value', '').lower()
                        if email in self.bounced_emails:
                            contact_name = 'Unknown'
                            names = person.get('names', [])
                            if names:
                                contact_name = names[0].get('displayName', 'Unknown')
                            
                            contacts_to_process.append({
                                'resourceName': person['resourceName'],
                                'name': contact_name,
                                'email': email,
                                'etag': person.get('etag', '')
                            })
                            break
                
                # Check for more pages
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
                print(f"  Processed {total_contacts} contacts so far...")
            
            print(f"\n✅ Scanned {total_contacts} total contacts")
            print(f"📊 Found {len(contacts_to_process)} contacts with bounced emails")
            
        except HttpError as error:
            print(f'❌ An error occurred: {error}')
            
        return contacts_to_process
    
    def remove_from_contacts(self, dry_run=True, batch_size=50):
        """Remove bounced emails from Google Contacts"""
        contacts_to_delete = self.search_contacts()
        
        if not contacts_to_delete:
            print("\n✅ No matching contacts found to delete")
            return
        
        print(f"\n{'🔍 DRY RUN - Would delete' if dry_run else '🗑️  Deleting'} {len(contacts_to_delete)} contacts:")
        
        # Show list of contacts to be deleted
        for i, contact in enumerate(contacts_to_delete[:20], 1):  # Show first 20
            print(f"  {i}. {contact['name']} ({contact['email']})")
        
        if len(contacts_to_delete) > 20:
            print(f"  ... and {len(contacts_to_delete) - 20} more")
        
        if not dry_run:
            print("\n⏳ Starting deletion process...")
            
            deleted_count = 0
            failed_count = 0
            
            # Delete in batches
            for i in range(0, len(contacts_to_delete), batch_size):
                batch = contacts_to_delete[i:i+batch_size]
                print(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} contacts)...")
                
                for contact in batch:
                    try:
                        self.people_service.people().deleteContact(
                            resourceName=contact['resourceName']
                        ).execute()
                        deleted_count += 1
                        print(f"  ✅ Deleted: {contact['name']} ({contact['email']})")
                    except HttpError as e:
                        failed_count += 1
                        print(f"  ❌ Failed: {contact['name']} - {e}")
                    except Exception as e:
                        failed_count += 1
                        print(f"  ❌ Error: {contact['name']} - {e}")
            
            print(f"\n📊 Final Results:")
            print(f"  ✅ Successfully deleted: {deleted_count} contacts")
            if failed_count > 0:
                print(f"  ❌ Failed to delete: {failed_count} contacts")
        else:
            print("\n💡 To actually delete these contacts, run with --no-dry-run")
            print("⚠️  WARNING: This action cannot be undone!")
    
    def export_contacts_to_delete(self, filename='contacts_to_delete.json'):
        """Export list of contacts that would be deleted"""
        contacts_to_delete = self.search_contacts()
        
        if contacts_to_delete:
            with open(filename, 'w') as f:
                json.dump(contacts_to_delete, f, indent=2)
            print(f"\n📁 Exported {len(contacts_to_delete)} contacts to {filename}")
        else:
            print("\n✅ No contacts to export")
    
    def get_stats(self):
        """Get statistics about contacts"""
        try:
            # Get total count
            results = self.people_service.people().connections().list(
                resourceName='people/me',
                pageSize=1,
                personFields='names'
            ).execute()
            
            total_contacts = results.get('totalPeople', 0)
            
            print(f"\n📊 Statistics:")
            print(f"  • Total contacts in Google: {total_contacts}")
            print(f"  • Bounced emails loaded: {len(self.bounced_emails)}")
            
            # If we have bounced emails, check how many match
            if self.bounced_emails:
                contacts_to_delete = self.search_contacts()
                print(f"  • Contacts to be deleted: {len(contacts_to_delete)}")
                print(f"  • Contacts that will remain: {total_contacts - len(contacts_to_delete)}")
            
        except HttpError as error:
            print(f'❌ An error occurred: {error}')


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Clean bounced emails from Google Contacts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load bounced emails from file and do a dry run
  %(prog)s --load-file bounced_emails.txt
  
  # Actually delete the contacts
  %(prog)s --load-file bounced_emails.txt --no-dry-run
  
  # Export list of contacts to be deleted
  %(prog)s --load-file bounced_emails.txt --export
        """
    )
    
    parser.add_argument('--load-file', type=str, default='bounced_emails.txt',
                       help='File containing bounced emails (one per line)')
    parser.add_argument('--no-dry-run', action='store_true',
                       help='Actually delete contacts (default is dry run)')
    parser.add_argument('--export', action='store_true',
                       help='Export list of contacts to be deleted to JSON')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics only')
    parser.add_argument('--credentials', type=str, default='credentials.json',
                       help='Path to Google OAuth credentials file')
    parser.add_argument('--token', type=str, default='token.pickle',
                       help='Path to token file for storing auth')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧹 Google Contacts Cleanup Tool")
    print("=" * 60)
    
    # Initialize cleaner
    cleaner = BounceContactCleaner(
        credentials_file=args.credentials,
        token_file=args.token
    )
    
    # Authenticate
    if not cleaner.authenticate():
        print("\n❌ Authentication failed. Please follow the instructions above.")
        return
    
    # Load bounced emails from file
    if not cleaner.load_bounced_from_file(args.load_file):
        print(f"\n📝 Please create a file '{args.load_file}' with bounced emails (one per line)")
        print("Example content:")
        print("  baduser@example.com")
        print("  invalid@domain.com")
        print("  bounced@email.com")
        return
    
    # Show statistics
    if args.stats:
        cleaner.get_stats()
        return
    
    # Export contacts to be deleted
    if args.export:
        cleaner.export_contacts_to_delete()
        return
    
    # Remove from contacts
    cleaner.remove_from_contacts(dry_run=not args.no_dry_run)
    
    print("\n" + "=" * 60)
    print("✅ Process complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()