from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import requests
import json
import time
import threading
import uuid
import os
app = Flask(__name__)
app.secret_key = "any_secret_password" 

# --- CONFIGURAxTION ---
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

queue_data = {
    "queue_id": uuid.uuid4().hex[:8].upper(),  # Unique ID for this queue instance
    "current_serving": 1,
    "last_token_issued": 1,
    "last_click_time": None,
    "service_history": [300],
    "user_satisfaction_scores": {},
    "users": {},
    "eta_offsets": {},
    "discounts": {},
    "game_scores": {}          # {"2": {"score": 45, "playing": True}}
}

# --- AI LOGIC ---
def get_goodbye_message(name):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a warm, supportive queue assistant. Be encouraging and helpful. Speak JSON."},
            {"role": "user", "content": f"The customer named {name} has reached the counter after waiting. Give them a warm, encouraging message thanking them for their patience and wishing them well. Format as JSON: {{\"text\": \"your message\"}}"}
        ],
        "response_format": {"type": "json_object"}
    }
    try:
        r = requests.post(url, headers=headers, json=payload)
        return r.json()['choices'][0]['message']['content']
    except:
        return json.dumps({"text": f"Thank you for your patience, {name}! You're all set. Have a great experience with us!"})

def get_groq_response(user_choice, queue_pos, token):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    tone = "encouraging and uplifting" if queue_pos < 3 else "empathetic and supportive"
    
    prompt = f"""
    Queue Position: {queue_pos} people ahead. User chose: '{user_choice}'. 
    Your Tone: Be {tone} and genuinely helpful.
    Task: Respond with genuine support and helpful suggestions. Rate the user's satisfaction from 1 to 10 based on how well you've supported them.
    Format ONLY as JSON: 
    {{
        "text": "your supportive response", 
        "options": ["opt1", "opt2", "opt3"],
        "satisfaction_score": 8
    }}
    """
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": "You are a warm, helpful, and supportive queue assistant. Your goal is to make customers feel valued and comfortable while they wait. Speak JSON. Be encouraging and genuinely helpful in every response."},
                     {"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        res_text = r.json()['choices'][0]['message']['content']
        data = json.loads(res_text)
        
        # Save this specific user's satisfaction score
        queue_data["user_satisfaction_scores"][str(token)] = data.get("satisfaction_score", 8)
        return res_text
    except Exception as e:
        print(f"AI Error: {e}")
        return json.dumps({"text": "We're here to help! Your patience means a lot to us. Is there anything we can assist you with while you wait?", "options": ["Play a game", "Learn about services", "Chat"], "satisfaction_score": 7})

# --- PAGE ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

# --- API ENDPOINTS ---
@app.route('/api/join', methods=['POST'])
def join_queue():
    name = request.json.get('name', 'Anonymous')
    queue_data["last_token_issued"] += 1
    new_token = queue_data["last_token_issued"]
    queue_data["users"][str(new_token)] = name
    # Start the timer on first customer joining
    if queue_data["last_click_time"] is None:
        queue_data["last_click_time"] = time.time()
    return jsonify({"token": new_token, "name": name, "queue_id": queue_data["queue_id"]})

@app.route('/api/status')
def status():
    user_token = int(request.args.get('token', 0))
    ahead = max(0, user_token - queue_data["current_serving"])
    actual_avg_seconds = sum(queue_data["service_history"]) / len(queue_data["service_history"])
    base_eta = round((ahead * actual_avg_seconds) / 60, 1)
    offset = queue_data["eta_offsets"].get(str(user_token), 0)
    dynamic_eta = round(max(0, base_eta + offset), 1)

    current_satisfaction = queue_data["user_satisfaction_scores"].get(str(queue_data["current_serving"]), 8)
    user_satisfaction = queue_data["user_satisfaction_scores"].get(str(user_token), 8)
    has_queue = queue_data["last_token_issued"] > queue_data["current_serving"]
    elapsed = round(time.time() - queue_data["last_click_time"], 1) if (queue_data["last_click_time"] and has_queue) else None

    return jsonify({
        "current": queue_data["current_serving"],
        "last_token": queue_data["last_token_issued"],
        "avg_seconds": round(actual_avg_seconds, 1),
        "eta": dynamic_eta,
        "satisfaction": user_satisfaction,
        "current_satisfaction": current_satisfaction,
        "discount": queue_data["discounts"].get(str(user_token), None),
        "elapsed_seconds": elapsed,
        "serving_token": queue_data["current_serving"],
        "queue_id": queue_data["queue_id"]
    })

@app.route('/api/queue_list')
def queue_list():
    if not session.get('admin'):
        return "Unauthorized", 403
    actual_avg_seconds = sum(queue_data["service_history"]) / len(queue_data["service_history"])
    members = []
    for token_str, name in queue_data["users"].items():
        t = int(token_str)
        if t < queue_data["current_serving"]:
            continue  # already served
        ahead = max(0, t - queue_data["current_serving"])
        base_eta = round((ahead * actual_avg_seconds) / 60, 1)
        offset = queue_data["eta_offsets"].get(token_str, 0)
        eta = round(max(0, base_eta + offset), 1)
        members.append({
            "token": t,
            "name": name,
            "satisfaction": queue_data["user_satisfaction_scores"].get(token_str, 8),
            "eta": eta,
            "is_current": t == queue_data["current_serving"],
            "game": queue_data["game_scores"].get(token_str, None),
            "queue_id": queue_data["queue_id"]
        })
    members.sort(key=lambda x: x["token"])
    return jsonify({"members": members, "queue_id": queue_data["queue_id"]})

@app.route('/api/adjust_eta', methods=['POST'])
def adjust_eta():
    if not session.get('admin'):
        return "Unauthorized", 403
    token = str(request.json.get('token'))
    delta = float(request.json.get('delta', 0))
    current = queue_data["eta_offsets"].get(token, 0)
    queue_data["eta_offsets"][token] = current + delta
    return jsonify({"success": True})

@app.route('/api/game_score', methods=['POST'])
def game_score():
    token = str(request.json.get('token'))
    score = int(request.json.get('score', 0))
    playing = bool(request.json.get('playing', False))
    queue_data["game_scores"][token] = {"score": score, "playing": playing}
    # Auto-discount at score >= 200 (hard to reach, ~40 apples)
    DISCOUNT_THRESHOLD = 200
    if score >= DISCOUNT_THRESHOLD and token not in queue_data["discounts"]:
        queue_data["discounts"][token] = 10  # reward: 10% off
    return jsonify({"success": True, "discount_threshold": DISCOUNT_THRESHOLD})

@app.route('/api/adjust_avg', methods=['POST'])
def adjust_avg():
    if not session.get('admin'):
        return "Unauthorized", 403
    delta_seconds = float(request.json.get('delta', 0))  # +30 or -30
    # Inject a synthetic history entry to nudge the rolling average
    current_avg = sum(queue_data["service_history"]) / len(queue_data["service_history"])
    new_val = max(30, current_avg + delta_seconds)
    queue_data["service_history"].append(new_val)
    if len(queue_data["service_history"]) > 5:
        queue_data["service_history"].pop(0)
    return jsonify({"avg_seconds": round(sum(queue_data["service_history"]) / len(queue_data["service_history"]), 1)})

@app.route('/api/apply_discount', methods=['POST'])
def apply_discount():
    if not session.get('admin'):
        return "Unauthorized", 403
    token = str(request.json.get('token'))
    percent = int(request.json.get('percent'))
    queue_data["discounts"][token] = percent
    return jsonify({"success": True})

@app.route('/api/goodbye', methods=['POST'])
def goodbye():
    token = str(request.json.get('token'))
    name = queue_data["users"].get(token, "friend")
    return get_goodbye_message(name)

@app.route('/api/interact', methods=['POST'])
def interact():
    data = request.json
    choice = data.get('choice')
    token = str(data.get('token'))
    pos = int(token) - queue_data["current_serving"]
    return get_groq_response(choice, pos, token)

@app.route('/api/next', methods=['POST'])
def next_queue():
    if not session.get('admin'):
        return "Unauthorized", 403
    
    now = time.time()
    if queue_data["last_click_time"]:
        duration = now - queue_data["last_click_time"]
        queue_data["service_history"].append(duration)
        if len(queue_data["service_history"]) > 5:
            queue_data["service_history"].pop(0)
    
    queue_data["last_click_time"] = now
    queue_data["current_serving"] += 1
    return jsonify({"success": True})

# --- AUTO-ADVANCE BACKGROUND THREAD ---
def auto_advance_worker():
    while True:
        time.sleep(10)  # check every 10 seconds
        try:
            current = queue_data["current_serving"]
            last = queue_data["last_token_issued"]
            if current > last:
                continue  # no one waiting

            actual_avg_seconds = sum(queue_data["service_history"]) / len(queue_data["service_history"])
            offset = queue_data["eta_offsets"].get(str(current), 0)
            # ETA for the person AT the counter is 0 by definition;
            # we track how long they've been sitting there instead
            if queue_data["last_click_time"] is None:
                continue
            time_at_counter = time.time() - queue_data["last_click_time"]
            allowed_seconds = actual_avg_seconds + (offset * 60)
            if time_at_counter >= allowed_seconds:
                # Auto-advance
                now = time.time()
                duration = now - queue_data["last_click_time"]
                queue_data["service_history"].append(duration)
                if len(queue_data["service_history"]) > 5:
                    queue_data["service_history"].pop(0)
                queue_data["last_click_time"] = now
                queue_data["current_serving"] += 1
                print(f"[Auto-Advance] Token {current} timed out. Now serving {queue_data['current_serving']}")
        except Exception as e:
            print(f"[Auto-Advance Error] {e}")

auto_thread = threading.Thread(target=auto_advance_worker, daemon=True)
auto_thread.start()

# --- START SERVER (Always at the very bottom) ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=False)