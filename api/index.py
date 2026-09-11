import datetime
import re
import secrets
import string
import time
from flask import Flask, jsonify, request
import requests
import urllib3

# SSL verification সতর্কতা নিষ্ক্রিয় করা
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Branding and Config
OWNER = "@dipcb001"

# Prank IDs and Title Mapping
PRANK_TITLES = {
    "8810": "আপনি আমার গার্লফ্রেন্ডকে কল করেন কেন?",
    "8805": "গাজার মতো দুর্গন্ধ!",
    "8803": "পিজ্জা ডেলিভারি",
    "8809": "আপনি কেন আমাকে কল করেন?",
    "8808": "আপনি আমার ওয়াই-ফাই চুরি করছেন!",
    "8806": "আপনার কামরার হৈচৈ আওয়াজ",
    "8804": "আপনার ট্যাক্সি আপনার জন্য অপেক্ষা করছে",
    "8807": "আপনার কুকুরটি খুবই ক্লান্তিকর!",
}

PRANK_IDS = list(PRANK_TITLES.keys())

COMMON_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; CPH2269 Build/SP1A.210812.016)",
    "Content-Type": "application/json; charset=utf-8",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
}


def generate_device_id():
    """Jokesphone ফরম্যাটে র‍্যান্ডম ডিভাইস আইডি তৈরি করে।"""
    return f"{secrets.token_hex(8)}@jokesphone"


def generate_unique_task_id():
    """১৫ অক্ষরের ইউনিক টাস্ক আইডেন্টিফায়ার তৈরি করে।"""
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(15))


