from time import sleep

import pyautogui
import numpy as np
import cv2

from screen import Screen, Point, BoundingBox
from util import find_center_of_contour, find_colored_contours, find_white_contours

class Sequence():
    def __init__(self):
        self._bounding_box = BoundingBox(250, 900, 400, 350)
        self._screen = Screen(bounding_box=self._bounding_box)
        self._scale = 2

    def relative_point(self, point):
        return Point(
            self._bounding_box.left + (point.x/2),
            self._bounding_box.top + (point.y/2)
        )

    def play(self, goal) -> None:
        centers = []
        started = False

        # Align window with start button
        self._screen.find_window(BoundingBox(315, 480, 165, 75))

        # Find the orange start button and click
        for image in self._screen.capture():
            contours = find_colored_contours(image, np.array([0,111,136]), np.array([59,190,255]))
            if not started and contours:
                print("Starting")
                center = find_center_of_contour(contours[0])
                sleep(2)
                relative = self.relative_point(center)
                pyautogui.click(relative.x, relative.y)
                sleep(0.2)
                break

        for target in range(1, goal + 1):
            centers = []
            print(f"Waiting for {target}")
            for image in self._screen.capture():
                contours = find_white_contours(image)
                if len(contours) not in {1, 2}:
                    continue

                last_center = None if len(centers) == 0 else centers[-1]
                if len(contours) == 1:
                    contour = contours[0]
                    if find_center_of_contour(contour) == last_center:
                        continue
                else:
                    contour = next(c for c in contours if find_center_of_contour(c) != last_center)

                centers.append(find_center_of_contour(contour))
                if len(centers) == target:
                    break

            print("Found targets")
            sleep(1)

            for center in centers:
                relative = self.relative_point(center)
                pyautogui.click(relative.x, relative.y)
                sleep(0.05)


if __name__ == "__main__":
    sequence = Sequence()
    sequence.play(200)