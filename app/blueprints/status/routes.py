from flask import Blueprint, request, jsonify
import sqlite3
import datetime
import os
import traceback

status_bp = Blueprint("status", __name__)

# Path to Wizarr DB
DB_PATH = "/data/database/database.db"
API_KEY = os.environ.get("WIZARR_API_KEY")  

@status_bp.route("/api/status", methods=["GET"])
def wizarr_status():
    try:
        # Enforce explicit API key
        if not API_KEY:
            return jsonify({"error": "API key not configured"}), 401

        # Verify incoming key
        key = request.headers.get("X-API-Key")
        if key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM user")
        users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM invitation")
        invites = cursor.fetchone()[0]

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        cursor.execute("""
            SELECT COUNT(*) FROM invitation 
            WHERE used = 0 AND (expires IS NULL OR expires >= ?)
        """, (now,))
        pending = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM invitation 
            WHERE expires IS NOT NULL AND expires < ?
        """, (now,))
        expired = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            "users": users,
            "invites": invites,
            "pending": pending,
            "expired": expired
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
