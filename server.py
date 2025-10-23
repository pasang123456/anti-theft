"""
Anti-Theft Alert Server (Flask)
- POST /api/alert
  JSON payload:
    {
      "deviceName": "John's Pixel",
      "devicePhone": "+1234567890",
      "reason": "theft" | "pin_attempt" | "tamper",
      "contacts": [
        {"name": "Alice", "phone": "+19998887777", "push_token": "...optional FCM token..."},
        ...
      ]
    }

Notes:
- Real detection of PIN attempts must be done by a native mobile app. This server only receives events and dispatches notifications.
- Put credentials (Firebase service account JSON, Twilio SID/token, Twilio from number) into environment variables or a secure secrets store.
"""

import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from typing import List, Dict

# Optional integrations
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except Exception:
    FIREBASE_AVAILABLE = False

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except Exception:
    TWILIO_AVAILABLE = False

load_dotenv()  # load .env if present

app = Flask(__name__)

# Enable CORS for development (allow browser pages served from file:// or localhost to call this API)
CORS(app)

# Serve the prototype HTML from the project root so the demo can call the API from same origin
@app.route("/")
def index():
    try:
        with open("anti-theft-prototype.html", "r", encoding="utf-8") as f:
            return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
    except Exception as e:
        return jsonify({"error": "prototype HTML not found", "details": str(e)}), 404


# Helpful debug logging for incoming requests (prints method, path, headers and small bodies)
@app.before_request
def log_request_info():
    try:
        app.logger.info(f"Incoming request: {request.method} {request.path}")
        # log headers at debug level to avoid noisy info logs
        app.logger.debug("Request headers: %s", dict(request.headers))
        if request.method in ("POST", "PUT", "PATCH"):
            # small body only (avoid logging huge payloads)
            data = request.get_data(as_text=True)
            if data:
                app.logger.debug("Request body: %s", data)
    except Exception:
        # don't let logging errors interrupt request handling
        pass

# Load environment config
FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")  # stringified JSON or path
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")  # e.g. "+15551234567"

# Initialize Firebase Admin if configured and library available
firebase_initialized = False
if FIREBASE_AVAILABLE and FIREBASE_SERVICE_ACCOUNT_JSON:
    try:
        # support passing a path or a JSON string
        if os.path.exists(FIREBASE_SERVICE_ACCOUNT_JSON):
            cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_JSON)
        else:
            cred_dict = json.loads(FIREBASE_SERVICE_ACCOUNT_JSON)
            cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
        app.logger.info("Firebase Admin initialized.")
    except Exception as e:
        app.logger.warning(f"Could not initialize Firebase Admin SDK: {e}")

# Initialize Twilio if available
twilio_client = None
if TWILIO_AVAILABLE and TWILIO_SID and TWILIO_TOKEN:
    try:
        twilio_client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        app.logger.info("Twilio client initialized.")
    except Exception as e:
        app.logger.warning(f"Could not initialize Twilio client: {e}")

def build_message(device_name: str, device_phone: str, reason: str) -> str:
    if reason == "theft":
        return f"{device_name} ({device_phone}) may have been stolen."
    if reason == "pin_attempt":
        return f"{device_name} experienced multiple failed PIN attempts."
    return f"{device_name} reported tampering or SIM change."

def send_push_to_tokens(tokens: List[str], title: str, body: str) -> Dict:
    """
    Send a multicast message via FCM. Returns a summary dict.
    """
    if not firebase_initialized:
        return {"success": 0, "failure": len(tokens), "error": "firebase not configured"}

    # Prepare message payload
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        tokens=tokens,
        data={"source": "anti-theft-server", "body": body}
    )
    resp = messaging.send_multicast(message)
    return {"success": resp.success_count, "failure": resp.failure_count, "responses": [r.__dict__ for r in resp.responses]}

def send_sms(phone: str, body: str) -> Dict:
    """
    Send SMS via Twilio. Returns result dict or error.
    """
    if not twilio_client or not TWILIO_FROM:
        return {"ok": False, "error": "twilio not configured"}
    try:
        msg = twilio_client.messages.create(
            body=body,
            from_=TWILIO_FROM,
            to=phone
        )
        return {"ok": True, "sid": getattr(msg, "sid", None)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.route("/api/alert", methods=["POST", "OPTIONS"])
def api_alert():
    # Respond to CORS preflight requests from browsers
    if request.method == "OPTIONS":
        return jsonify({}), 200

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "invalid json"}), 400

    device_name = payload.get("deviceName", "Unknown device")
    device_phone = payload.get("devicePhone", "Unknown phone")
    reason = payload.get("reason", "unknown")
    contacts = payload.get("contacts", [])

    if not isinstance(contacts, list) or len(contacts) == 0:
        return jsonify({"error": "contacts must be a non-empty list"}), 400

    message_body = build_message(device_name, device_phone, reason)
    title = "Anti-Theft Alert"

    results = {
        "sent_push": [],
        "sent_sms": [],
        "skipped": []
    }

    # Collect push tokens to batch-send
    tokens_to_notify = []
    token_to_contact = {}  # map token -> contact info
    for c in contacts:
        if isinstance(c, dict) and c.get("push_token"):
            token = c["push_token"]
            tokens_to_notify.append(token)
            token_to_contact[token] = c

    # Send push notifications in one batch (if tokens exist)
    if tokens_to_notify:
        push_resp = send_push_to_tokens(tokens_to_notify, title, message_body)
        # push_resp contains counts; we log at token-level if needed (here we append summary)
        results["push_summary"] = push_resp

    # Send SMS to contacts that have phone numbers (fallback)
    for c in contacts:
        phone = c.get("phone")
        name = c.get("name", "")
        push_token = c.get("push_token")
        # If contact had a push_token and push was sent, we still optionally send SMS according to policy.
        if phone:
            sms_resp = send_sms(phone, message_body)
            results["sent_sms"].append({"to": phone, "name": name, **sms_resp})
        else:
            # nothing to do (no push token or phone)
            if not push_token:
                results["skipped"].append({"contact": c, "reason": "no push_token or phone"})

    # Log server-side for auditing
    app.logger.info("Alert processed", extra={"device": device_name, "reason": reason, "contacts": len(contacts)})

    return jsonify({"status": "processed", "message": message_body, "results": results}), 200

if __name__ == "__main__":
    # Run in debug during development only. Use a proper WSGI server (gunicorn/uvicorn) in production.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")), debug=True)
