import os
import json
from http.server import BaseHTTPRequestHandler
import requests

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            sender = data.get('from')
            recipients = data.get('to', [])
            bcc = data.get('bcc', '')
            reply_to = data.get('reply_to', '')
            subject = data.get('subject', '')
            html_body = data.get('body', '')

            api_token = os.environ.get('CLOUDFLARE_API_TOKEN')
            account_id = os.environ.get('CLOUDFLARE_ACCOUNT_ID')

            if not api_token or not account_id:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Server configuration error: Missing Cloudflare credentials.'}).encode())
                return

            results = []
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            }

            # Cloudflare Email Sending API endpoint
            url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/email/sending/emails'

            for email in recipients:
                email = email.strip()
                if not email:
                    continue

                payload = {
                    "personalizations": [{"to": [{"email": email}]}],
                    "from": {"email": sender, "name": "Creative Structures Groups"},
                    "reply_to": {"email": reply_to},
                    "subject": subject,
                    "content": [
                        {"type": "text/plain", "value": html_body},
                        {"type": "text/html", "value": f"<p>{html_body.replace(chr(10), '<br>')}</p>"}
                    ]
                }

                if bcc:
                    payload["personalizations"][0]["bcc"] = [{"email": bcc.strip()}]

                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=10)
                    if response.status_code in [200, 201, 202]:
                        results.append({"email": email, "status": "Sent"})
                    else:
                        results.append({"email": email, "status": "Failed", "reason": response.text})
                except Exception as e:
                    results.append({"email": email, "status": "Failed", "reason": str(e)})

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'results': results}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())