import sys
import time
import win32gui
import win32api
import win32con
import win32process
import win32event
import win32gui_struct
import ctypes
import psutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QApplication, QWidget
from ctypes import wintypes
import win32con
import pythoncom
import time

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
dwmapi = ctypes.windll.dwmapi

_has_getdpiforwindow: bool

# Debug toggle: set True to print windows / segments info
DEBUG = False


#region WHAT IN THE HELL
user32 = ctypes.windll.user32

# Callback for window events
WinEventProcType = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD
)

def win_event_callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
    # Only top-level windows
    if idObject != win32con.OBJID_WINDOW or windows_detector == None:
        return
    
    print("Hook went off")
    # Call your update functions
    schedule_update()
    # QTimer.singleShot(0, windows_detector.update_window_list) #type: ignore
    # QTimer.singleShot(0, windows_detector.update_frame) #type: ignore

update_timer = QTimer()
update_timer.setSingleShot(True)
update_timer.setInterval(16)  # ~60Hz max

def schedule_update():
    if not update_timer.isActive():
        update_timer.timeout.connect(run_update)
        update_timer.start()

def run_update():
    print("actual update")
    windows_detector.update_window_list()
    windows_detector.update_frame()

# Convert the Python function into a callback
WinEventProc = WinEventProcType(win_event_callback)

# Hook events that indicate window changes
EVENTS = [
    win32con.EVENT_OBJECT_SHOW,
    win32con.EVENT_OBJECT_HIDE,
    win32con.EVENT_OBJECT_LOCATIONCHANGE,
    win32con.EVENT_SYSTEM_FOREGROUND,
    win32con.EVENT_SYSTEM_MINIMIZESTART,
    win32con.EVENT_SYSTEM_MINIMIZEEND,
]

# Register hooks
hooks = []
for ev in EVENTS:
    hook = user32.SetWinEventHook(
        ev,
        ev,
        0,
        WinEventProc,
        0, 0,
        win32con.WINEVENT_OUTOFCONTEXT | win32con.WINEVENT_SKIPOWNPROCESS
    )
    hooks.append(hook)

print("Window event hooks installed — listening for changes...")

#endregion

try:
    user32.GetDpiForWindow.restype = ctypes.c_uint
    _has_getdpiforwindow = True
except Exception:
    pass

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]


def get_extended_frame_bounds(hwnd):
    rect = RECT()
    result = dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        DWMWA_EXTENDED_FRAME_BOUNDS,
        ctypes.byref(rect),
        ctypes.sizeof(rect)
    )
    if result != 0:
        return None
    return (rect.left, rect.top, rect.right, rect.bottom)


def is_window_cloaked(hwnd):
    cloaked = wintypes.DWORD()
    result = dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        DWMWA_CLOAKED,
        ctypes.byref(cloaked),
        ctypes.sizeof(cloaked)
    )
    if result != 0:
        return False
    return cloaked.value != 0

def is_fullscreen(hwnd):
    rect = get_extended_frame_bounds(hwnd)
    if not rect:
        return False

    monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
    info = win32api.GetMonitorInfo(monitor)
    mx1, my1, mx2, my2 = info["Monitor"]
    # print(" rect ==", (mx1, my1, mx2, my2))

    return rect == (mx1, my1, mx2, my2)

def is_maximized(hwnd):
    try:
        placement = win32gui.GetWindowPlacement(hwnd)
        return placement[1] == win32con.SW_MAXIMIZE
    except:
        return False

