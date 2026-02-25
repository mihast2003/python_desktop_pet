import sys
import ctypes
import time
import win32gui
import win32con
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QApplication, QWidget

# Debug toggle: set True to print windows / segments info
DEBUG = False

# -----------------------
# DPI helper (robust)
# -----------------------
user32 = ctypes.windll.user32
# best-effort: if GetDpiForWindow exists use it
try:
    user32.GetDpiForWindow.restype = ctypes.c_uint
    _has_getdpiforwindow = True
except Exception:
    _has_getdpiforwindow = False


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
# Window enumeration (expensive)
# -----------------------
def get_windows_in_zorder(excluded_hwnd):
    """
    Return list of top-level window HWNDs in Z-order top-first, skipping excluded_hwnd.
    Use GetForegroundWindow -> GetWindow(GW_HWNDFIRST) as starting point.
    """
    try:
        fg = win32gui.GetForegroundWindow()
        start = win32gui.GetWindow(fg, win32con.GW_HWNDFIRST)
    except Exception:
        # fallback: desktop window
        start = win32gui.GetWindow(win32gui.GetDesktopWindow(), win32con.GW_HWNDFIRST)

    windows = []
    hwnd = start
    while hwnd:
        if hwnd != excluded_hwnd and win32gui.IsWindow(hwnd):
            # accept visible windows; don't require non-empty title (some apps use empty title)
            if win32gui.IsWindowVisible(hwnd):
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                    if rect and (rect[0] != rect[2] and rect[1] != rect[3]):
                        windows.append(hwnd)
                except Exception:
                    pass
        hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
    return windows


# -----------------------
# Compute visible border segments (physical pixels)
# -----------------------
def compute_visible_segments(windows, rects):
    """
    windows: list of HWND top-first (topmost first)
    rects: dict hwnd->(L,T,R,B) physical pixels for the same windows (may be subset)
    returns dict hwnd->{"rect":..., "top":[(x1,x2)],...}
    """
    segs = {}

    # For easier "windows above" logic convert to bottom-first
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

        # windows above this: those later in list (higher visual stacking)
        for above in windows_bottom_first[idx + 1:]:
            ar = rects.get(above)
            if not ar:
                continue
            inter = intersect_rect(rect, ar)
            if not inter:
                continue
            x1, y1, x2, y2 = inter
            # top border coverage
            if y1 <= T <= y2:
                cuts_top.append((x1, x2))
            # bottom border coverage
            if y1 <= B <= y2:
                cuts_bottom.append((x1, x2))
            # left border coverage
            if x1 <= L <= x2:
                cuts_left.append((y1, y2))
            # right border coverage
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


# -----------------------
# Overlay Widget
# -----------------------
class BorderOverlay(QWidget):
    def __init__(self):
        super().__init__()

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
        self.my_hwnd = int(self.winId())

        # cached data
        self.windows = []   # top-first
        self.rects = {}     # hwnd -> rect physical
        self.segments = {}  # hwnd -> clipped segments computed in physical pixels

        # timers
        # enumerate windows once per second
        self.enum_timer = QTimer()
        self.enum_timer.timeout.connect(self._update_window_list)
        self.enum_timer.start(1000)

        # update positions + recompute clipping every frame (16ms)
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self._update_frame)
        self.frame_timer.start(16)

        # initial population
        self._update_window_list()
        self._update_frame()

    # expensive: run once/sec
    def _update_window_list(self):
        self.windows = get_windows_in_zorder(self.my_hwnd)
        if DEBUG:
            print(f"[enum] found {len(self.windows)} windows")

    # cheap: run each frame (16ms)
    def _update_frame(self):
        # update rects for current cached windows
        rects = {}
        for hwnd in self.windows:
            try:
                r = win32gui.GetWindowRect(hwnd)
                # sanity check
                if r and (r[0] != r[2] and r[1] != r[3]):
                    rects[hwnd] = r
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # type: ignore

        # pen width is in logical pixels; color alpha for nice appearance
        pen = QPen(QColor(0, 200, 60, 220), 3)
        painter.setPen(pen)

        # draw every cached segment using per-window DPI scale conversion
        for hwnd, data in list(self.segments.items()):
            rect = data["rect"]
            if not rect:
                continue
            L, T, R, B = rect

            scale = get_window_dpi_scale(hwnd)
            if scale <= 0:
                scale = 1.0

            # scaled coords (logical)
            dL = int(round(L / scale))
            dT = int(round(T / scale))
            dR = int(round(R / scale))
            dB = int(round(B / scale))

            # top
            for x1, x2 in data["top"]:
                sx1 = int(round(x1 / scale))
                sx2 = int(round(x2 / scale))
                painter.drawLine(sx1, dT, sx2, dT)

            # bottom
            for x1, x2 in data["bottom"]:
                sx1 = int(round(x1 / scale))
                sx2 = int(round(x2 / scale))
                painter.drawLine(sx1, dB, sx2, dB)

            # left
            for y1, y2 in data["left"]:
                sy1 = int(round(y1 / scale))
                sy2 = int(round(y2 / scale))
                painter.drawLine(dL, sy1, dL, sy2)

            # right
            for y1, y2 in data["right"]:
                sy1 = int(round(y1 / scale))
                sy2 = int(round(y2 / scale))
                painter.drawLine(dR, sy1, dR, sy2)

        painter.end()


# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = BorderOverlay()
    sys.exit(app.exec())
