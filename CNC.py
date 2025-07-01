import random
import json
import time
from datetime import datetime
import ssl
import paho.mqtt.client as mqtt
import subprocess

#retrieve raw cert
raw_cert = subprocess.check_output(["terraform", "output", "-json", "cert_pem"])
cert_string = json.loads(raw_cert)

with open("cert.pem", "w") as f:
    f.write(cert_string)
#retrieve iot core private key
raw_key = subprocess.check_output(["terraform", "output", "-json", "private_key"])
key_string = json.loads(raw_key)

with open("pem.key", "w") as f:
    f.write(key_string)
#AWS ROOT CA

cert_file="cert.pem"
key_file="pem.key"
aws_ca_file="AWSROOTCA.pem"

client = mqtt.Client(protocol=mqtt.MQTTv311)

#needs pem_cert, AWS Root CA (publicly available ), private_key
client.tls_set(ca_certs=aws_ca_file,
    certfile=cert_file,
    keyfile=key_file,
    tls_version=ssl.PROTOCOL_TLSv1_2) 

iot_endpoint = "a1w49aeulo3niq-ats.iot.us-east-1.amazonaws.com"
port = 8883
topic = "cnc/machine/data"
client.connect(iot_endpoint, port)

client.loop_start()


MACHINE_IDS = ["CNC-001", "CNC-002", "CNC-003", "CNC-004", "CNC-005"]
PART_NUMBERS = ["AXLE-9876", "GEAR-1234", "BRK-4567", "DRIVE-3321"]
OPERATIONS = ["DRILLING", "MILLING", "CUTTING", "GRINDING"]

def generate_fake_data():

    return {
        "timestamp": datetime.now().isoformat() + "Z",
        "machine_id": random.choice(MACHINE_IDS),
        "part_number": random.choice(PART_NUMBERS),
        "operation": random.choice(OPERATIONS),
        "rpm": random.randint(800, 3000),
        "temperature_c": round(random.uniform(30.0, 90.0), 2),
        "vibration_mm_s": round(random.uniform(0.1, 5.0), 2),
        "status": random.choices(["OK", "WARN", "FAIL"], weights=[85, 10, 5])[0]
    }

while True:
    data = generate_fake_data()
    payload= json.dumps(data)
    print(payload)
    client.publish(topic, payload)

    time.sleep(60)  # generates a new reading every second