import os
import html
import requests

from flask import Flask, request, jsonify, send_file

app = Flask(__name__)


@app.get("/")
def home():
    return send_file("index.html")


@app.get("/api/send")
def api_status():
    return jsonify({
        "status": "Mail API is running"
    })


@app.post("/api/send")
def send_email():
    try:
        data = request.get_json(force=True)

        sender = data.get("from", "").strip()
        recipients = data.get("to", [])
        bcc = data.get("bcc", "").strip()
        reply_to = data.get("reply_to", "").strip()
        subject = data.get("subject", "").strip()
        email_body = data.get("body", "")

        if isinstance(recipients, str):
            recipients = [
                x.strip()
                for x in recipients.splitlines()
                if x.strip()
            ]

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

        if not sender:
            return jsonify({"error": "Send From is required."}), 400

        if not recipients:
            return jsonify({"error": "At least one recipient is required."}), 400

        if not subject:
            return jsonify({"error": "Subject is required."}), 400

        cloudflare_url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{account_id}/email/sending/emails"
        )

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        results = []

        for recipient in recipients:
            try:
                payload = {
                    "from": sender,
                    "to": recipient,
                    "subject": subject,
                    "text": email_body,
                    "html": (
                        "<p>"
                        + html.escape(email_body).replace("\n", "<br>")
                        + "</p>"
                    ),
                }

                if bcc:
                    payload["bcc"] = bcc

                if reply_to:
                    payload["reply_to"] = reply_to

                response = requests.post(
                    cloudflare_url,
                    headers=headers,
                    json=payload,
                    timeout=30,
                )

                try:
                    response_data = response.json()
                except Exception:
                    response_data = {}

                if response.ok and response_data.get("success", True):
                    results.append({
                        "email": recipient,
                        "status": "Sent"
                    })
                else:
                    results.append({
                        "email": recipient,
                        "status": "Failed",
                        "reason": response.text
                    })

            except Exception as exc:
                results.append({
                    "email": recipient,
                    "status": "Failed",
                    "reason": str(exc)
                })

        sent = sum(
            1 for result in results
            if result["status"] == "Sent"
        )

        failed = len(results) - sent

        return jsonify({
            "results": results,
            "sent": sent,
            "failed": failed,
            "total": len(results)
        })

    except Exception as exc:
        return jsonify({
            "error": str(exc)
        }), 500
