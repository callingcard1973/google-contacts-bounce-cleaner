#!/home/tudor/google_contacts_venv/bin/python3
"""
Test Google API authentication without browser
"""

import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# OAuth scopes needed
SCOPES = [
    'https://www.googleapis.com/auth/contacts',
    'https://www.googleapis.com/auth/gmail.send'
]

def test_auth():
    """Test authentication"""
    creds = None
    
    # Check if we have existing token
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, get them
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("No valid credentials found.")
            print("\nTo authenticate:")
            print("1. Run this on a computer with a browser")
            print("2. Or use the following URL manually:")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            
            # Get authorization URL
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            print(f"\nVisit this URL: {auth_url}")
            print("\nAfter authorizing, you'll get a code. Enter it here:")
            
            try:
                auth_code = input("Enter authorization code: ").strip()
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
                
                # Save credentials
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                    
                print("✅ Authentication successful!")
                
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                return False
    
    # Test the APIs
    try:
        # Test People API
        people_service = build('people', 'v1', credentials=creds)
        profile = people_service.people().get(
            resourceName='people/me',
            personFields='names,emailAddresses'
        ).execute()
        
        print("\n✅ People API working!")
        print(f"Authenticated as: {profile.get('names', [{}])[0].get('displayName', 'Unknown')}")
        
        # Test Gmail API
        gmail_service = build('gmail', 'v1', credentials=creds)
        gmail_profile = gmail_service.users().getProfile(userId='me').execute()
        
        print("✅ Gmail API working!")
        print(f"Gmail: {gmail_profile['emailAddress']}")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

if __name__ == '__main__':
    test_auth()