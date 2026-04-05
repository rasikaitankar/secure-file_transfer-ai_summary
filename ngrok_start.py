"""
ngrok_start.py
--------------
HTTPS Tunnel via ngrok

Run this script INSTEAD of python app.py to get:
  - Local HTTP server on port 5000
  - Public HTTPS URL (e.g. https://abc123.ngrok.io)

NETWORKING CONCEPT — HTTPS / TLS:
  HTTP sends data in plaintext. Anyone intercepting packets can read the data.
  HTTPS = HTTP + TLS (Transport Layer Security).
  TLS adds:
    1. Encryption:      Data encrypted between client and server
    2. Authentication:  Server proves its identity via certificate
    3. Integrity:       Data cannot be tampered in transit

  ngrok creates an encrypted tunnel:
    Browser ──[HTTPS/TLS]──► ngrok servers ──[HTTP]──► your Flask app
    (ngrok handles the TLS certificate so you don't need to set one up)

INSTALLATION:
  pip install pyngrok flask

USAGE:
  python ngrok_start.py

OUTPUT:
  Public HTTPS URL: https://abc123.ngrok.io
  Share this URL — anyone on the internet can use your app over HTTPS!
"""

import threading
from app import app, seed_users

def start_ngrok():
    try:
        from pyngrok import ngrok

        public_url = ngrok.connect(8000)
        print("Public URL:", public_url)
        print("=" * 65)
        print(f"  🔐 HTTPS URL: {public_url}")
        print(f"  📡 Local URL: http://localhost:5000")
        print(f"  🌐 Share the HTTPS URL with anyone!")
        print(f"  📊 ngrok dashboard: http://localhost:4040")
        print("=" * 65)
        print()
        print("  NETWORKING CONCEPTS ACTIVE:")
        print(f"  ✅ HTTP  — Flask on port 5000")
        print(f"  ✅ HTTPS — TLS encryption via ngrok tunnel")
        print(f"  ✅ TCP   — reliable data transmission")
        print(f"  ✅ IP    — packets routed through ngrok servers")
        print("=" * 65)

    except ImportError:
        print("⚠️  pyngrok not installed.")
        print("   Run: pip install pyngrok")
        print("   Then re-run: python ngrok_start.py")
        print()
        print("   Alternatively, download ngrok from https://ngrok.com")
        print("   and run: ngrok http 5000")
        print()
        print("   Starting local HTTP server only...")

if __name__ == "__main__":
    seed_users()

    # Start ngrok in background thread
    ngrok_thread = threading.Thread(target=start_ngrok, daemon=True)
    ngrok_thread.start()

    # Small delay so ngrok URL prints before Flask startup messages
    import time
    time.sleep(1)

    print("\n[Flask] Starting server...")
    app.run(debug=False, host="0.0.0.0", port=8000)
