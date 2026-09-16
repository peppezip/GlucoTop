import sys
import ctypes
import os
import json
from datetime import datetime, timezone

from dotenv import load_dotenv

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QPushButton,
    QRadioButton,
    QGroupBox,
    QMenu,
)


# ============================================================
# DEXCOM CONFIGURATION
# ============================================================

load_dotenv()

DEXCOM_USERNAME = os.getenv("DEXCOM_USERNAME")
DEXCOM_PASSWORD = os.getenv("DEXCOM_PASSWORD")
DEXCOM_REGION = os.getenv("DEXCOM_REGION", "ous")


# ============================================================
# WIDGET CONFIGURATION
# ============================================================

WIDGET_SIZE = 115

# Update interval: 5 minutes
UPDATE_INTERVAL = 300000

# Glucose thresholds in mg/dL
LOW_THRESHOLD = 70
HIGH_THRESHOLD = 180

# Maximum age before a reading is considered stale
# Value is expressed in minutes
STALE_READING_MINUTES = 10

# Distance from the screen edges
DEFAULT_MARGIN = 20


# ============================================================
# COLORS
# ============================================================

COLOR_NORMAL = "#4CAF50"
COLOR_LOW = "#FF4D4D"
COLOR_HIGH = "#FFC107"
COLOR_STALE = "#FF9800"
COLOR_ERROR = "#FF4D4D"
COLOR_NEUTRAL = "#AAAAAA"


# ============================================================
# LOCAL CONFIGURATION
# ============================================================

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "config.json"
)


def load_config():
    """Load the local widget configuration."""

    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except Exception as e:
        print(f"Error reading configuration: {e}")
        return {}


def save_config(config):
    """Save the local widget configuration."""

    try:
        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                config,
                file,
                indent=4
            )

    except Exception as e:
        print(f"Error saving configuration: {e}")


# ============================================================
# SINGLE INSTANCE
# ============================================================

# Unique Windows mutex name for GlucoDesk.
# This only prevents multiple GlucoDesk instances.
MUTEX_NAME = "GlucoDesk_SingleInstance"

mutex_handle = None


def acquire_single_instance():
    """
    Create a Windows named mutex.

    Return True if this is the first GlucoDesk instance.
    Return False if another GlucoDesk instance is already running.
    """

    global mutex_handle

    kernel32 = ctypes.windll.kernel32

    ERROR_ALREADY_EXISTS = 183

    mutex_handle = kernel32.CreateMutexW(
        None,
        False,
        MUTEX_NAME
    )

    if not mutex_handle:
        print(
            "Unable to create GlucoDesk instance mutex."
        )

        return False

    last_error = kernel32.GetLastError()

    if last_error == ERROR_ALREADY_EXISTS:

        kernel32.CloseHandle(
            mutex_handle
        )

        mutex_handle = None

        print(
            "GlucoDesk is already running."
        )

        return False

    return True


def release_single_instance():
    """Release the Windows GlucoDesk mutex."""

    global mutex_handle

    if mutex_handle:

        ctypes.windll.kernel32.ReleaseMutex(
            mutex_handle
        )

        ctypes.windll.kernel32.CloseHandle(
            mutex_handle
        )

        mutex_handle = None


# ============================================================
# UNIT SELECTION
# ============================================================

def choose_unit():
    """
    Ask the user which glucose measurement unit
    should be displayed.

    Return the selected unit and whether the dialog
    was confirmed.
    """

    dialog = QDialog()

    dialog.setWindowTitle(
        "GlucoDesk"
    )

    dialog.setFixedSize(
        360,
        220
    )

    layout = QVBoxLayout(
        dialog
    )

    title = QLabel(
        "<b>Choose your glucose unit</b><br><br>"
        "Select how you want your glucose value "
        "to be displayed:"
    )

    title.setWordWrap(True)

    layout.addWidget(
        title
    )

    group = QGroupBox()

    group_layout = QVBoxLayout(
        group
    )

    mg_radio = QRadioButton(
        "mg/dL"
    )

    mmol_radio = QRadioButton(
        "mmol/L"
    )

    mg_radio.setChecked(
        True
    )

    group_layout.addWidget(
        mg_radio
    )

    group_layout.addWidget(
        mmol_radio
    )

    layout.addWidget(
        group
    )

    ok_button = QPushButton(
        "OK"
    )

    cancel_button = QPushButton(
        "Cancel"
    )

    ok_button.clicked.connect(
        dialog.accept
    )

    cancel_button.clicked.connect(
        dialog.reject
    )

    button_layout = QHBoxLayout()
    button_layout.addStretch()
    button_layout.addWidget(ok_button)
    button_layout.addWidget(cancel_button)

    layout.addLayout(
        button_layout
    )

    result = dialog.exec()

    if result != QDialog.DialogCode.Accepted:
        return None, False

    if mmol_radio.isChecked():
        return "mmol/L", True

    return "mg/dL", True

