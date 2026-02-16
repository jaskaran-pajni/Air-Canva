# debug.py
import sys
import os
import traceback

def debug_print(msg):
    print(f"🔍 DEBUG: {msg}")
    sys.stdout.flush()  # Force print to show immediately

try:
    debug_print("Starting application...")
    debug_print(f"Python version: {sys.version}")
    debug_print(f"Current directory: {os.getcwd()}")
    debug_print(f"Files in directory: {os.listdir('.')}")
    
    # Try to import your app
    debug_print("Attempting to import server...")
    from server import app
    debug_print("✅ Server imported successfully")
    
except Exception as e:
    debug_print(f"❌ ERROR: {e}")
    traceback.print_exc()
    sys.stdout.flush()