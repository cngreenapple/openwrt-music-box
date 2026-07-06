from flask import request, jsonify
import threading
import random
from . import controls_bp
from app import mpv_send, owmb_state, state_lock, af_state, update_mpv_filters, EQ_PRESETS, generate_fireq_cmd, trigger_play, play_next_in_queue

@controls_bp.route('/control/<action>')
def control(action):
    if action == "pause": mpv_send(["cycle", "pause"])
    elif action == "stop":
        mpv_send(["stop"])
        with state_lock:
            owmb_state["status"] = "stopped"
            owmb_state["queue"] = []
            owmb_state["current_index"] = -1
            owmb_state["manual_stop"] = True
    elif action == "next": play_next_in_queue()
    elif action == "prev":
        with state_lock:
            if owmb_state["current_index"] > 0:
                owmb_state["current_index"] -= 1
                prev_song = owmb_state["queue"][owmb_state["current_index"]]
                trigger_play(prev_song['link'])
            else: mpv_send(["seek", 0, "absolute"])
    elif action == "shuffle":
        with state_lock:
            if len(owmb_state["queue"]) > 1:
                current_song = owmb_state["queue"][owmb_state["current_index"]]
                random.shuffle(owmb_state["queue"])
                for idx, song in enumerate(owmb_state["queue"]):
                    if song['link'] == current_song['link']:
                        owmb_state["current_index"] = idx; break
        return jsonify({"status": "shuffled"})
    elif action == "volume":
        try: 
            v = int(request.args.get('val', 30))
            mpv_send(["set_property", "volume", v])
            with state_lock: owmb_state["volume"] = v
        except: pass
    elif action == "seek":
        try: mpv_send(["seek", float(request.args.get('val', 0)), "absolute-percent"])
        except: pass
    elif action == "output":
        from app import get_audio_device_string, TOGGLE_SCRIPT, MODE_FILE
        import os, subprocess
        target = request.args.get('mode') or 'jack'
        dev_string = get_audio_device_string(target)
        mpv_send(["set_property", "audio-device", dev_string])
        if os.path.exists(TOGGLE_SCRIPT): subprocess.run(["/bin/bash", TOGGLE_SCRIPT, dev_string], check=False)
        else:
            with open(MODE_FILE, "w") as f: f.write(dev_string)
        with state_lock: owmb_state["status_output"] = target
        return jsonify({"status": "ok", "active": target})
    return jsonify({"status": "ok"})

@controls_bp.route('/control/jump')
def jump_to_index():
    try:
        idx = int(request.args.get('index', -1))
        with state_lock:
            if 0 <= idx < len(owmb_state["queue"]):
                owmb_state["current_index"] = idx
                song = owmb_state["queue"][idx]
                owmb_state["error_count"] = 0
                threading.Thread(target=trigger_play, args=(song['link'],)).start()
                return jsonify({"status": "ok", "title": song['title']})
    except: pass
    return jsonify({"error": "invalid index"})

@controls_bp.route('/control/eq')
def set_eq():
    p = request.args
    gains = {}
    for i in range(1, 11): gains[f'f{i}'] = p.get(f'f{i}', 0)
    cmd_str = generate_fireq_cmd(gains)
    af_state["eq"] = f"lavfi=[{cmd_str}]"
    update_mpv_filters()
    with state_lock: owmb_state["current_eq_cmd"] = af_state["eq"]
    return jsonify({"status": "ok"})

@controls_bp.route('/control/preset')
def set_preset():
    n = request.args.get('name')
    if n in EQ_PRESETS:
        preset = EQ_PRESETS[n]
        cmd_str = generate_fireq_cmd(preset)
        af_state["eq"] = f"lavfi=[{cmd_str}]"
        update_mpv_filters()
        with state_lock: 
            owmb_state["active_preset"] = n
            owmb_state["current_eq_cmd"] = af_state["eq"]
        return jsonify(preset)
    return jsonify({"error": "not found"}), 404

@controls_bp.route('/control/balance')
def set_balance():
    try:
        l_vol = float(request.args.get('l', 1.0))
        r_vol = float(request.args.get('r', 1.0))
    except:
        l_vol = 1.0; r_vol = 1.0

    pan_cmd = f"pan=stereo|c0={l_vol:.2f}*c0|c1={r_vol:.2f}*c1"
    
    if l_vol >= 0.99 and r_vol >= 0.99: af_state["balance"] = ""
    else: af_state["balance"] = f"lavfi=[{pan_cmd}]"
    
    update_mpv_filters()
    return jsonify({"status": "ok", "L": l_vol, "R": r_vol})

@controls_bp.route('/control/bitperfect')
def toggle_bitperfect():
    import os
    from app import BP_MODE_FILE
    current = "0"
    if os.path.exists(BP_MODE_FILE):
        try:
            with open(BP_MODE_FILE, 'r') as f: current = f.read().strip()
        except: pass
    
    new_state = "1" if current == "0" else "0"
    with open(BP_MODE_FILE, 'w') as f: f.write(new_state)
    update_mpv_filters()
    
    if new_state == "0":
        mpv_send(["set_property", "volume", 30])
        with state_lock: owmb_state["volume"] = 30

    return jsonify({"status": "ok", "bitperfect": new_state == "1"})

@controls_bp.route('/get_bitperfect')
def get_bitperfect():
    import os
    from app import BP_MODE_FILE
    active = False
    if os.path.exists(BP_MODE_FILE):
        with open(BP_MODE_FILE, 'r') as f: active = f.read().strip() == "1"
    return jsonify({"active": active})

@controls_bp.route('/control/crossfeed')
def toggle_crossfeed():
    state = request.args.get('state', 'on')
    af_state["crossfeed"] = "lavfi=[bs2b=profile=cmoy]" if state == 'on' else ""
    update_mpv_filters()
    return jsonify({"status": "ok", "crossfeed": state == 'on'})

@controls_bp.route('/get_crossfeed')
def get_crossfeed():
    return jsonify({"active": len(af_state["crossfeed"]) > 0})