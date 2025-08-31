import os
from app import app, init_db

print("\nStarting School Management System...")
print("================================================")

try:
    print("✓ Flask application loaded successfully")
    
    # Check if database exists and initialize if needed
    db_path = 'school.db'
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        print("✓ Creating new database...")
        init_db()
        print("✓ Database initialized successfully")
    else:
        print("✓ Database will be initialized automatically")
    
    print("\nStarting server...")
    print("Access the application at: http://localhost:5000")
    print("Admin login: email='admin', password='admin'")
    print("\nPress Ctrl+C to stop the server")
    print("================================================")
    
    # Run the application
    app.run(debug=True, host='0.0.0.0')
    
except Exception as e:
    print(f"✗ Error: {str(e)}")
    print("Please check your configuration and try again.")