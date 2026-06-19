import os
import json
import time
import sys
import argparse
import threading
from datetime import datetime
import paho.mqtt.client as mqtt

def load_env(filepath=".env"):
    """
    Parses a local .env file and populates os.environ
    """
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

load_env()

MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
BASE_TOPIC = os.getenv("BASE_TOPIC", "zigbee2mqtt")

REQ_TOPIC = f"{BASE_TOPIC}/bridge/request/networkmap"
RES_TOPIC = f"{BASE_TOPIC}/bridge/response/networkmap"

stop_spinner = threading.Event()

def spinner_animation():
    spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    sys.stdout.write("Requesting Zigbee network map... ")
    sys.stdout.flush()
    while not stop_spinner.is_set():
        sys.stdout.write(f"\rRequesting Zigbee network map... {spinners[i % len(spinners)]}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write("\r" + " " * 40 + "\r")
    sys.stdout.flush()

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(RES_TOPIC)
        payload = {"type": "raw"}
        client.publish(REQ_TOPIC, json.dumps(payload))
        
        spinner_thread = threading.Thread(target=spinner_animation)
        spinner_thread.daemon = True
        spinner_thread.start()
    else:
        print(f"Connection failed with code: {rc}")
        client.disconnect()

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        
        # Validar que sea el mensaje definitivo con los datos del mapa
        if payload.get("status") == "ok" and "data" in payload:
            stop_spinner.set()  # Detener animacion
            process_and_save_network_data(payload["data"])
            client.disconnect()  # Desconectarse SOLO ahora
            
    except Exception as e:
        print(f"Error parsing MQTT message: {e}")
        stop_spinner.set()
        client.disconnect()

def process_and_save_network_data(data):
    inner = data.get("value", data)
    nodes = {node["ieeeAddr"]: node.get("friendlyName", node["ieeeAddr"]) for node in inner.get("nodes", [])}
    links = inner.get("links", [])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_filename = f"zigbee_network_raw_{timestamp}.json"
    parsed_filename = f"zigbee_network_parsed_{timestamp}.txt"
    
    # 1. Guardar JSON original sin alteraciones
    with open(raw_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    # 2. Parsear relaciones y estructurar archivo legible
    with open(parsed_filename, "w", encoding="utf-8") as f:
        f.write(f"Zigbee Network Map Topology - {datetime.now().isoformat()}\n")
        f.write("-" * 75 + "\n")
        f.write(f"{'Source':<30} -> {'Target':<30} | {'LQI':<5}\n")
        f.write("-" * 75 + "\n")
        
        console_output = []
        console_output.append(f"\n{'Source':<30} -> {'Target':<30} | {'LQI':<5}")
        console_output.append("-" * 75)
        
        for link in links:
            source_addr = link["source"]["ieeeAddr"]
            target_addr = link["target"]["ieeeAddr"]
            lqi = link["lqi"]
            
            source_name = nodes.get(source_addr, source_addr)
            target_name = nodes.get(target_addr, target_addr)
            
            line = f"{source_name:<30} -> {target_name:<30} | {lqi:<5}"
            if lqi < 50:
                line_with_flag = f"{line} (LOW LQI)"
            else:
                line_with_flag = line
                
            f.write(line_with_flag + "\n")
            console_output.append(line_with_flag)
            
    # Mostrar por pantalla
    for c_line in console_output:
        print(c_line)
        
    print(f"\n[+] Raw data saved to: {raw_filename}")
    print(f"[+] Parsed data saved to: {parsed_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zigbee network map tool")
    parser.add_argument("--file", "-f", metavar="JSON_FILE", help="Parse an existing raw JSON dump instead of querying MQTT")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        process_and_save_network_data(data)
        sys.exit(0)

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    if MQTT_USER and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        stop_spinner.set()
        print(f"Failed to connect to broker: {e}")