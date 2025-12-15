import socket
import time

# --- CONFIGURATION ---
RP_IP = "192.168.130.228"
RP_PORT = 5000

def set_analog_output(channel, voltage):
    """
    Channel: 0-3
    Voltage: 0.0 - 1.8 V
    """
    try:
        # Create a transient connection (connect, send, close)
        # This prevents locking the port from your High Priority script
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((RP_IP, RP_PORT))
        
        # SCPI Command: ANALOG:PIN AOUT0,1.5
        cmd = f"ANALOG:PIN AOUT{channel},{voltage}\r\n"
        s.send(cmd.encode())
        
        s.close()
        print(f"Set AO{channel} to {voltage}V")
        
    except Exception as e:
        print(f"Failed to set AO: {e}")

def main():
    print("External AO Controller running...")
    
    # Example: Toggle Output 0 every 5 seconds
    while True:
        set_analog_output(1, 1.0) # Set AO0 to 1V
        time.sleep(5)
        set_analog_output(1, 0.5) # Set AO0 to 0.5V
        time.sleep(5)

if __name__ == "__main__":
    main()