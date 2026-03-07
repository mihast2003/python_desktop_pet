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


#region HOOKS IF WINDOW APPEAR/DISAPPEAR
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
    schedule_update()



def schedule_update():
    print("schedule_update")
    if not update_timer.isActive():
        update_timer.start()

def run_update():
    print("---------- actual update ----------------")
    windows_detector.update_window_list()
    windows_detector.update_frame()

update_timer = QTimer()
update_timer.setSingleShot(True)
update_timer.setInterval(16)  # ~60Hz max
update_timer.timeout.connect(run_update)

# Convert the Python function into a callback
WinEventProc = WinEventProcType(win_event_callback)

# Hook events that indicate window changes
UPDATE_EVENTS = [
    win32con.EVENT_OBJECT_SHOW,
    win32con.EVENT_OBJECT_HIDE,
    # win32con.EVENT_OBJECT_LOCATIONCHANGE,
    win32con.EVENT_SYSTEM_FOREGROUND,
    win32con.EVENT_SYSTEM_MINIMIZESTART,
    win32con.EVENT_SYSTEM_MINIMIZEEND,
]

# Register hooks
hooks = []
for ev in UPDATE_EVENTS:
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

        # Get styles
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)

        # Skip windows without overlapped style
        if not (style & win32con.WS_OVERLAPPEDWINDOW):
            return False
        
        if not win32gui.IsWindowVisible(hwnd):
            return False
        
        # Skip tiny or zero-size windows
        rect = get_extended_frame_bounds(hwnd)
        if not rect:
            return False
        L, T, R, B = rect
        if R - L < 50 or B - T < 50:
            return False

        exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

        # Skip tool windows
        if exstyle & win32con.WS_EX_TOOLWINDOW:
            return False
            
        
        # Ignore cloaked windows (UWP / modern app hidden windows)
        if is_window_cloaked(hwnd):
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

    windows.append("taskbar") # appending taskbar as a top window

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

                # cls = win32gui.GetClassName(window)
                # style = win32gui.GetWindowLong(window, win32con.GWL_STYLE)
                # exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

                # print(f"Name: {win32gui.GetWindowText(window)}\nWindow: {window}\nClass: {cls}\nStyle: {style}")

                windows.append(window)

        except Exception:
            pass

    return windows


def is_real_app(hwnd):
    try:
        if not win32gui.IsWindow(hwnd):
            # print("not IsWindow")
            return False

        # Top-level only
        if win32gui.GetParent(hwnd) != 0:
            # print("no GetParent")
            return False
        
        # Styles
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)

        # Must be normal overlapped window, not tool window or pure popup
        if not (style & win32con.WS_OVERLAPPEDWINDOW):
            # print("style is weird")
            return False
        
        # Size
        rect = get_extended_frame_bounds(hwnd)
        if not rect:
            # print("no rect")
            return False
        L, T, R, B = rect
        if R - L < 50 or B - T < 50:
            # print("too small")
            return False

        exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        if exstyle & win32con.WS_EX_TOOLWINDOW:
            # print("exstyle is weird")
            return False
        
        if exstyle & win32con.WS_EX_APPWINDOW:
            # print("second exstyle is weird")
            return False

        # Title
        # title = win32gui.GetWindowText(hwnd).strip()
        # if not title:
        #     return False
        
        # Ignore cloaked windows (UWP / modern app hidden windows)
        if is_window_cloaked(hwnd):
            # print("is cloaked")
            return False
        
        # Check process name to filter shell / system processes
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc_name = psutil.Process(pid).name().lower()
        if proc_name in {"explorer.exe", "taskhostw.exe", "ctfmon.exe"}:
            # print("name is dumb")
            return False
        
        if win32gui.GetWindow(hwnd, win32con.GW_OWNER) != 0:
            # print("no GW OWNER")
            return False
        
        # System classes to ignore
        cls = win32gui.GetClassName(hwnd)
        if cls in {
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "Shell_SecondaryTrayWnd",
            "SystemTray_Main",
        }:
            # print("weird classname")
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

def ranges_overlap(a1, a2, b1, b2):
    return a1 <= b2 and b1 <= a2



