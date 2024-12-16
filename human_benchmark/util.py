import numpy as np
import cv2

from screen import Point


def find_white_contours(image, sensitivity=15):
    lower_white = np.array([0,0,255-sensitivity])
    upper_white = np.array([255,sensitivity,255])
    return find_colored_contours(image, lower_white, upper_white)

def find_colored_contours(image, lower, upper):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, lower, upper)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    return contours

def find_center_of_contour(contour):
    x, y, w, h = cv2.boundingRect(contour)
    center = Point(int(x+(w/2)), int(y+h/2))
    return center

def hsv_has_color(hsv, lower, upper, threshold):
    thresh = cv2.inRange(hsv, lower, upper)
    count = np.sum(np.nonzero(thresh))
    return count > threshold