def is_window_real(hwnd):
    """
    Return True if this hwnd is a "real" user window your pet can interact with.
    Filters out:
        - Tool windows
        - Taskbar, desktop, worker windows
        - Flyouts / IME / popups
        - Cloaked or zero-size windows
    """
    try:
        # Must exist
        if not win32gui.IsWindow(hwnd):
            return False

        if not win32gui.IsWindowVisible(hwnd):
            return False

        # Ignore cloaked windows (UWP / modern app hidden windows)
        if is_window_cloaked(hwnd):
            return False

        # Get styles
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

        # Skip tool windows
        if exstyle & win32con.WS_EX_TOOLWINDOW:
            return False

        # Skip windows without overlapped style (normal app windows)
        if not (style & win32con.WS_OVERLAPPEDWINDOW):
            return False

        # Skip system tray / taskbar / desktop
        cls = win32gui.GetClassName(hwnd)
        if cls in {
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "Shell_SecondaryTrayWnd",
            "SystemTray_Main",
        }:
            return False

        # Skip tiny or zero-size windows
        rect = get_extended_frame_bounds(hwnd)
        if not rect:
            return False
        L, T, R, B = rect
        if R - L < 50 or B - T < 50:
            return False

        # Skip windows that are topmost flyouts (like Network / Volume / Emoji)
        if style & win32con.WS_POPUP and not style & win32con.WS_OVERLAPPEDWINDOW:
            return False

        # If it passed all checks, it's probably a real window
        return True

    except Exception:
        return False

def get_windows_in_zorder(excluded_hwnd):
    """
    Return list of top-level window HWNDs in Z-order (top-first),
    using DWM visual bounds and ignoring cloaked windows.
    """

    try:
        fg = win32gui.GetForegroundWindow()
        start = win32gui.GetWindow(fg, win32con.GW_HWNDFIRST)
    except Exception:
        start = win32gui.GetWindow(
            win32gui.GetDesktopWindow(),
            win32con.GW_HWNDFIRST
        )

    windows = []
    hwnd = start

    while hwnd:
        window = hwnd
        hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
        try:
            if window not in excluded_hwnd and is_window_real(window):
                if is_fullscreen(window):
                    title = win32gui.GetWindowText(window)
                    # print("FULLSCREEN:", title)
                    windows.append(window)
                    break
                elif is_maximized(window):
                    title = win32gui.GetWindowText(window)
                    # print("MAXIMISED: ", title)
                    windows.append(window)
                    break

                cls = win32gui.GetClassName(window)
                style = win32gui.GetWindowLong(window, win32con.GWL_STYLE)
                exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

                # print(f"Name: {win32gui.GetWindowText(window)}\nWindow: {window}\nClass: {cls}\nStyle: {style}")

                windows.append(window)

        except Exception:
            pass

    return windows


def is_real_app(hwnd):
    try:
        if not win32gui.IsWindow(hwnd):
            return False

        # Top-level only
        if win32gui.GetParent(hwnd) != 0:
            return False
        if win32gui.GetWindow(hwnd, win32con.GW_OWNER) != 0:
            return False
        
                # Ignore cloaked windows (UWP / modern app hidden windows)
        if is_window_cloaked(hwnd):
            return False

        # Styles
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

        # Must be normal overlapped window, not tool window or pure popup
        if not (style & win32con.WS_OVERLAPPEDWINDOW):
            return False
        
        if exstyle & win32con.WS_EX_TOOLWINDOW:
            return False
        
        if exstyle & win32con.WS_EX_APPWINDOW:
            return False

        # Size
        rect = get_extended_frame_bounds(hwnd)
        if not rect:
            return False
        L, T, R, B = rect
        if R - L < 50 or B - T < 50:
            return False

        # Title
        # title = win32gui.GetWindowText(hwnd).strip()
        # if not title:
        #     return False

        # System classes to ignore
        cls = win32gui.GetClassName(hwnd)
        if cls in {
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "Shell_SecondaryTrayWnd",
            "SystemTray_Main",
        }:
            return False

        # Check process name to filter shell / system processes
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc_name = psutil.Process(pid).name().lower()
        if proc_name in {"explorer.exe", "taskhostw.exe", "ctfmon.exe"}:
            return False

        return True

    except Exception:
        return False


