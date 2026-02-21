#!/usr/bin/env python3
"""
Newsletter subscription endpoint for storing email addresses.
Stores emails in a JSON file for later processing.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Path to store newsletter subscriptions
NEWSLETTER_FILE = Path(__file__).parent.parent / 'data' / 'newsletter_subscriptions.json'

def ensure_data_dir():
    """Ensure the data directory exists."""
    NEWSLETTER_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_subscriptions():
    """Load existing subscriptions from file."""
    ensure_data_dir()
    if NEWSLETTER_FILE.exists():
        try:
            with open(NEWSLETTER_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_subscription(email):
    """Save a new subscription to the file."""
    subscriptions = load_subscriptions()
    
    # Check if email already exists
    if any(sub.get('email') == email for sub in subscriptions):
        return False
    
    # Add new subscription
    subscriptions.append({
        'email': email,
        'subscribed_at': datetime.now().isoformat(),
        'source': 'blog'
    })
    
    # Save to file
    ensure_data_dir()
    with open(NEWSLETTER_FILE, 'w') as f:
        json.dump(subscriptions, f, indent=2)
    
    return True

def handle_request(method, path, headers, body):
    """Handle HTTP request for newsletter subscription."""
    if method != 'POST':
        return {
            'status': 405,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        data = json.loads(body) if body else {}
        email = data.get('email', '').strip()
        
        if not email or '@' not in email:
            return {
                'status': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid email address'})
            }
        
        if save_subscription(email):
            return {
                'status': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'message': 'Successfully subscribed', 'email': email})
            }
        else:
            return {
                'status': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'message': 'Already subscribed', 'email': email})
            }
    except json.JSONDecodeError:
        return {
            'status': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Invalid JSON'})
        }