# -----------------------
# Overlay Widget
# -----------------------
class WindowsOverlay(QWidget):
    def __init__(self, pet):
        super().__init__()

        self.pet = pet

        self.update_hitbox(pet.hitbox_width, pet.hitbox_height)

        self.primary_screen = QApplication.primaryScreen()
        screen = QApplication.primaryScreen() # Screen detection
        self.screen_geom = screen.geometry()
        self.screen_avail_geom = screen.availableGeometry()

        self.taskbar_top = self.screen_avail_geom.bottom() + 1

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
        self.surfaces = {
            "top": [],     # floors
            "bottom": [],  # ceilings
            "left": [],    # right walls
            "right": []    # left walls
        }

        # Hook all top-level window events
        user32 = ctypes.windll.user32

        
    def update_hitbox(self, new_hitbox_w, new_hitbox_h):
        self.hitbox_w = new_hitbox_w
        self.hitbox_h = new_hitbox_h

    def update_window_list(self):
        update_active_apps()
        self.windows = get_windows_in_zorder(excluded_hwnd=self.excluded_hwnd)
        if DEBUG:
            print(f"[enum] found {len(self.windows)} windows")

    def update_frame(self):
        # update rects for current cached windows
        rects = {}

        t1 = time.perf_counter()

        # appending taskbar as a rect for collisions
        rects["taskbar"] = (
            self.screen_geom.left(),
            self.screen_avail_geom.bottom() + 1,
            self.screen_geom.right(),
            self.screen_geom.bottom()
        )

        for hwnd in self.windows:
            scale = get_window_dpi_scale(hwnd=hwnd) # this is probably to remove or move up, its getting dpi per window
            if scale <= 0:
                scale = 1.0
            
            try:
                rect = get_extended_frame_bounds(hwnd)
                if not rect: return

                rects[hwnd] = (rect[0]/scale, rect[1]/scale, rect[2]/scale, rect[3]/scale) # getting real scaled values for positions
            except Exception:
                pass
    
        t2 = time.perf_counter()
        # print(f"Time for getting rects: {t2 - t1}")

        self.rects = rects

        # recompute clipped border segments in physical pixels
        segs = compute_visible_segments(self.windows, self.rects)

        self.segments = segs

        self.rebuild_surfaces(segs)

        t3 = time.perf_counter()
        # print(f"Time for computing visible segments: {t3 - t2}")
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


    def rebuild_surfaces(self, segs):
        # clearing surfaces before appending
        for k in self.surfaces:
            self.surfaces[k].clear()

        # appending found surfaces
        for hwnd, data in segs.items():

            L, T, R, B = data["rect"]

            for x1, x2 in data["top"]:
                self.surfaces["top"].append((T, x1, x2, hwnd))

            for x1, x2 in data["bottom"]:
                self.surfaces["bottom"].append((B, x1, x2, hwnd))

            for y1, y2 in data["left"]:
                self.surfaces["left"].append((L, y1, y2, hwnd))

            for y1, y2 in data["right"]:
                self.surfaces["right"].append((R, y1, y2, hwnd))

# --- Update position of the top active window ---
    def update_active_window(self, hwnd):
        scale = get_window_dpi_scale(hwnd=hwnd) # this is probably to remove or move up, its getting dpi per window
        if scale <= 0:
            scale = 1.0

        rect = get_extended_frame_bounds(hwnd)
        if not rect: return

        rect = (rect[0]/scale, rect[1]/scale, rect[2]/scale, rect[3]/scale) # getting real scaled values for positions
        
# --- Movement collision stuff ---
    def bounds(self, pos_x, pos_y):
        hw = self.hitbox_w / 4
        hh = self.hitbox_h / 2
    
        return (
            pos_x - hw,
            pos_y - hh,
            pos_x + hw,
            pos_y + hh
        )

    def collide_vertical(self, pos_x, pos_y, dy):
        L,T,R,B = self.bounds(pos_x, pos_y)

        best = dy
        surface_data = None
        collision = False

        surfaces = self.surfaces

        if dy > 0:  # falling

            for y, x1, x2, hwnd in surfaces["top"]:

                if R < x1 or L > x2:
                    continue

                dist = y - B

                if 0 <= dist < best:
                    best = dist
                    collision = True
                    surface_data = (hwnd, y, x1, x2)
                    # print(y, x1, x2)

        elif dy < 0:  # jumping

            for y, x1, x2, hwnd in surfaces["bottom"]:

                if R < x1 or L > x2:
                    continue

                dist = y - T

                if best < dist < 0:
                    best = dist
                    collision = True
                    surface_data = (hwnd, y, x1, x2)
                    # print(y, x1, x2)

        # print(dy, best, collision)
        return best, collision, surface_data

    def collide_horizontal(self, pos_x, pos_y, dx):

        L,T,R,B = self.bounds(pos_x, pos_y)

        best = dx
        surface_data = None
        collision = False

        surfaces = self.surfaces

        if dx > 0:  # moving right

            for x, y1, y2, hwnd in surfaces["left"]:

                if B < y1 or T > y2:
                    continue

                dist = x - R

                if 0 <= dist < best:
                    best = dist
                    collision = True
                    surface_data = (hwnd, x, y1, y2)

        elif dx < 0:  # moving left

            for x, y1, y2, hwnd in surfaces["right"]:

                if B < y1 or T > y2:
                    continue

                dist = x - L

                if best < dist <= 0:
                    best = dist
                    collision = True
                    surface_data = (hwnd, x, y1, y2)

        return best, collision, surface_data

# --- Find nearest surface in a given direction ---
    def get_nearest_surface(self, direction, hitbox_w, hitbox_h):

        px, py = self.pet.anchor.x, self.pet.anchor.y

        pet_left  = px - hitbox_w / 4
        pet_right = px + hitbox_w / 4
        pet_top   = py - hitbox_h / 2
        pet_bot   = py + hitbox_h / 2

        best_dist = float("inf")
        best_surface = None

        segments = self.segments

        for hwnd, data in segments.items():
            L, T, R, B = data["rect"]

            if direction == "down":

                for x1, x2 in data["top"]:
                    if ranges_overlap(pet_left, pet_right, x1, x2):

                        dist = T - pet_bot
                        if 0 <= dist < best_dist:
                            best_dist = dist
                            best_surface = T

            elif direction == "up":

                for x1, x2 in data["bottom"]:
                    if ranges_overlap(pet_left, pet_right, x1, x2):

                        dist = pet_top - B
                        if 0 <= dist < best_dist:
                            best_dist = dist
                            best_surface = B

            elif direction == "right":

                for y1, y2 in data["left"]:
                    if ranges_overlap(pet_top, pet_bot, y1, y2):

                        dist = L - pet_right
                        if 0 <= dist < best_dist:
                            best_dist = dist
                            best_surface = L

            elif direction == "left":

                for y1, y2 in data["right"]:
                    if ranges_overlap(pet_top, pet_bot, y1, y2):

                        dist = pet_left - R
                        if 0 <= dist < best_dist:
                            best_dist = dist
                            best_surface = R

        return best_surface
    

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