def get_unit():
    """
    Return the configured unit.

    If no unit has been configured yet,
    ask the user during the first launch.
    """

    config = load_config()

    unit = config.get(
        "unit"
    )

    if unit in (
        "mg/dL",
        "mmol/L"
    ):
        return unit

    unit, confirmed = choose_unit()

    if not confirmed:
        return None

    config["unit"] = unit

    save_config(
        config
    )

    return unit


# ============================================================
# WINDOWS DESKTOP INTEGRATION
# ============================================================

def make_desktop_widget(hwnd):
    """
    Attach the widget to the Windows desktop layer.

    This allows the widget to remain visible on the desktop
    when using Win+D.
    """

    user32 = ctypes.windll.user32

    # Find the Windows desktop icon container
    progman = user32.FindWindowW(
        "Progman",
        None
    )

    shelldll = user32.FindWindowExW(
        progman,
        0,
        "SHELLDLL_DefView",
        None
    )

    if not shelldll:

        # Force Windows to create the WorkerW layer
        user32.SendMessageTimeoutW(
            progman,
            0x052C,
            0,
            0,
            0x0002,
            1000,
            None
        )

        def enum_windows_proc(
            top_hwnd,
            extra_param
        ):
            nonlocal shelldll

            s = user32.FindWindowExW(
                top_hwnd,
                0,
                "SHELLDLL_DefView",
                None
            )

            if s:
                shelldll = s
                return False

            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p
        )

        user32.EnumWindows(
            WNDENUMPROC(enum_windows_proc),
            0
        )

    # Attach the widget to the desktop
    target = (
        shelldll
        if shelldll
        else progman
    )

    user32.SetParent(
        hwnd,
        target
    )


# ============================================================
# DEXCOM WIDGET
# ============================================================

