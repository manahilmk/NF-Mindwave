import socket
import json
import time
import pandas as pd

IP = '127.0.0.1'
PORT = 13854

def connect_to_mindwave():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((IP, PORT))
    config = json.dumps({"enableRawOutput": False, "format": "Json"})
    sock.send(config.encode('utf-8'))
    return sock

# === User Input ===
name = input("Enter user name: ")
duration = int(input("Enter the Baseline Recording Duration (in seconds): "))
baseline_state = input("Is this a Pre or Post baseline recording? (Pre/Post): ").strip()

filename = f"User Data/{baseline_state}_Baseline_{name}.csv"
start_time = time.time()

sock = connect_to_mindwave()
data_list = []

print(f"[INFO] Collecting {baseline_state}-baseline data for {duration} seconds...")

while time.time() - start_time < duration:
    try:
        response = sock.recv(4096).decode('utf-8')
        packets = response.strip().split('\r')
        for packet in packets:
            if not packet:
                continue
            data = json.loads(packet)
            if "eegPower" in data and "eSense" in data:
                eeg = data["eegPower"]
                attention = data["eSense"]["attention"]
                meditation = data["eSense"]["meditation"]
                timestamp = time.time()
                eeg.update({
                    "timestamp": timestamp,
                    "attention": attention,
                    "meditation": meditation
                })
                data_list.append(eeg)
    except Exception as e:
        print(f"[ERROR] {e}")
        continue

df = pd.DataFrame(data_list)
df.to_csv(filename, index=False)
sock.close()
print(f"[SUCCESS] Baseline data saved to: {filename}")
