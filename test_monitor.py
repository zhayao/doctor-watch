#!/usr/bin/env python3
"""
Test script for the doctor appointment monitor.
Run this to test your configuration and web scraping locally.

Usage:
    # Activate virtual environment first
    source venv/bin/activate
    python test_monitor.py
"""

import os
import sys
import logging

# Check if we're in a virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("⚠️  Warning: Virtual environment not detected!")
    print("   Recommended: source venv/bin/activate")
    print()

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ python-dotenv not installed!")
    print("   Run: pip install python-dotenv")
    sys.exit(1)

# Add the function directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'doctor-watch'))

try:
    from function_app import AppointmentMonitor
except ImportError as e:
    print(f"❌ Failed to import function_app: {e}")
    print("   Make sure you're in the project root directory")
    sys.exit(1)

# Load environment variables from local.settings.json equivalent
load_dotenv()

def test_pushover():
    """Test Pushover notification"""
    print("Testing Pushover notification...")
    
    monitor = AppointmentMonitor()
    
    if not monitor.pushover_token or not monitor.pushover_user:
        print("❌ Pushover credentials not configured")
        print("Please set PUSHOVER_TOKEN and PUSHOVER_USER environment variables")
        return False
    
    success = monitor.send_pushover_notification(
        "🧪 Test notification from Doctor Watch", 
        "Test Notification"
    )
    
    if success:
        print("✅ Pushover notification sent successfully!")
        return True
    else:
        print("❌ Failed to send Pushover notification")
        return False

def test_web_scraping():
    """Test web scraping functionality"""
    print("Testing web scraping...")
    
    monitor = AppointmentMonitor()
    
    if not monitor.target_url:
        print("❌ TARGET_URL not configured")
        return False
    
    print(f"Scraping URL: {monitor.target_url}")
    appointments = monitor.scrape_appointments()
    
    print(f"Found {len(appointments)} potential appointments:")
    
    for i, apt in enumerate(appointments, 1):
        print(f"\n{i}. {apt.get('type', 'unknown_type')}")
        if apt.get('text'):
            print(f"   Text: {apt['text'][:100]}...")
        if apt.get('found_dates'):
            print(f"   Dates: {apt['found_dates']}")
        if apt.get('context'):
            print(f"   Context: {apt['context'][:100]}...")
    
    if appointments:
        print("✅ Web scraping working - found appointment data")
        return True
    else:
        print("⚠️  No appointments found - this might be normal or the website structure changed")
        return True

def test_full_flow():
    """Test the complete appointment checking flow"""
    print("Testing complete appointment checking flow...")
    
    monitor = AppointmentMonitor()
    monitor.check_for_appointments()
    
    print("✅ Full flow test completed - check logs above for details")

def main():
    """Run all tests"""
    print("🏥 Doctor Appointment Monitor Test Suite")
    print("=" * 50)
    
    # Set up logging to see detailed output
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test environment variables
    print("\n1. Checking Environment Variables:")
    env_vars = ['TARGET_URL', 'DOCTOR_NAME', 'PUSHOVER_TOKEN', 'PUSHOVER_USER']
    
    for var in env_vars:
        value = os.getenv(var)
        print(value)
        if value and not value.startswith('<'):
            print(f"   ✅ {var}: {'*' * len(value) if 'TOKEN' in var or 'USER' in var else value}")
        else:
            print(f"   ❌ {var}: Not configured")
    
    # Test web scraping
    print("\n2. Testing Web Scraping:")
    test_web_scraping()
    
    # Test Pushover (optional - will send actual notification)
    print("\n3. Testing Pushover Notification:")
    response = input("Send test notification to your phone? (y/N): ")
    if response.lower() in ['y', 'yes']:
        test_pushover()
    else:
        print("   ⏭️  Skipping Pushover test")
    
    # Test full flow (optional)
    print("\n4. Testing Full Flow:")
    response = input("Run complete appointment check? This may send a notification if appointments are found. (y/N): ")
    if response.lower() in ['y', 'yes']:
        test_full_flow()
    else:
        print("   ⏭️  Skipping full flow test")
    
    print("\n" + "=" * 50)
    print("✅ Test suite completed!")
    print("If everything looks good, you can deploy to Azure Functions.")

if __name__ == "__main__":
    main()
