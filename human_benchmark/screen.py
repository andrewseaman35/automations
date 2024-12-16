from dataclasses import dataclass

import numpy as np
import cv2
from mss import mss


sct = mss()

@dataclass
class BoundingBox():
    top: int
    left: int
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            'top': self.top,
            'left': self.left,
            'width': self.width,
            'height': self.height,
        }

@dataclass
class Point():
    x: int
    y: int

class Screen():
    def __init__(self, bounding_box: BoundingBox) -> None:
        self._bounding_box = bounding_box

    def find_window(self, alignment_rec: BoundingBox | None):
        print("Finding window")
        while True:
            image = np.array(sct.grab(self._bounding_box.to_dict()))

            if (alignment_rec):
                cv2.rectangle(image,
                              (alignment_rec.top, alignment_rec.left),
                              (alignment_rec.top + alignment_rec.width, alignment_rec.left + alignment_rec.height),
                              (0, 0, 255),
                              2
                            )
            cv2.imshow("screen", image)
            if (cv2.waitKey(33)) == ord('a'):
                cv2.destroyAllWindows()
                break

    def single(self):
        sct_image = sct.grab(self._bounding_box.to_dict())
        return np.array(sct_image)

    def capture(self):
        while True:
            sct_image = sct.grab(self._bounding_box.to_dict())
            yield np.array(sct_image)
