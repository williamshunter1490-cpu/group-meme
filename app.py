import os
import requests
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)


@app.route("/")
def home():
    return send_file("index.html")


@app.route("/api/send", methods=["GET"])
def api_status():
    return jsonify({"status": "Mail API is running"})


@app.route("/api/send", methods=["POST"])
def send_email():
    data = request.get_json(silent=True) or {}

    send_from = str(data.get("from", "")).strip()
    recipients = data.get("to", [])
    reply_to = str(data.get("reply_to", "")).strip()
    subject = str(data.get("subject", "")).strip()
    body = str(data.get("body", ""))

    if not send_from:
        return jsonify({"error": "Send From is required."}), 400

    if not isinstance(recipients, list) or not recipients:
        return jsonify({"error": "At least one recipient is required."}), 400

    recipients = [
        str(email).strip()
        for email in recipients
        if str(email).strip()
    ]

    if not recipients:
        return jsonify({"error": "At least one valid recipient is required."}), 400

    if not subject:
        return jsonify({"error": "Subject is required."}), 400

    if not body.strip():
        return jsonify({"error": "Email body is required."}), 400

    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

    if not api_token:
        return jsonify({
            "error": "CLOUDFLARE_API_TOKEN is not configured."
        }), 500

    if not account_id:
        return jsonify({
            "error": "CLOUDFLARE_ACCOUNT_ID is not configured."
        }), 500

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/email/sending/send"
    )

    payload = {
        "from": send_from,
        "to": recipients,
        "subject": subject,
        "text": body,
        "html": body.replace("\n", "<br>")
    }

    if reply_to:
        payload["reply_to"] = reply_to

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        try:
            result = response.json()
        except Exception:
            result = {
                "error": response.text or "Unknown Cloudflare response"
            }

        if response.ok and result.get("success", True):
            return jsonify({
                "success": True,
                "status": "Sent"
            }), 200

        return jsonify(
            result if isinstance(result, dict) else {
                "error": result
            }
        ), response.status_code

    except requests.RequestException as exc:
        return jsonify({
            "error": f"Cloudflare request failed: {str(exc)}"
        }), 502


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
