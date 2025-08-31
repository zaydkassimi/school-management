#!/usr/bin/env python3
"""
Simple test script to verify the Flask application setup
"""

import sqlite3
import os

def test_database_creation():
    """Test if the database and tables are created correctly"""
    print("Testing database creation...")
    
    # Check if database file exists
    if os.path.exists('school.db'):
        print("✓ Database file created successfully")
    else:
        print("✗ Database file not found")
        return False
    
    # Test database connection and table structure
    try:
        conn = sqlite3.connect('school.db')
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        
        expected_tables = ['users', 'grades', 'absences']
        for table in expected_tables:
            if table in tables:
                print(f"✓ Table '{table}' created successfully")
            else:
                print(f"✗ Table '{table}' not found")
                return False
        
        conn.close()
        print("✓ Database structure is correct")
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_flask_import():
    """Test if Flask can be imported"""
    print("\nTesting Flask import...")
    try:
        from flask import Flask
        print("✓ Flask imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        return False

if __name__ == "__main__":
    print("Flask School Management System - Setup Test")
    print("=" * 50)
    
    # Test Flask import
    flask_ok = test_flask_import()
    
    # Test database (will be created when app runs)
    print("\nNote: Database will be created when you run 'python app.py'")
    
    if flask_ok:
        print("\n✓ All tests passed! You can now run:")
        print("  python app.py")
        print("\nThen visit http://localhost:5000 in your browser")
        print("\nAdmin login: email='admin', password='admin'")
    else:
        print("\n✗ Some tests failed. Please check the requirements.") 