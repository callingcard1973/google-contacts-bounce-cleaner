#!/home/tudor/google_contacts_venv/bin/python3
"""
Gmail API Email Sender
Send emails using Gmail API with OAuth2 authentication
Supports bulk sending, templates, and rate limiting
"""

import os
import pickle
import base64
import time
import csv
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# OAuth scopes needed for Gmail sending
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

class GmailSender:
    def __init__(self, credentials_file='credentials.json', token_file='gmail_token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.gmail_service = None
        self.sent_count = 0
        self.failed_count = 0
        self.rate_limit_delay = 1  # seconds between emails
        
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
                    print("\n📋 To set up Google Cloud credentials for Gmail:")
                    print("1. Go to https://console.cloud.google.com/")
                    print("2. Create a new project or select existing")
                    print("3. Enable the Gmail API:")
                    print("   - Go to APIs & Services → Enable APIs")
                    print("   - Search for 'Gmail API'")
                    print("   - Click Enable")
                    print("4. Create OAuth 2.0 credentials:")
                    print("   - Go to APIs & Services → Credentials")
                    print("   - Click '+ CREATE CREDENTIALS' → OAuth client ID")
                    print("   - Application type: Desktop app")
                    print("   - Name it (e.g., 'Gmail Sender')")
                    print("5. Download the credentials.json file")
                    print("6. Place it in the same directory as this script")
                    return False
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build Gmail API service
        self.gmail_service = build('gmail', 'v1', credentials=creds)
        print("✅ Successfully authenticated with Gmail API")
        return True
    
    def create_message(self, sender, to, subject, message_text, html_message=None, attachments=None):
        """Create a message for an email."""
        if html_message:
            message = MIMEMultipart('alternative')
        else:
            message = MIMEText(message_text, 'plain', 'utf-8')
            
        if isinstance(message, MIMEMultipart):
            message['to'] = to
            message['from'] = sender
            message['subject'] = subject
            
            # Add plain text part
            text_part = MIMEText(message_text, 'plain', 'utf-8')
            message.attach(text_part)
            
            # Add HTML part if provided
            if html_message:
                html_part = MIMEText(html_message, 'html', 'utf-8')
                message.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for file_path in attachments:
                    if os.path.isfile(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        message.attach(part)
        else:
            message['to'] = to
            message['from'] = sender
            message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw_message}
    
    def send_message(self, message, dry_run=False):
        """Send an email message."""
        if dry_run:
            print(f"  📧 DRY RUN: Would send to {message.get('to', 'unknown')}")
            return True
            
        try:
            sent_message = self.gmail_service.users().messages().send(
                userId="me", 
                body=message
            ).execute()
            
            self.sent_count += 1
            return True
            
        except HttpError as error:
            print(f"  ❌ Error sending email: {error}")
            self.failed_count += 1
            return False
        except Exception as error:
            print(f"  ❌ Unexpected error: {error}")
            self.failed_count += 1
            return False
    
    def load_template(self, template_file):
        """Load email template from file"""
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f"❌ Template file {template_file} not found")
            return None
    
    def replace_variables(self, template, variables):
        """Replace variables in template like {{name}}, {{email}}, etc."""
        content = template
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content
    
    def send_bulk_emails(self, recipients_file, subject, template_file=None, message_text=None, 
                        html_template=None, dry_run=True, delay=None):
        """Send bulk emails to recipients from CSV file"""
        
        if delay:
            self.rate_limit_delay = delay
            
        # Load template if provided
        template = None
        if template_file:
            template = self.load_template(template_file)
            if not template:
                return False
        elif not message_text:
            print("❌ Either template_file or message_text must be provided")
            return False
        
        # Load HTML template if provided
        html_template_content = None
        if html_template:
            html_template_content = self.load_template(html_template)
        
        # Get sender email from credentials
        try:
            profile = self.gmail_service.users().getProfile(userId='me').execute()
            sender_email = profile['emailAddress']
            print(f"📤 Sending from: {sender_email}")
        except Exception as e:
            print(f"❌ Could not get sender email: {e}")
            return False
        
        print(f"\n{'🔍 DRY RUN MODE' if dry_run else '📧 SENDING EMAILS'}")
        print(f"📄 Loading recipients from: {recipients_file}")
        
        # Load recipients
        recipients = []
        try:
            with open(recipients_file, 'r', encoding='utf-8') as f:
                if recipients_file.endswith('.csv'):
                    reader = csv.DictReader(f)
                    recipients = list(reader)
                else:
                    # Plain text file with emails, one per line
                    for line_num, line in enumerate(f, 1):
                        email = line.strip()
                        if email and '@' in email and not email.startswith('#'):
                            recipients.append({'email': email, 'line': line_num})
        except Exception as e:
            print(f"❌ Error reading recipients file: {e}")
            return False
        
        if not recipients:
            print("❌ No recipients found")
            return False
            
        print(f"📊 Found {len(recipients)} recipients")
        
        # Send emails
        for i, recipient in enumerate(recipients, 1):
            email = recipient.get('email', '').strip()
            if not email:
                continue
                
            print(f"\n[{i}/{len(recipients)}] Processing: {email}")
            
            # Prepare message content
            if template:
                # Use template with variable replacement
                final_message = self.replace_variables(template, {
                    'email': email,
                    'name': recipient.get('name', email.split('@')[0]),
                    'first_name': recipient.get('first_name', ''),
                    'last_name': recipient.get('last_name', ''),
                    **recipient  # Include all CSV columns as variables
                })
            else:
                final_message = message_text
            
            # Prepare HTML content if available
            final_html = None
            if html_template_content:
                final_html = self.replace_variables(html_template_content, {
                    'email': email,
                    'name': recipient.get('name', email.split('@')[0]),
                    'first_name': recipient.get('first_name', ''),
                    'last_name': recipient.get('last_name', ''),
                    **recipient
                })
            
            # Create and send message
            try:
                message = self.create_message(
                    sender=sender_email,
                    to=email,
                    subject=subject,
                    message_text=final_message,
                    html_message=final_html
                )
                
                success = self.send_message(message, dry_run)
                
                if success and not dry_run:
                    print(f"  ✅ Sent successfully")
                elif success and dry_run:
                    print(f"  👀 Ready to send")
                    
                # Rate limiting
                if not dry_run and i < len(recipients):
                    time.sleep(self.rate_limit_delay)
                    
            except Exception as e:
                print(f"  ❌ Error processing {email}: {e}")
                self.failed_count += 1
        
        # Final summary
        print(f"\n{'=' * 50}")
        print(f"📊 SUMMARY:")
        if not dry_run:
            print(f"  ✅ Sent: {self.sent_count}")
            print(f"  ❌ Failed: {self.failed_count}")
            print(f"  📈 Success rate: {(self.sent_count/(self.sent_count+self.failed_count)*100):.1f}%")
        else:
            print(f"  👀 Ready to send: {len(recipients)}")
            print(f"  💡 Run with --no-dry-run to actually send")
        print(f"{'=' * 50}")
        
        return True
    
    def send_single_email(self, to_email, subject, message_text, html_message=None, dry_run=True):
        """Send a single email"""
        try:
            profile = self.gmail_service.users().getProfile(userId='me').execute()
            sender_email = profile['emailAddress']
        except Exception as e:
            print(f"❌ Could not get sender email: {e}")
            return False
        
        print(f"\n{'🔍 DRY RUN' if dry_run else '📧 SENDING'}")
        print(f"From: {sender_email}")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        
        message = self.create_message(
            sender=sender_email,
            to=to_email,
            subject=subject,
            message_text=message_text,
            html_message=html_message
        )
        
        success = self.send_message(message, dry_run)
        
        if success:
            if dry_run:
                print("✅ Ready to send")
            else:
                print("✅ Sent successfully")
        
        return success


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Send emails using Gmail API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send single email (dry run)
  %(prog)s --to user@example.com --subject "Test" --message "Hello World"
  
  # Send bulk emails from CSV
  %(prog)s --bulk recipients.csv --subject "Newsletter" --template template.txt
  
  # Actually send emails (not dry run)  
  %(prog)s --bulk recipients.csv --subject "News" --template template.txt --no-dry-run
  
  # With rate limiting
  %(prog)s --bulk recipients.csv --subject "News" --template template.txt --delay 2
        """
    )
    
    # Authentication options
    parser.add_argument('--credentials', type=str, default='credentials.json',
                       help='Path to Google OAuth credentials file')
    parser.add_argument('--token', type=str, default='gmail_token.pickle',
                       help='Path to Gmail token file')
    
    # Single email options
    parser.add_argument('--to', type=str, help='Recipient email address')
    parser.add_argument('--subject', type=str, help='Email subject')
    parser.add_argument('--message', type=str, help='Email message text')
    parser.add_argument('--html', type=str, help='HTML message content')
    
    # Bulk email options
    parser.add_argument('--bulk', type=str, help='Recipients file (CSV or text)')
    parser.add_argument('--template', type=str, help='Text template file')
    parser.add_argument('--html-template', type=str, help='HTML template file')
    
    # Sending options
    parser.add_argument('--no-dry-run', action='store_true',
                       help='Actually send emails (default is dry run)')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between emails in seconds (default: 1.0)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📧 Gmail API Email Sender")
    print("=" * 60)
    
    # Initialize sender
    sender = GmailSender(
        credentials_file=args.credentials,
        token_file=args.token
    )
    
    # Authenticate
    if not sender.authenticate():
        print("\n❌ Authentication failed. Please follow the instructions above.")
        return
    
    # Send emails
    if args.bulk:
        # Bulk sending
        if not args.subject:
            print("❌ Subject is required for bulk sending")
            return
            
        success = sender.send_bulk_emails(
            recipients_file=args.bulk,
            subject=args.subject,
            template_file=args.template,
            message_text=args.message,
            html_template=args.html_template,
            dry_run=not args.no_dry_run,
            delay=args.delay
        )
        
    elif args.to and args.subject:
        # Single email
        if not (args.message or args.html):
            print("❌ Message content is required")
            return
            
        success = sender.send_single_email(
            to_email=args.to,
            subject=args.subject,
            message_text=args.message or "No text content",
            html_message=args.html,
            dry_run=not args.no_dry_run
        )
        
    else:
        print("❌ Please provide either:")
        print("   Single email: --to, --subject, --message")
        print("   Bulk emails: --bulk, --subject, (--template or --message)")
        parser.print_help()
        return
    
    print("\n" + "=" * 60)
    print("✅ Process complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()