import socket
import json
import time
import pandas as pd
import numpy as np
#import vlc
import os
import sys
import ctypes

# === Force Load VLC DLLs ===
lib_path = os.path.abspath(os.path.dirname(__file__))  # current folder
os.environ['PATH'] = lib_path + os.pathsep + os.environ['PATH']

try:
    ctypes.CDLL(os.path.join(lib_path, "libvlc.dll"))
    print("[INFO] libvlc.dll loaded successfully.")
except Exception as e:
    print(f"[ERROR] Could not manually load libvlc.dll: {e}")
    exit()

import vlc


IP = '127.0.0.1'
PORT = 13854

def connect_to_mindwave():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((IP, PORT))
    config = json.dumps({"enableRawOutput": False, "format": "Json"})
    sock.send(config.encode('utf-8'))
    return sock

# === User Input ===
name = input("Enter user name (same as for baseline): ")
session_duration = int(input("Enter neurofeedback session duration (in seconds): "))
threshold_percent = float(input("Enter beta threshold increase percentage (e.g., 10 for +10%): "))
nf_day = input("Enter neurofeedback day number: ")
session_no = input("Enter session number: ")

baseline_file = f"User Data/Pre_Baseline_{name}.csv"
nf_file = f"User Data/NF{nf_day}_Ses{session_no}_{name}.csv"
nf_details_file = f"User Data/NF{nf_day}_Ses{session_no}_NF_details_{name}.csv"

# === Load Baseline ===
try:
    baseline_df = pd.read_csv(baseline_file)
    baseline_beta = baseline_df[["lowBeta", "highBeta"]].mean(axis=1)
    baseline_mean = baseline_beta.mean()
    beta_threshold = baseline_mean + (baseline_mean * threshold_percent / 100)
    print(f"[INFO] Baseline beta mean: {baseline_mean:.2f}")
    print(f"[INFO] Neurofeedback threshold (+" + str(threshold_percent) + f"%): {beta_threshold:.2f}")
except Exception as e:
    print(f"[ERROR] Could not load baseline file: {e}")
    exit()

# === VLC Setup ===
media = vlc.MediaPlayer("NF Video.mp4")
media_state = 0  # 0 = paused, 1 = playing

print("[INFO] Starting VLC player...")
media.play()
time.sleep(2)
media.pause()
print("[INFO] VLC initialized and paused. Starting session in 5 seconds.")
time.sleep(5)

# === Real-time NFB ===
sock = connect_to_mindwave()
start_time = time.time()

raw_data = []
nf_scores = []
nf_beta_vals = []

print("[INFO] Beginning neurofeedback session...")

try:
    while time.time() - start_time < session_duration:
        response = sock.recv(4096).decode('utf-8')
        packets = response.strip().split('\r')
        for packet in packets:
            if not packet:
                continue
            try:
                data = json.loads(packet)
            except:
                continue
            if "eegPower" in data and "eSense" in data:
                eeg = data["eegPower"]
                attention = data["eSense"]["attention"]
                meditation = data["eSense"]["meditation"]
                timestamp = time.time()

                low_beta = eeg.get("lowBeta", 0)
                high_beta = eeg.get("highBeta", 0)
                beta_mean = np.mean([low_beta, high_beta])
                nf_beta_vals.append(beta_mean)
                score = 1 if beta_mean > beta_threshold else 0
                nf_scores.append(score)

                raw_data.append({
                    "timestamp": timestamp,
                    "attention": attention,
                    "meditation": meditation,
                    **eeg
                })

                # === Feedback + Media Control ===
                if beta_mean > beta_threshold:
                    print("[FEEDBACK] Threshold exceeded: neurofeedback target achieved.")
                    if media_state == 0:
                        media.play()
                        media_state = 1
                else:
                    print("[FEEDBACK] Below threshold: continue focusing to maintain elevated beta activity.")
                    if media_state == 1:
                        media.pause()
                        media_state = 0

except KeyboardInterrupt:
    print("[INFO] Interrupted by user. Stopping session.")

finally:
    sock.close()
    media.stop()
    print("[INFO] Neurofeedback session complete. Saving data...")

    df_main = pd.DataFrame(raw_data)
    df_main.to_csv(nf_file, index=False)

    df_feedback = pd.DataFrame({
        "NFB Mean Beta": nf_beta_vals,
        "NFB Score": nf_scores
    })
    df_feedback.to_csv(nf_details_file, index=False)

    print(f"[SUCCESS] Data saved:\n→ {nf_file}\n→ {nf_details_file}")

