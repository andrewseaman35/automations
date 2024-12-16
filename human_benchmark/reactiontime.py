from time import sleep

import pyautogui
import numpy as np
import cv2

from screen import Screen, Point, BoundingBox

from util import hsv_has_color

# BLUE = rgb(43, 135, 209)
BLUE_LOWER = np.array([48, 158, 164])
BLUE_UPPER = np.array([210, 255, 244])


# GREEN = rgb(75, 219, 106)
GREEN_LOWER = np.array([33, 128, 206])
GREEN_UPPER = np.array([191, 255, 244])

# RED = rgb(206, 38, 54)
RED_LOWER = np.array([0, 176, 145])
RED_UPPER = np.array([69, 202, 221])

class ReactionTime():
    def __init__(self):
        self._bounding_box = BoundingBox(250, 900, 100, 100)
        self._screen = Screen(bounding_box=self._bounding_box)
        self._scale = 2

    def relative_point(self, point):
        return Point(
            self._bounding_box.left + (point.x/2),
            self._bounding_box.top + (point.y/2)
        )

    def play(self):
        self._screen.find_window(BoundingBox(315, 480, 165, 75))
        click_point = self.relative_point(Point(50, 50))

        for image in self._screen.capture():
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            if hsv_has_color(hsv, GREEN_LOWER, GREEN_UPPER, 5000000):
                pyautogui.click(click_point.x, click_point.y)
                sleep(3)
            elif hsv_has_color(hsv, RED_LOWER, RED_UPPER, 5000000):
                continue
            elif hsv_has_color(hsv, BLUE_LOWER, BLUE_UPPER, 5000000):
                sleep(1)
                pyautogui.click(click_point.x, click_point.y)


ReactionTime().play()