class DexcomWidget(QWidget):

    def __init__(self, unit):

        super().__init__()

        self.unit = unit
        self.dexcom = None

        # Track the current connection state
        self.connection_status = "disconnected"

        self.initUI()

        self.connect_dexcom()

        # Create the automatic update timer
        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.update_glucose
        )

        self.timer.start(
            UPDATE_INTERVAL
        )

        # Perform the first reading immediately
        self.update_glucose()

    # --------------------------------------------------------
    # USER INTERFACE
    # --------------------------------------------------------

    def initUI(self):
        """Configure the widget appearance."""

        # Frameless window hidden from the taskbar
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )

        # Transparent window background
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True
        )

        # Keep the widget square
        self.setFixedSize(
            WIDGET_SIZE,
            WIDGET_SIZE
        )

        layout = QVBoxLayout()

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.label = QLabel(
            "..."
        )

        self.label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.label.setWordWrap(
            True
        )

        layout.addWidget(
            self.label
        )

        self.setLayout(
            layout
        )

        # Position the widget in the bottom-right corner
        self.position_bottom_right()

    # --------------------------------------------------------
    # WIDGET POSITION
    # --------------------------------------------------------

    def position_bottom_right(self):
        """
        Position the widget in the bottom-right corner
        of the primary screen.
        """

        screen = QApplication.primaryScreen()

        if not screen:
            return

        work_area = (
            screen.availableGeometry()
        )

        margin = DEFAULT_MARGIN

        x = (
            work_area.right()
            - self.width()
            - margin
        )

        y = (
            work_area.bottom()
            - self.height()
            - margin
        )

        self.move(
            x,
            y
        )

    # --------------------------------------------------------
    # CONTEXT MENU
    # --------------------------------------------------------

    def mousePressEvent(self, event):
        """
        Handle mouse clicks.

        Left click does nothing.
        Right click opens the context menu.
        """

        if (
            event.button()
            == Qt.MouseButton.RightButton
        ):

            self.show_context_menu(
                event.globalPosition().toPoint()
            )

            event.accept()

        else:

            event.accept()

    def show_context_menu(self, position):
        """Display the widget context menu."""

        menu = QMenu()

        change_unit = menu.addAction(
            "Change unit"
        )

        menu.addSeparator()

        refresh = menu.addAction(
            "Refresh now"
        )

        menu.addSeparator()

        exit_action = menu.addAction(
            "Exit"
        )

        action = menu.exec(
            position
        )

        if action == change_unit:

            self.change_unit()

        elif action == refresh:

            self.update_glucose()

        elif action == exit_action:

            QApplication.quit()

    # --------------------------------------------------------
    # CHANGE UNIT
    # --------------------------------------------------------

    def change_unit(self):
        """Allow the user to change the glucose unit."""

        new_unit, confirmed = choose_unit()

        if not confirmed:
            return

        self.unit = new_unit

        config = load_config()

        config["unit"] = new_unit

        save_config(
            config
        )

        self.update_glucose()

    # --------------------------------------------------------
    # DEXCOM CONNECTION
    # --------------------------------------------------------

    def connect_dexcom(self):
        """Connect to the user's Dexcom account."""

        if (
            not DEXCOM_USERNAME
            or not DEXCOM_PASSWORD
        ):

            print(
                "Dexcom credentials are not configured."
            )

            self.dexcom = None
            self.connection_status = "login_error"

            return False

        try:

            from pydexcom import Dexcom

            self.dexcom = Dexcom(
                username=DEXCOM_USERNAME,
                password=DEXCOM_PASSWORD,
                region=DEXCOM_REGION
            )

            self.connection_status = "connected"

            print(
                "Dexcom connection successful!"
            )

            return True

        except Exception as e:

            print(
                f"Dexcom login error: {e}"
            )

            self.dexcom = None
            self.connection_status = "login_error"

            return False

    # --------------------------------------------------------
    # DESKTOP ATTACHMENT
    # --------------------------------------------------------

    def showEvent(self, event):
        """Attach the widget to the Windows desktop."""

        super().showEvent(
            event
        )

        make_desktop_widget(
            int(self.winId())
        )

        # Re-apply the fixed bottom-right position
        self.position_bottom_right()

    # --------------------------------------------------------
    # GLUCOSE UPDATE
    # --------------------------------------------------------

    def update_glucose(self):
        """Retrieve and display the latest glucose reading."""

        if not self.dexcom:

            connected = self.connect_dexcom()

            if not connected:

                if self.connection_status == "login_error":

                    self.show_error_state(
                        "ERR",
                        "Login",
                        COLOR_ERROR
                    )

                else:

                    self.show_error_state(
                        "ERR",
                        "Connect",
                        COLOR_ERROR
                    )

                return

        try:

            glucose = (
                self.dexcom
                .get_current_glucose_reading()
            )

            if not glucose:

                self.connection_status = "connected"

                self.show_error_state(
                    "N/D",
                    "",
                    COLOR_NEUTRAL
                )

                return

            self.connection_status = "connected"

            # Glucose value in mg/dL
            value_mg = glucose.value

            # Glucose value in mmol/L
            value_mmol = glucose.mmol_l

            # Dexcom trend arrow
            trend = (
                glucose.trend_arrow
                or ""
            )

            # ------------------------------------------------
            # READING AGE
            # ------------------------------------------------

            minutes_ago = (
                self.get_minutes_ago(
                    glucose
                )
            )

            # Determine whether the reading is stale
            is_stale = (
                minutes_ago is not None
                and minutes_ago >= STALE_READING_MINUTES
            )

            # ------------------------------------------------
            # SELECT DISPLAY UNIT
            # ------------------------------------------------

            if self.unit == "mg/dL":

                value_text = (
                    f"{value_mg}"
                )

                unit_text = (
                    "mg/dL"
                )

            else:

                value_text = (
                    f"{value_mmol:.1f}"
                )

                unit_text = (
                    "mmol/L"
                )

            # ------------------------------------------------
            # READING AGE TEXT
            # ------------------------------------------------

            if minutes_ago is None:

                updated_text = ""

            elif minutes_ago <= 1:

                updated_text = "just now"

            else:

                updated_text = (
                    f"{minutes_ago} min ago"
                )

            # ------------------------------------------------
            # COLOR
            # ------------------------------------------------

            # Thresholds are always evaluated using mg/dL
            if value_mg < LOW_THRESHOLD:

                color = COLOR_LOW

            elif value_mg > HIGH_THRESHOLD:

                color = COLOR_HIGH

            elif is_stale:

                color = COLOR_STALE

            else:

                color = COLOR_NORMAL

            # ------------------------------------------------
            # DISPLAY
            # ------------------------------------------------

            self.label.setText(
                f"""
                <div align="center">

                    <span style="
                        font-size:9px;
                        color:#AAAAAA;
                    ">
                        {updated_text}
                    </span>

                    <br>

                    <span style="
                        font-size:20px;
                        font-weight:bold;
                    ">
                        {value_text}
                    </span>

                    <span style="
                        font-size:12px;
                    ">
                        {unit_text}
                    </span>

                    <br>

                    <span style="
                        font-size:18px;
                        font-weight:bold;
                    ">
                        {trend}
                    </span>

                </div>
                """
            )

            self._apply_style(
                color
            )

            if is_stale:

                print(
                    f"Warning: glucose reading is "
                    f"{minutes_ago} minutes old."
                )

        except Exception as e:

            print(
                f"Error retrieving glucose reading: {e}"
            )

            self.show_error_state(
                "ERR",
                "Network",
                COLOR_ERROR
            )

            # Force a new connection on the next update
            self.dexcom = None
            self.connection_status = "network_error"

    # --------------------------------------------------------
    # ERROR DISPLAY
    # --------------------------------------------------------

    def show_error_state(
        self,
        main_text,
        secondary_text,
        color
    ):
        """Display a compact error or unavailable state."""

        if secondary_text:

            text = (
                f"""
                <div align="center">

                    <span style="
                        font-size:19px;
                        font-weight:bold;
                    ">
                        {main_text}
                    </span>

                    <br>

                    <span style="
                        font-size:11px;
                    ">
                        {secondary_text}
                    </span>

                </div>
                """
            )

        else:

            text = (
                f"""
                <div align="center">

                    <span style="
                        font-size:19px;
                        font-weight:bold;
                    ">
                        {main_text}
                    </span>

                </div>
                """
            )

        self.label.setText(
            text
        )

        self._apply_style(
            color
        )

    # --------------------------------------------------------
    # READING TIMESTAMP
    # --------------------------------------------------------

    def get_minutes_ago(self, reading):
        """Calculate how many minutes ago the reading was taken."""

        try:

            reading_time = (
                reading.datetime
            )

            if reading_time is None:
                return None

            if reading_time.tzinfo is None:

                now = datetime.now()

            else:

                now = datetime.now(
                    timezone.utc
                )

            difference = (
                now - reading_time
            )

            minutes = int(
                difference.total_seconds()
                / 60
            )

            return max(
                0,
                minutes
            )

        except Exception as e:

            print(
                f"Error calculating timestamp: {e}"
            )

            return None

    # --------------------------------------------------------
    # WIDGET STYLE
    # --------------------------------------------------------

    def _apply_style(self, color):
        """Apply the visual style to the widget."""

        self.label.setStyleSheet(
            f"""
            QLabel {{
                background-color: #121212;
                color: {color};
                border-radius: 18px;
                border: 2px solid {color};
                padding: 5px;
            }}
            """
        )


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":

    # The current implementation supports Windows only
    if sys.platform != "win32":

        print(
            "This widget currently supports "
            "Windows only."
        )

        sys.exit(1)

    # Prevent multiple GlucoDesk instances
    if not acquire_single_instance():

        sys.exit(0)

    app = QApplication(
        sys.argv
    )

    # Do not close the application when a temporary dialog closes.
    app.setQuitOnLastWindowClosed(False)

    # Release the mutex when the application exits
    app.aboutToQuit.connect(
        release_single_instance
    )

    # Ask for the unit during the first launch
    unit = get_unit()

    if unit is None:

        release_single_instance()

        sys.exit(0)

    print(
        f"Selected unit: {unit}"
    )

    widget = DexcomWidget(
        unit
    )

    widget.show()

    sys.exit(
        app.exec()
    )