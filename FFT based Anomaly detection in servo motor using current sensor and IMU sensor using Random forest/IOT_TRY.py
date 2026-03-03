from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import serial
import time
import sys
import requests
from plyer import notification

# ==========================
# CONFIGURATION
# ==========================
PORT = "COM9"
BAUD = 9600

THRESHOLD_MAG = 11.85        # ADXL threshold
THRESHOLD_CURRENT = 150     # INA219 threshold (you can tune this)

# Telegram config
BOT_TOKEN = "7984732469:AAFxzcBgVk1TLk5DA3TpntB4bjKfapegkyI"   # Telegram bot token
CHAT_ID = "1979714611"  

# ==========================
# TELEGRAM FUNCTION
# ==========================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg}
        requests.post(url, data=data)
    except:
        print("Telegram send failed")

# ==========================
# DESKTOP POPUP
# ==========================
def show_popup(msg):
    try:
        notification.notify(
            title="⚠ SENSOR WARNING",
            message=msg,
            timeout=4
        )
    except:
        print("Popup failed")

# ==========================
# SERIAL INITIALIZATION
# ==========================
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(1)

# ==========================
# PYQT APPLICATION
# ==========================
app = QtWidgets.QApplication([])

win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Sensor Dashboard")
win.resize(1100, 650)
win.setWindowTitle("ADXL + INA219 Monitoring")

pg.setConfigOptions(antialias=True)

# ==========================
# ADXL Magnitude Graph
# ==========================
p1 = win.addPlot(title="ADXL Magnitude (m/s²)", row=0, col=0)
p1.setLabel('left', 'Magnitude')
p1.setLabel('bottom', 'Samples')
curve_mag = p1.plot(pen='g')

p1.addLine(y=THRESHOLD_MAG, pen=pg.mkPen('r', width=2))

# ==========================
# INA219 Current Graph
# ==========================
p2 = win.addPlot(title="INA219 Current (mA)", row=1, col=0)
p2.setLabel('left', 'Current (mA)')
p2.setLabel('bottom', 'Samples')
curve_current = p2.plot(pen='y')

p2.addLine(y=THRESHOLD_CURRENT, pen=pg.mkPen('r', width=2))

# ==========================
# WARNING TEXT ON TOP GRAPH
# ==========================
warning_text = pg.TextItem(
    text="",
    color="r",
    anchor=(0, 1),
    fill=pg.mkBrush(0, 0, 0, 150)
)
p1.addItem(warning_text)

# ==========================
# DATA BUFFERS
# ==========================
mag_data = []
current_data = []
max_points = 200

alert_sent = False
alert_cooldown = 5
last_alert_time = 0

# ==========================
# UPDATE LOOP
# ==========================
def update():
    global alert_sent, last_alert_time

    line = ser.readline().decode().strip()
    parts = line.split(",")

    # Expected from your Arduino:
    # x, y, z, magnitude, current_mA, angle, status
    if len(parts) < 6:
        return

    try:
        mag = float(parts[3])
        current = float(parts[4])
    except:
        return

    # Store data
    mag_data.append(mag)
    current_data.append(current)

    if len(mag_data) > max_points:
        mag_data.pop(0)
    if len(current_data) > max_points:
        current_data.pop(0)

    # Update graphs
    curve_mag.setData(mag_data)
    curve_current.setData(current_data)

    # Check for anomaly
    anomaly = False

    if mag > THRESHOLD_MAG:
        anomaly = True
        warning_text.setText(f"⚠ ADXL Peak: {mag:.2f}")
    elif current > THRESHOLD_CURRENT:
        anomaly = True
        warning_text.setText(f"⚠ HIGH CURRENT: {current:.2f} mA")
    else:
        warning_text.setText("")

    # Send alerts
    now = time.time()
    if anomaly and (now - last_alert_time > alert_cooldown):
        last_alert_time = now

        msg = f"⚠ Sensor Alert!\nMagnitude: {mag:.2f}\nCurrent: {current:.2f} mA"
        send_telegram(msg)
        show_popup(msg)


# TIMER FOR REAL-TIME UPDATE
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(25)   # ~40 FPS smooth graph

# RUN APP
sys.exit(app.exec_())
