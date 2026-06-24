import sys
import socket
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QDoubleSpinBox, 
                             QPushButton, QFrame, QGridLayout)
from PyQt5.QtCore import QTimer, Qt
from influxdb_client import InfluxDBClient

# --- CONFIGURATION ---
RPI_IP = "192.168.130.203"
UDP_PORT = 5005

INFLUX_URL = "http://andrew.psl.wisc.edu:8086"
INFLUX_ORG = "WHAM"
INFLUX_TOKEN = "_h8EHu5V5jF_u9dHjqHPH4eL1uDYOY25auKPTa9Z9e0R_jJMHhvqbhlcxQfeq9QG2KsJnlvurS1IsSVym5D7UA=="
INFLUX_BUCKET = "fueling"

GAS_OPTIONS = ['H2', 'D2', 'He', 'Ar']
KPA_TO_PSI = 0.145038
PSI_TO_KPA = 6.894757

class ChannelControl(QFrame):
    def __init__(self, ch_num):
        super().__init__()
        self.ch_num = ch_num
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        
        layout = QGridLayout()
        self.setLayout(layout)

        # Title & Status Banner
        title = QLabel(f"<b>Line {ch_num} Control</b>")
        layout.addWidget(title, 0, 0)
        
        self.lbl_status = QLabel("IDLE")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("background-color: #AAAAAA; color: black; font-weight: bold; padding: 4px; border-radius: 4px;")
        layout.addWidget(self.lbl_status, 0, 1, 1, 3)

        # Controls
        layout.addWidget(QLabel("Gas:"), 1, 0)
        self.gas_combo = QComboBox()
        self.gas_combo.addItems(GAS_OPTIONS)
        layout.addWidget(self.gas_combo, 1, 1)

        layout.addWidget(QLabel("Setpoint (PSI):"), 2, 0)
        self.setpoint_box = QDoubleSpinBox()
        self.setpoint_box.setRange(0.0, 150.0) # Approx 1000 kPa limit
        self.setpoint_box.setDecimals(2)
        layout.addWidget(self.setpoint_box, 2, 1)

        # Send Button
        self.send_btn = QPushButton("Send Setpoint")
        self.send_btn.clicked.connect(self.send_udp_command)
        layout.addWidget(self.send_btn, 3, 0, 1, 2)
        
        # Override / Purge Button
        self.override_btn = QPushButton("Force OPEN (Purge)")
        self.override_btn.setCheckable(True)
        self.override_btn.setStyleSheet(
            "QPushButton:checked { background-color: red; color: white; font-weight: bold; }"
        )
        self.override_btn.clicked.connect(self.send_udp_command)
        layout.addWidget(self.override_btn, 4, 0, 1, 2)

        # Telemetry Display
        layout.addWidget(QLabel("<b>Live Telemetry:</b>"), 1, 3)
        
        self.lbl_pressure = QLabel("Pressure: -- PSI")
        self.lbl_pressure.setStyleSheet("color: blue; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.lbl_pressure, 2, 3)

        self.lbl_flow = QLabel("Cmd Flow: -- sccm")
        layout.addWidget(self.lbl_flow, 3, 3)

        self.lbl_valve = QLabel("Valve State: Unknown")
        layout.addWidget(self.lbl_valve, 4, 3)

    def send_udp_command(self):
        gas = self.gas_combo.currentText()
        setpoint_psi = self.setpoint_box.value()
        is_override = self.override_btn.isChecked()
        
        # Convert PSI back to kPa for the backend
        setpoint_kpa = setpoint_psi * PSI_TO_KPA
        
        payload = json.dumps({
            "line": self.ch_num,
            "gas": gas,
            "setpoint": setpoint_kpa,
            "override": is_override
        })
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(payload.encode('utf-8'), (RPI_IP, UDP_PORT))
            print(f"Sent to Pi: {payload}")
        except Exception as e:
            print(f"Failed to send UDP packet: {e}")

    def update_telemetry(self, pressure_kpa, target_kpa, flow_sccm, valve_state):
        press_psi = pressure_kpa * KPA_TO_PSI
        self.lbl_pressure.setText(f"Pressure: {press_psi:.2f} PSI")
        self.lbl_flow.setText(f"Cmd Flow: {flow_sccm:.1f} sccm")
        
        # Update Valve String
        if valve_state == 2:
            self.lbl_valve.setText("Valve State: FORCED OPEN")
            self.lbl_valve.setStyleSheet("color: red; font-weight: bold;")
            self.lbl_status.setText("PURGING LINE")
            self.lbl_status.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 4px; border-radius: 4px;")
        elif valve_state == 1:
            self.lbl_valve.setText("Valve State: PID ACTIVE")
            self.lbl_valve.setStyleSheet("color: green; font-weight: bold;")
            
            # Actionable logic for the operator
            if pressure_kpa >= (target_kpa - 0.5): 
                self.lbl_status.setText("TARGET REACHED - CLOSE SUPPLY")
                self.lbl_status.setStyleSheet("background-color: #00FF00; color: black; font-weight: bold; padding: 4px; border-radius: 4px;")
            else:
                self.lbl_status.setText("FILLING...")
                self.lbl_status.setStyleSheet("background-color: #FFFF00; color: black; font-weight: bold; padding: 4px; border-radius: 4px;")
                
        else:
            self.lbl_valve.setText("Valve State: CLOSED")
            self.lbl_valve.setStyleSheet("color: gray;")
            self.lbl_status.setText("IDLE")
            self.lbl_status.setStyleSheet("background-color: #AAAAAA; color: black; font-weight: bold; padding: 4px; border-radius: 4px;")

class WHAMDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WHAM Fueling Control Dashboard")
        self.resize(700, 650)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header = QLabel("<h3>WHAM Mass Flow Controller System</h3>")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        self.channels = {}
        for i in range(1, 5):
            ch_widget = ChannelControl(i)
            self.channels[i] = ch_widget
            main_layout.addWidget(ch_widget)

        self.influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        self.query_api = self.influx_client.query_api()

        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_influxdb)
        self.timer.start(1000)

    def poll_influxdb(self):
        flux_query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -5s)
          |> filter(fn: (r) => r["_measurement"] == "mfc")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> group(columns: ["channel"])
          |> last(column: "_time")
        '''
        
        try:
            tables = self.query_api.query(flux_query)
            for table in tables:
                for record in table.records:
                    ch_tag = record.values.get("channel")
                    if not ch_tag: continue
                    ch_num = int(ch_tag.replace("ch", ""))
                    
                    if ch_num in self.channels:
                        press_kpa = record.values.get("pressure_kpa", 0.0)
                        target_kpa = record.values.get("commanded_pressure_kpa", 0.0)
                        flow = record.values.get("commanded_flow_sccm", 0.0)
                        valve = record.values.get("valve_feedback_state", 0)
                        
                        self.channels[ch_num].update_telemetry(press_kpa, target_kpa, flow, int(valve))
                        
        except Exception as e:
            pass 

    def closeEvent(self, event):
        self.influx_client.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WHAMDashboard()
    window.show()
    sys.exit(app.exec_())