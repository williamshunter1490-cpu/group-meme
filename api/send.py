import os
import json
from http.server import BaseHTTPRequestHandler
import requests


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            sender = data.get("from", "")
            recipients = data.get("to", [])
            bcc = data.get("bcc", "")
            reply_to = data.get("reply_to", "")
            subject = data.get("subject", "")
            email_body = data.get("body", "")

            api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
            account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

            if not api_token or not account_id:
                self._json_response(
                    500,
                    {"error": "Missing Cloudflare environment variables."}
                )
                return

            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            }

            url = (
                "https://api.cloudflare.com/client/v4/accounts/"
                f"{account_id}/email/sending/emails"
            )

            results = []

            for email in recipients:
                email = email.strip()

                if not email:
                    continue

                personalization = {
                    "to": [{"email": email}]
                }

                if bcc:
                    personalization["bcc"] = [
                        {"email": bcc.strip()}
                    ]

                payload = {
                    "personalizations": [personalization],
                    "from": {
                        "email": sender,
                        "name": "Creative Structures Groups",
                    },
                    "reply_to": {
                        "email": reply_to
                    } if reply_to else None,
                    "subject": subject,
                    "content": [
                        {
                            "type": "text/plain",
                            "value": email_body,
                        },
                        {
                            "type": "text/html",
                            "value": (
                                "<p>"
                                + email_body.replace("\n", "<br>")
                                + "</p>"
                            ),
                        },
                    ],
                }

                payload = {
                    key: value
                    for key, value in payload.items()
                    if value is not None
                }

                try:
                    response = requests.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=20,
                    )

                    if response.status_code in (200, 201, 202):
                        results.append({
                            "email": email,
                            "status": "Sent",
                        })
                    else:
                        results.append({
                            "email": email,
                            "status": "Failed",
                            "reason": response.text,
                        })

                except Exception as exc:
                    results.append({
                        "email": email,
                        "status": "Failed",
                        "reason": str(exc),
                    })

            self._json_response(200, {"results": results})

        except Exception as exc:
            self._json_response(
                500,
                {"error": str(exc)}
            )

    def do_GET(self):
        self._json_response(
            200,
            {"status": "Mail API is running"}
        )

    def _json_response(self, status_code, payload):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(
            json.dumps(payload).encode("utf-8")
        )
