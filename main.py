import os, json, time, hashlib, datetime, threading, requests, schedule, pytz
from flask import Flask, request, jsonify

APP_ID        = os.getenv("SEATALK_APP_ID")
CLIENT_ID     = os.getenv("SEATALK_CLIENT_ID")
CLIENT_SECRET = os.getenv("SEATALK_CLIENT_SECRET")
SIGN_SECRET   = os.getenv("SEATALK_SIGNING_SECRET").encode()
GROUP_ID      = os.getenv("SEATALK_GROUP_ID")
TZ = pytz.timezone("America/Sao_Paulo")

app = Flask(__name__)

def valid_sig(body: bytes, header_sig: str) -> bool:
    return hashlib.sha256(body + SIGN_SECRET).hexdigest() == header_sig

@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data()
    if not valid_sig(body, request.headers.get("signature", "")):
        return "", 403
    data = json.loads(body)
    if data.get("event_type") == "event_verification":
        return jsonify({"seatalk_challenge": data["event"]["seatalk_challenge"]})
    return "", 200

def get_token():
    resp = requests.post(
        "https://openapi.seatalk.io/auth/v1/token",
        json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def send_reminder():
    now = datetime.datetime.now(TZ)
    if now.weekday() >= 5:
        return
    token = get_token()
    msg = {
        "group_id": GROUP_ID,
        "message": {
            "tag": "text",
            "text": {"content": "Você já fez seu Check-In hoje?"}
        }
    }
    requests.post(
        "https://openapi.seatalk.io/messaging/v2/group-chats/messages",
        json=msg,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )

def scheduler_loop():
    schedule.every().day.at("13:45").do(send_reminder)
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    threading.Thread(target=scheduler_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
