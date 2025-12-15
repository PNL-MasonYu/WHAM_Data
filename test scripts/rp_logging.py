#!/usr/bin/python3
import time
import sys
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# --- CONFIGURATION ---
INFLUX_URL = "http://192.168.1.50:8086"  # Your InfluxDB IP
INFLUX_TOKEN = "my-token"
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "redpitaya_logs"
IIO_PATH = "/sys/bus/iio/devices/iio:device1"

def get_scale(pin_index):
    try:
        with open(f"{IIO_PATH}/in_voltage{9+pin_index}_scale", 'r') as f:
            return float(f.read().strip())
    except: return 1.0

def get_offset(pin_index):
    try:
        with open(f"{IIO_PATH}/in_voltage{9+pin_index}_offset", 'r') as f:
            return float(f.read().strip())
    except: return 0.0

def read_voltage(pin_index, scale, offset):
    try:
        with open(f"{IIO_PATH}/in_voltage{9+pin_index}_raw", 'r') as f:
            raw = float(f.read().strip())
        return ((raw + offset) * scale) / 1000.0
    except: return None

def main():
    # Retry loop for initial connection (in case DB is down when board boots)
    client = None
    while client is None:
        try:
            client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
            write_api = client.write_api(write_options=SYNCHRONOUS)
            print("Connected to InfluxDB.")
        except Exception:
            print("Waiting for InfluxDB...")
            time.sleep(10)

    scales = [get_scale(i) for i in range(4)]
    offsets = [get_offset(i) for i in range(4)]

    while True:
        try:
            voltages = []
            for i in range(4):
                voltages.append(read_voltage(i, scales[i], offsets[i]))

            if None not in voltages:
                point = Point("analog_readings") \
                    .tag("device", "STEMlab_125_14") \
                    .field("AIN0", voltages[0]) \
                    .field("AIN1", voltages[1]) \
                    .field("AIN2", voltages[2]) \
                    .field("AIN3", voltages[3])
                
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            
            time.sleep(1.0)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5) # Wait before retrying

if __name__ == "__main__":
    main()