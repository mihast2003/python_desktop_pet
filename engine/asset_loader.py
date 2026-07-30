import sys, os, random, time, math
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor

from OpenGL.GL import * #type: ignore

class AssetLoader:

    @staticmethod
    def load_QPixmap_frames(folder):  # function for loading frames, recieves a string path to a folder, returns a list of png files( converted to PixMap ) in name order
        """
        Returns a list of QPixmap files taken from .png files from the provided folder.
        
        :param folder: Path to the folder. (not from base)
        """
        frames = []

        files = sorted(                # get the png files
        f for f in os.listdir(folder)
        if f.lower().endswith((".png", ".webp"))
        )

        for i, filename in enumerate(files):
            pix = QPixmap(os.path.join(folder, filename))

            if pix.isNull():
                raise ValueError("Could not load Pixmap, for file", filename)

            frames.append(pix)

        return frames
    

    @staticmethod
    def load_openGL_texture(path):
        """
        Returns a openGL texture file taken from a path.
        
        :param folder: Path to the texture. (not from base)
        """
        from PIL import Image
        import os

        # base_dir = os.path.dirname(os.path.abspath(__file__))
        # full_path = os.path.join(base_dir, path)

        img = Image.open(path).convert("RGBA")
        img_data = img.tobytes("raw", "RGBA", 0, -1)

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            img.width,
            img.height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            img_data
        )

        glBindTexture(GL_TEXTURE_2D, 0)

        return tex_id