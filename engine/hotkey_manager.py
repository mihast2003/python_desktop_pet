import win32gui
import win32con
from PySide6.QtCore import QTimer

HOTKEY_ID = 1


class HotkeyManager:
    def __init__(self, pet):
        self.pet = pet

        success = win32gui.RegisterHotKey(
            None,
            HOTKEY_ID,
            win32con.MOD_CONTROL | win32con.MOD_SHIFT,
            win32con.VK_F9
        )

        print("hotkey registered", success)


    def messagag(self):
        while True:
            msg = win32gui.PeekMessage(None, 0, 0, win32con.PM_REMOVE) # type: ignore

            if msg:
                if msg[1][1] == win32con.WM_HOTKEY:
                    print("works")
                    self.handle()

    def handle(self):
        print("HOTKEY FIRED")
        # self.pet.debug_dump()