def compute_visible_segments(windows, rects):
    """
    windows: list of HWND top-first (topmost first)

    Returns:
        dict hwnd -> {
            "rect": (L,T,R,B),
            "top": [(x1,x2)],
            "bottom": [(x1,x2)],
            "left": [(y1,y2)],
            "right": [(y1,y2)],
        }
    """

    segs = {}

    # bottom-first for occlusion logic
    windows_bottom_first = list(reversed(windows))

    for idx, hwnd in enumerate(windows_bottom_first):

        rect = rects.get(hwnd)
        if not rect:
            continue

        L, T, R, B = rect

        top_seg = (L, R)
        bottom_seg = (L, R)
        left_seg = (T, B)
        right_seg = (T, B)

        cuts_top = []
        cuts_bottom = []
        cuts_left = []
        cuts_right = []

        # windows above this one
        for above in windows_bottom_first[idx + 1:]:
            ar = rects.get(above)
            if not ar:
                continue

            inter = intersect_rect(rect, ar)
            if not inter:
                continue

            x1, y1, x2, y2 = inter

            if y1 <= T <= y2:
                cuts_top.append((x1, x2))

            if y1 <= B <= y2:
                cuts_bottom.append((x1, x2))

            if x1 <= L <= x2:
                cuts_left.append((y1, y2))

            if x1 <= R <= x2:
                cuts_right.append((y1, y2))

        vis_top = subtract_many(top_seg, cuts_top)
        vis_bottom = subtract_many(bottom_seg, cuts_bottom)
        vis_left = subtract_many(left_seg, cuts_left)
        vis_right = subtract_many(right_seg, cuts_right)

        segs[hwnd] = {
            "rect": rect,
            "top": vis_top,
            "bottom": vis_bottom,
            "left": vis_left,
            "right": vis_right,
        }

    return segs

def update_active_apps():
    try:
        fg = win32gui.GetForegroundWindow()
        start = win32gui.GetWindow(fg, win32con.GW_HWNDFIRST)
    except Exception:
        start = win32gui.GetWindow(win32gui.GetDesktopWindow(), win32con.GW_HWNDFIRST)

    hwnd = start
    apps = set()
    pid_cache = {}

    while hwnd:
        if is_real_app(hwnd):
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid not in pid_cache:
                    pid_cache[pid] = psutil.Process(pid).name()
                apps.add(pid_cache[pid])
            except Exception:
                pass

        hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)

    # print("Active apps:", apps)
    
def get_window_dpi_scale(hwnd):
    """Return DPI scale for HWND (physical -> logical)."""
    # Try modern API
    try:
        if _has_getdpiforwindow:
            dpi = user32.GetDpiForWindow(hwnd)
            if dpi and dpi != 0:
                return dpi / 96.0
    except Exception:
        pass
    # Fallback: system DPI via device caps
    try:
        hdc = win32gui.GetDC(0)
        LOGPIXELSX = 88
        dpi = win32gui.GetDeviceCaps(hdc, LOGPIXELSX)  # type: ignore
        if dpi and dpi != 0:
            return dpi / 96.0
    except Exception:
        pass
    return 1.0

