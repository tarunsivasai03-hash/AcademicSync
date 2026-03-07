"""
Entry point for the AcademicSync Flask backend.

Usage:
    python run.py                      # development server
    FLASK_ENV=production python run.py # production (use gunicorn instead)
"""
import os
from app import create_app

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n{'='*50}")
    print(f"  AcademicSync API  |  {env.upper()}")
    print(f"  http://localhost:{port}")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", port=port, debug=(env == "development"))