def create_user(session, device_id):
    """সার্ভারে অস্থায়ী ইউজার রেজিস্ট্রেশন করে।"""
    url = "https://master.appha.es/lua/jokesphone/user/create.lua"
    payload = {
        "uv": "jokesphone",
        "dtype": "adr",
        "did": device_id,
        "route": "jo_1",
        "timezone": "Asia/Dhaka",
        "tags": {
            "mf": "OPPO",
            "mcc": 470,
            "mnc": 1,
            "r": "12",
            "v": "4.0.030826.346",
            "l": "en_BD",
            "c": "BD",
            "lnf": "en",
            "platform": "gplay",
            "aid": device_id[:16],
            "class": "Jokesphone_o",
        },
        "root": True,
        "imeiex": False,
        "version": "4.0.030826.346",
        "version_num": 346,
        "recommender": "",
    }

    try:
        res = session.post(
            url, json=payload, headers=COMMON_HEADERS, verify=False, timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            if data.get("res") == "OK" and "uid" in data:
                return {"success": True, "uid": data["uid"]}
    except Exception:
        pass
    return {"success": False}


def get_user_details(session, device_id):
    """ইউজার ডিটেইলস ও প্রাথমিক ক্রেডিট তথ্য আনে।"""
    url = "https://master.appha.es/usr?i=1"
    payload = {"uv": "jokesphone", "id": {"did": device_id, "dtype": "adr"}}

    try:
        res = session.post(
            url, json=payload, headers=COMMON_HEADERS, verify=False, timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            if "_id" in data.get("usr", {}):
                credit = data.get("usr", {}).get("extra", {}).get("credit", 0)
                return {"success": True, "credit": credit}
    except Exception:
        pass
    return {"success": False}


def check_credit(session, device_id):
    """অ্যাকাউন্টে পর্যাপ্ত ক্রেডিট আছে কি না যাচাই করে।"""
    url = "https://master.appha.es/lua/jokesphone/user/getCredit.lua"
    payload = {"did": device_id}
    headers = {
        "User-Agent": COMMON_HEADERS["User-Agent"],
        "Content-Type": COMMON_HEADERS["Content-Type"],
    }

    try:
        res = session.post(
            url, json=payload, headers=headers, verify=False, timeout=5
        )
        if res.status_code == 200:
            data = res.json()
            return data.get("credit", 0)
    except Exception:
        pass
    return 0


def send_prank_call(session, device_id, target_number, prank_id):
    """নির্দিষ্ট নম্বরে কলের টাস্ক পাঠায়।"""
    url = "https://master.appha.es/lua/jokesphone/user/create_task.lua"
    current_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    unique_id = generate_unique_task_id()

    # ডায়নামিক টাইটেল নির্ধারণ
    prank_title = PRANK_TITLES.get(prank_id, "প্র্যাঙ্ক কল")

    payload = {
        "real_f": current_time,
        "f": current_time,
        "uid": device_id,
        "dst": target_number,
        "dial": prank_id,
        "titulo": prank_title,
        "credit": 1,
        "smscredit": 0,
        "tz": "Asia/Dhaka",
        "c": "bd",
        "sc": "bd",
        "rec": False,
        "landline": False,
        "odid": device_id,
        "_id": unique_id,
    }

    try:
        res = session.post(
            url, json=payload, headers=COMMON_HEADERS, verify=False, timeout=10
        )
        data = res.json() if res.status_code == 200 else res.text
        if res.status_code == 200 and isinstance(data, dict):
            if data.get("res") == "OK":
                return {"success": True, "task_id": unique_id}
            return {"success": False, "response": data}
        return {"success": False, "response": data}
    except Exception as e:
        return {"success": False, "response": str(e)}


def fetch_prank_recordings(uid):
    """UID দিয়ে রেকর্ডিং সংক্রান্ত ডেটা নিয়ে আসে।"""
    url = "https://master.appha.es/lua/jokesphone/user/get_mis_bromas.lua"
    payload = {"uid": uid, "c": "bd", "sc": "bd", "lpd": True}

    headers = COMMON_HEADERS.copy()
    headers["Host"] = "master.appha.es"

    try:
        res = requests.post(
            url, json=payload, headers=headers, verify=False, timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                records = []
                for item in data:
                    prank_dial = item.get("dial")
                    # টাইটেল ম্যাচ করে না পাওয়া গেলে ডিফল্ট ডেকোরেটর ব্যবহার করবে
                    title = PRANK_TITLES.get(prank_dial, item.get("titulo", "প্র্যাঙ্ক কল"))
                    records.append(
                        {
                            "id": item.get("_id"),
                            "url": item.get("url"),
                            "prank_id": prank_dial,
                            "title": title,
                            "date": item.get("real_f") or item.get("fecha"),
                            "done": item.get("done", False),
                            "pic": item.get("pic"),
                        }
                    )
                return {"success": True, "records": records, "raw": data}
        return {
            "success": False,
            "message": f"Server error (Status Code: {res.status_code})",
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


# --- ENDPOINT 0: HOME DIRECT ROUTE ---
@app.route("/", methods=["GET"])
def home_endpoint():
    return (
        jsonify(
            {
                "success": False,
                "message": "Direct Access is not allowed. Please provide valid parameters.",
                "usage": {
                    "send_prank": "/prank?phone=01XXXXXXXXX&id=8810",
                    "fetch_record": "/record?uid=xxxx@jokesphone",
                },
                "allowed_prank_ids": PRANK_TITLES,
                "owner": OWNER,
            }
        ),
        400,
    )


# --- ENDPOINT 1: PRANK CALL ---
@app.route("/prank", methods=["GET"])
def prank_endpoint():
    allowed_params = {"phone", "id"}
    received_params = set(request.args.keys())

    if received_params != allowed_params:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Invalid request parameters. Exactly 'phone' and 'id' are required.",
                    "usage": "/prank?phone=01xxxxxxx&id=8810",
                    "owner": OWNER,
                }
            ),
            400,
        )

    target_number = request.args.get("phone", "").strip()
    user_prank = request.args.get("id", "").strip()

    # ফোন নম্বর ভ্যালিডেশন
    if not re.match(r"^(01|8801)[3-9]\d{8}$", target_number):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Invalid Bangladesh mobile number format.",
                    "owner": OWNER,
                }
            ),
            400,
        )

    # প্র্যাঙ্ক আইডি ভ্যালিডেশন
    if user_prank not in PRANK_IDS:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Invalid prank id. Allowed values: {', '.join(PRANK_IDS)}",
                    "owner": OWNER,
                }
            ),
            400,
        )

    max_retries = 3
    session = requests.Session()

    for attempt in range(1, max_retries + 1):
        device_id = generate_device_id()

        # Step 1: Create user
        create = create_user(session, device_id)
        if not create["success"]:
            time.sleep(1)
            continue

        # Step 2: Get user details
        details = get_user_details(session, device_id)
        if not details["success"]:
            time.sleep(1)
            continue

        # Step 3: Check credit
        credit = check_credit(session, device_id)
        if credit < 1:
            time.sleep(1)
            continue

        # Step 4: Send call
        result = send_prank_call(session, device_id, target_number, user_prank)
        if result["success"]:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Prank call sent successfully!",
                        "data": {
                            "target": target_number,
                            "prank_id": user_prank,
                            "title": PRANK_TITLES.get(user_prank),
                            "task_id": result["task_id"],
                            "uid": device_id,
                            "credit_used": 1,
                        },
                        "owner": OWNER,
                    }
                ),
                200,
            )
        else:
            response_str = str(result.get("response", ""))
            if "not enough credit" in response_str:
                continue

            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Failed to send prank call (attempt {attempt})",
                        "debug": result.get("response", "Unknown error"),
                        "owner": OWNER,
                    }
                ),
                500,
            )

    return (
        jsonify(
            {
                "success": False,
                "message": f"Failed after {max_retries} attempts.",
                "owner": OWNER,
            }
        ),
        500,
    )


# --- ENDPOINT 2: RECORD FETCH ---
@app.route("/record", methods=["GET"])
def record_endpoint():
    allowed_params = {"uid"}
    received_params = set(request.args.keys())

    if received_params != allowed_params:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Invalid request parameters. Exactly 'uid' is required.",
                    "usage": "/record?uid=xxxx@jokesphone",
                    "owner": OWNER,
                }
            ),
            400,
        )

    uid = request.args.get("uid", "").strip()

    if not uid.endswith("@jokesphone") or len(uid) < 15:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Invalid UID format. Must be like 'xxxx@jokesphone'",
                    "owner": OWNER,
                }
            ),
            400,
        )

    res = fetch_prank_recordings(uid)

    if res["success"]:
        records = res.get("records", [])
        return (
            jsonify(
                {
                    "success": True,
                    "message": (
                        "Recording fetched successfully."
                        if records
                        else "No recording found yet."
                    ),
                    "records": records,
                    "owner": OWNER,
                }
            ),
            200,
        )
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Failed to retrieve recording details.",
                    "error": res.get("message"),
                    "owner": OWNER,
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100, debug=True)