# -----------------------
# Geometry helpers
# -----------------------
def intersect_rect(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    cx1 = max(ax1, bx1)
    cy1 = max(ay1, by1)
    cx2 = min(ax2, bx2)
    cy2 = min(ay2, by2)
    if cx2 <= cx1 or cy2 <= cy1:
        return None
    return (cx1, cy1, cx2, cy2)

def subtract_segment(seg, cut):
    s1, s2 = seg
    c1, c2 = cut
    if c2 <= s1 or c1 >= s2:
        return [seg]
    pieces = []
    if c1 > s1:
        pieces.append((s1, c1))
    if c2 < s2:
        pieces.append((c2, s2))
    return pieces

def subtract_many(seg, cuts):
    visible = [seg]
    for cut in cuts:
        new_list = []
        for v in visible:
            new_list.extend(subtract_segment(v, cut))
        visible = new_list
    return visible



# -----------------------
# Overlay Widget
# -----------------------
class WindowsOverlay(QWidget):
    def __init__(self, pet):
        super().__init__()

        self.pet: QWidget = pet

        global windows_detector
        windows_detector = self

        # Transparent click-through fullscreen overlay
        self.setWindowFlags(
            Qt.FramelessWindowHint # type: ignore
            | Qt.WindowStaysOnTopHint # type: ignore
            | Qt.Tool # type: ignore
            | Qt.WindowTransparentForInput # type: ignore
        )
        self.setAttribute(Qt.WA_TranslucentBackground) # type: ignore
        self.showFullScreen()

        # store overlay hwnd to skip it in enumeration
        my_hwnd = int(self.winId())
        pet_hwnd = int(self.pet.winId())
        self.excluded_hwnd = {my_hwnd, pet_hwnd} # set of excluded from search hwnd 

        # cached data
        self.windows = []   # top-first
        self.active_apps = {}   # top-first
        self.rects = {}     # hwnd -> rect physical
        self.segments = {}  # hwnd -> clipped segments computed in physical pixels

        # Hook all top-level window events
        user32 = ctypes.windll.user32


    def update_window_list(self):
        update_active_apps()
        self.windows = get_windows_in_zorder(excluded_hwnd=self.excluded_hwnd)
        if DEBUG:
            print(f"[enum] found {len(self.windows)} windows")

    def update_frame(self):
        # update rects for current cached windows
        rects = {}

        for hwnd in self.windows:
            scale = get_window_dpi_scale(hwnd=hwnd) # this is probably to remove or move up, its getting dpi per window
            if scale <= 0:
                scale = 1.0
            
            if not is_window_cloaked(hwnd) and not is_fullscreen(hwnd) and not is_maximized(hwnd):
                try:
                    rect = get_extended_frame_bounds(hwnd)
                    if rect and rect[0] != rect[2] and rect[1] != rect[3]:
                        rects[hwnd] = (rect[0]/scale, rect[1]/scale, rect[2]/scale, rect[3]/scale) # getting real scaled values for positions
                except Exception:
                    pass

        self.rects = rects

        # recompute clipped border segments in physical pixels
        self.segments = compute_visible_segments(self.windows, self.rects)

        if DEBUG:
            # print a summary for the top few windows
            topn = min(6, len(self.windows))
            print(f"[frame] rects={len(self.rects)}, segs={len(self.segments)} (top {topn}):")
            for i, hwnd in enumerate(self.windows[:topn]):
                title = win32gui.GetWindowText(hwnd)
                rect = self.rects.get(hwnd)
                seg = self.segments.get(hwnd)
                print(f"  {i}: hwnd={hwnd} title={repr(title)} rect={rect} segs_top={len(seg['top']) if seg else 0}")

        # trigger repaint
        self.update()


    def get_nearest_surface(self, direction):
        self.update_window_list()
        rects = self.rects

        for hwnd in self.windows:
            L, T, R, B = rects[hwnd]  

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # type: ignore

        # pen width is in logical pixels; color alpha for nice appearance
        pen = QPen(QColor(0, 200, 60, 255), 25)
        painter.setPen(pen)

        # draw every cached segment using per-window DPI scale conversion
        for hwnd, data in list(self.segments.items()):
            rect = data["rect"]
            if not rect:
                continue
            L, T, R, B = rect

            # scale = get_window_dpi_scale(hwnd=hwnd)
            # if scale <= 0:
            #     scale = 1.0

            # scaled coords (logical)
            dL = int(round(L))
            dT = int(round(T))
            dR = int(round(R))
            dB = int(round(B))

            # top
            for x1, x2 in data["top"]:
                sx1 = int(round(x1))
                sx2 = int(round(x2))
                painter.setPen(QColor(0, 200, 60))
                painter.drawLine(sx1, dT, sx2, dT)

            # bottom
            for x1, x2 in data["bottom"]:
                sx1 = int(round(x1))
                sx2 = int(round(x2))
                painter.setPen(QColor(220, 0, 220))
                painter.drawLine(sx1, dB, sx2, dB)

            # left
            for y1, y2 in data["left"]:
                sy1 = int(round(y1))
                sy2 = int(round(y2))
                painter.setPen(QColor(20, 150, 255))
                painter.drawLine(dL, sy1, dL, sy2)

            # right
            for y1, y2 in data["right"]:
                sy1 = int(round(y1))
                sy2 = int(round(y2))
                painter.setPen(QColor(210, 100, 100))
                painter.drawLine(dR, sy1, dR, sy2)

        painter.end()


# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = WindowsOverlay(pet=None)
    sys.exit(app.exec())
