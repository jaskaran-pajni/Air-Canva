# wsgi.py
import sys
import os
import traceback

print("🔧 WSGI: Starting up...", flush=True)

try:
    from server import app
    print("✅ WSGI: Successfully imported app from server", flush=True)
except Exception as e:
    print("❌ WSGI Error: Failed to import app", flush=True)
    traceback.print_exc()
    sys.exit(1)

# This is what gunicorn will look for
application = app

print("✅ WSGI: Application ready", flush=True)