from flask import Flask, request, jsonify
import requests
import json
import time
import random
import string
from urllib.parse import urlparse

app = Flask(__name__)


FIXED_HEADERS = {
    'User-Agent': "okhttp/5.1.0",
    'Accept-Encoding': "gzip",
    'authorization': "eyJzdWIiwsdeOiIyMzQyZmczNHJ0MzR0weMzQiLCJuYW1lIjorwiSm9objJif4md3kbnG",
    'sign': "68d6165b72a7f2d8d17b0dc6fe9691abdf77c583",
    'pt': "",
    'v': "72"
}

def generate_device_id():
    """Generate random 15-char device ID only"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))

@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "endpoint": "/generate?prompt=your_text",
        "device_rotation": "device_id_only"
    })

@app.route("/generate")
def generate():
    prompt = request.args.get("prompt")

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    
    # 🔄 ONLY DEVICE ID CHANGES - Everything else FIXED
    device_id = generate_device_id()
    
    # FIXED headers + random device_id only
    headers_base = FIXED_HEADERS.copy()
    headers_base['deviceid'] = device_id
    
    print(f"🔄 Device ID: {device_id}")
    
    # STEP 1: NSFW CHECK
    nsfw_url = "https://text2video.aritek.app/nsfw"
    nsfw_payload = {
        'prompt': prompt,
        'ctry_target': 'others',
        'versionCode': '72',
        'deviceID': device_id,
        'isPremium': '0'
    }

    try:
        nsfw_res = requests.post(nsfw_url, data=nsfw_payload, headers=headers_base)
        nsfw_data = nsfw_res.json()

        if nsfw_data.get('code') != 0 or not nsfw_data.get('success'):
            return jsonify({"error": "NSFW check failed"}), 400

        if nsfw_data['data'][0].get('nsfw'):
            return jsonify({"error": "Prompt flagged as NSFW"}), 400

    except Exception as e:
        return jsonify({"error": f"NSFW error: {str(e)}"}), 500

    # STEP 2: GENERATE KEY
    txt2video_url = "https://text2video.aritek.app/txt2videov3"
    payload = {
        "ai_sound": 1,
        "aspect_ratio": "auto",
        "ctry_target": "others",
        "deviceID": device_id,
        "isPremium": 0,
        "prompt": prompt,
        "used": [],
        "versionCode": 72
    }

    headers_json = headers_base.copy()
    headers_json['content-type'] = "application/json; charset=utf-8"

    try:
        res = requests.post(txt2video_url, data=json.dumps(payload), headers=headers_json)
        data = res.json()

        if data.get('code') != 0:
            return jsonify({"error": "Video generation failed"}), 400

        video_key = data.get("key")
        if not video_key:
            return jsonify({"error": "No video key"}), 400

    except Exception as e:
        return jsonify({"error": f"Key error: {str(e)}"}), 500

    # STEP 3: FETCH VIDEO
    video_url_api = "https://text2video.aritek.app/video"
    video_payload = {"keys": [video_key]}

    for _ in range(10):
        try:
            res = requests.post(video_url_api, data=json.dumps(video_payload), headers=headers_json)
            data = res.json()

            if data.get("code") == 0 and data.get("datas"):
                video_info = data["datas"][0]
                url = video_info.get("url")

                if url:
                    filename = urlparse(url).path.split("/")[-1]
                    return jsonify({
                        "status": "success",
                        "url": url,
                        "filename": filename,
                        "safe": video_info.get("safe", "unknown"),
                        "device_id_used": device_id
                    })

            time.sleep(3)

        except Exception as e:
            return jsonify({"error": f"Fetch error: {str(e)}"}), 500

    return jsonify({"error": "Timeout"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
