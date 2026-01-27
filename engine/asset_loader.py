import sys, os, random, time, math
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor

class AssetLoader:

    @staticmethod
    def load_frames(folder):  # function for loading frames, recieves a string path to a folder, returns a list of png files( converted to PixMap ) in name order
        frames = []

        files = sorted(                # get the png files
        f for f in os.listdir(folder)
        if f.lower().endswith(".png")
        )

        for i, filename in enumerate(files):
            pix = QPixmap(os.path.join(folder, filename))

            frames.append(pix)

        return frames