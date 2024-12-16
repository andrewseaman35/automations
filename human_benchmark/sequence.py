from time import sleep

import pyautogui
import numpy as np
import cv2

from screen import Screen, Point, BoundingBox

class Sequence():
    def __init__(self):
        self._bounding_box = BoundingBox(250, 900, 400, 350)
        self._screen = Screen(bounding_box=self._bounding_box)
        self._scale = 2

    def find_white_contours(self, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        sensitivity = 15
        lower_white = np.array([0,0,255-sensitivity])
        upper_white = np.array([255,sensitivity,255])

        mask = cv2.inRange(hsv, lower_white, upper_white)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        return contours

    def find_colored_contours(self, image, lower, upper):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(hsv, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        return contours

    def find_center_of_contour(self, contour):
        x, y, w, h = cv2.boundingRect(contour)
        center = Point(int(x+(w/2)), int(y+h/2))
        return center

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

        for image in self._screen.capture():

            # Find the orange start button
            contours = self.find_colored_contours(image, np.array([0,111,136]), np.array([59,190,255]))

            if not started and contours:
                print("Starting")
                center = self.find_center_of_contour(contours[0])
                sleep(2)
                pyautogui.click(self._bounding_box.left + (center.x/2), self._bounding_box.top + (center.y/2))
                sleep(0.2)
                break

        for target in range(1, goal + 1):
            centers = []
            print(f"Waiting for {target}")
            for image in self._screen.capture():
                contours = self.find_white_contours(image)
                if len(contours) not in {1, 2}:
                    continue

                last_center = None if len(centers) == 0 else centers[-1]
                if len(contours) == 1:
                    contour = contours[0]
                    if self.find_center_of_contour(contour) == last_center:
                        continue
                else:
                    contour = next(c for c in contours if self.find_center_of_contour(c) != last_center)

                centers.append(self.find_center_of_contour(contour))
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