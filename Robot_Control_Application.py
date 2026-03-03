from PyQt5 import QtCore, QtGui, QtWidgets
from datetime import datetime
import math, random, socket


class VirtualJoystick(QtWidgets.QWidget):
    angleChanged = QtCore.pyqtSignal(float)
    speedChanged = QtCore.pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self.x = 0
        self.y = 0
        self.dragging = False

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w, h = self.width(), self.height()
        self.r = min(w, h) // 2 - 10
        self.center = QtCore.QPoint(w // 2, h // 2)

        painter.drawEllipse(self.center, self.r, self.r)

        stick_x = int(self.center.x() + self.x * self.r)
        stick_y = int(self.center.y() - self.y * self.r)

        painter.setBrush(QtGui.QBrush(QtCore.Qt.gray))
        painter.drawEllipse(QtCore.QPoint(stick_x, stick_y), 12, 12)

    def updateStick(self, x, y):
        self.x, self.y = x, y
        self.update()

        speed = min(1.0, math.sqrt(x*x + y*y))
        angle = (math.degrees(math.atan2(y, x)) + 360) % 360

        self.angleChanged.emit(angle)
        self.speedChanged.emit(speed)

    def mousePressEvent(self, event):
        self.dragging = True
        self._updateFromMouse(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            self._updateFromMouse(event)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.updateStick(0, 0)

    def _updateFromMouse(self, event):
        dx = event.x() - self.center.x()
        dy = self.center.y() - event.y()

        mag = math.sqrt(dx*dx + dy*dy)
        if mag > self.r:
            dx = dx * self.r / mag
            dy = dy * self.r / mag

        self.updateStick(dx / self.r, dy / self.r)
        self.update()


# ---------- REUSABLE STEP PAGE ----------
class StepPage(QtWidgets.QWidget):
    def __init__(self, title):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

        header = QtWidgets.QLabel(title)
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.setAlignment(QtCore.Qt.AlignCenter)

        content = QtWidgets.QFrame()
        content.setFrameShape(QtWidgets.QFrame.StyledPanel)
        content.setMinimumHeight(300)

        layout.addWidget(header)
        layout.addWidget(content)
        layout.addStretch()


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1280, 720)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)

        # ---------------- TOP BAR ----------------
        self.topLayout = QtWidgets.QHBoxLayout()

        self.logoLabel = QtWidgets.QLabel()
        self.logoLabel.setMinimumSize(140, 60)

        self.logoLabel.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.logoLabel.setStyleSheet("border: none; background: transparent;")

        pix = QtGui.QPixmap("drc.png")
        if not pix.isNull():
            self.logoLabel.setPixmap(
                pix.scaled(140, 60,
                           QtCore.Qt.KeepAspectRatio,
                           QtCore.Qt.SmoothTransformation)
            )

        self.topLayout.addWidget(self.logoLabel, alignment=QtCore.Qt.AlignCenter)

        self.titleLabel = QtWidgets.QLabel("Welcome To Mars Rover Control Dashboard.")
        f = QtGui.QFont(); f.setPointSize(20); f.setBold(True)
        self.titleLabel.setFont(f)
        self.titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.topLayout.addWidget(self.titleLabel)

        # ---------- CONNECTION BUTTON ----------
        self.isConnected = False
        self.socket = None

        self.connectButton = QtWidgets.QPushButton("Connect")
        self.connectButton.setFixedHeight(28)
        self.connectButton.clicked.connect(self.handleConnection)
        self.topLayout.addWidget(self.connectButton)

        self.setConnectStyle()
        self.gridLayout.addLayout(self.topLayout, 0, 0, 1, 3)

        # ---------------- LEFT PANEL ----------------
        self.leftFrame = QtWidgets.QFrame()
        self.leftFrame.setFrameShape(QtWidgets.QFrame.Box)
        self.leftLayout = QtWidgets.QVBoxLayout(self.leftFrame)

        labels = [
            "1. Live Time", "2. Live Temperature", "3. Live Pressure",
            "4. Live Humidity", "5. Rover Speed (mile/hour)"
        ]

        self.buttons = []
        for i, t in enumerate(labels):
            b = QtWidgets.QPushButton(t)
            b.setMinimumHeight(40)
            self.leftLayout.addWidget(b)
            self.buttons.append(b)

            if i == 0: self.liveTimeButton = b
            if i == 1: self.liveTempButton = b
            if i == 2: self.livePressureButton = b
            if i == 3: self.liveHumidityButton = b

        self.gridLayout.addWidget(self.leftFrame, 1, 0, 2, 1)

        # ---------------- CENTER PANEL (STACK SYSTEM) ----------------
        self.centerFrame = QtWidgets.QFrame()
        self.centerFrame.setFrameShape(QtWidgets.QFrame.Box)
        self.centerLayout = QtWidgets.QVBoxLayout(self.centerFrame)

        # Step Button Bar
        self.stepButtons = []
        stepLayout = QtWidgets.QHBoxLayout()
        for i in range(1, 7):
            btn = QtWidgets.QPushButton(f"Step {i}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, x=i-1: self.stack.setCurrentIndex(x))
            self.stepButtons.append(btn)
            stepLayout.addWidget(btn)

        self.stepButtons[0].setChecked(True)
        self.centerLayout.addLayout(stepLayout)

        # STACK WIDGET
        self.stack = QtWidgets.QStackedWidget()
        self.centerLayout.addWidget(self.stack)

        # Create Step Pages
        self.stack.addWidget(StepPage("Step 1 : Rover Movement Controls"))
        self.stack.addWidget(StepPage("Step 2 : Sensor Calibration Panel"))
        self.stack.addWidget(StepPage("Step 3 : Arm / Gripper Control"))
        self.stack.addWidget(StepPage("Step 4 : Navigation & Path Planning"))
        self.stack.addWidget(StepPage("Step 5 : Power & Battery Monitoring"))
        self.stack.addWidget(StepPage("Step 6 : System Diagnostics"))

        self.gridLayout.addWidget(self.centerFrame, 1, 1, 2, 1)

        # ---------------- RIGHT PANEL ----------------
        self.rightFrame = QtWidgets.QFrame()
        self.rightFrame.setFrameShape(QtWidgets.QFrame.Box)
        self.rightLayout = QtWidgets.QVBoxLayout(self.rightFrame)

        camTabs = QtWidgets.QHBoxLayout()
        for t in ["Camera 1", "Camera 2", "Camera 3"]:
            camTabs.addWidget(QtWidgets.QPushButton(t))
        self.rightLayout.addLayout(camTabs)

        self.cameraBox = QtWidgets.QLabel("Camera View")
        self.cameraBox.setAlignment(QtCore.Qt.AlignCenter)
        self.cameraBox.setMinimumHeight(150)
        self.cameraBox.setFrameShape(QtWidgets.QFrame.Box)
        self.rightLayout.addWidget(self.cameraBox)

        # ---- JOYSTICK PANEL ----
        self.joystickWidget = VirtualJoystick()
        self.angleLabel = QtWidgets.QLabel("Angle: 0°")
        self.speedLabel = QtWidgets.QLabel("Speed: 0.00")
        self.angleLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.speedLabel.setAlignment(QtCore.Qt.AlignCenter)

        self.rightLayout.addWidget(self.joystickWidget)
        self.rightLayout.addWidget(self.angleLabel)
        self.rightLayout.addWidget(self.speedLabel)

        self.joystickWidget.angleChanged.connect(
            lambda a: self.angleLabel.setText(f"Angle: {a:.1f}°"))
        self.joystickWidget.speedChanged.connect(
            lambda s: self.speedLabel.setText(f"Speed: {s:.2f}"))

        self.gridLayout.addWidget(self.rightFrame, 1, 2, 2, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.retranslateUi(MainWindow)

        # ---------- TIMERS ----------
        self.timeTimer = QtCore.QTimer()
        self.timeTimer.timeout.connect(self.updateLiveTime)
        self.timeTimer.start(1000)
        self.updateLiveTime()

        self.tempTimer = QtCore.QTimer()
        self.tempTimer.timeout.connect(self.simulateTemperature)
        self.tempTimer.start(2000)

        self.pressureTimer = QtCore.QTimer()
        self.pressureTimer.timeout.connect(self.simulatePressure)
        self.pressureTimer.start(2000)
        self.simulatePressure()

        self.humidityTimer = QtCore.QTimer()
        self.humidityTimer.timeout.connect(self.simulateHumidity)
        self.humidityTimer.start(2000)
        self.simulateHumidity()

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("Mars Rover Control System")

    # --------- CONNECTION LOGIC ---------
    def handleConnection(self):
        if not self.isConnected:
            self.connectToServer()
        else:
            self.disconnectFromServer()

    def connectToServer(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(("192.168.0.10", 5000))
            self.isConnected = True
            self.setDisconnectStyle()
            print("Connected to Rover")
        except Exception as e:
            print("Connection failed:", e)

    def disconnectFromServer(self):
        try:
            if self.socket:
                self.socket.close()
            self.isConnected = False
            self.setConnectStyle()
            print("Disconnected from Rover")
        except Exception as e:
            print("Disconnect error:", e)

    # -------- BUTTON STYLES --------
    def setConnectStyle(self):
        self.connectButton.setText("Connect")
        self.connectButton.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                border-radius: 6px;
            }
        """)

    def setDisconnectStyle(self):
        self.connectButton.setText("Disconnect")
        self.connectButton.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                font-weight: bold;
                border-radius: 6px;
            }
        """)

    # -------- LIVE DATA --------
    def updateLiveTime(self):
        now = datetime.now().strftime("%I:%M:%S %p  |  %d-%m-%Y")
        self.liveTimeButton.setText(f"1. Live Time   —   {now}")

    def updateLiveTemperature(self, value):
        self.liveTempButton.setText(f"2. Live Temperature   —   {value:.2f} °C")

    def simulateTemperature(self):
        self.updateLiveTemperature(random.uniform(20.0, 35.0))

    def updateLivePressure(self, value):
        self.livePressureButton.setText(f"3. Live Pressure   —   {value:.2f} hPa")

    def simulatePressure(self):
        self.updateLivePressure(random.uniform(950.0, 1050.0))

    def updateLiveHumidity(self, value):
        self.liveHumidityButton.setText(f"4. Live Humidity   —   {value:.2f} %RH")

    def simulateHumidity(self):
        self.updateLiveHumidity(random.uniform(30.0, 85.0))


# -------- RUN APP --------
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
