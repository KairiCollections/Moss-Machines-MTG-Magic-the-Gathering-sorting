import cv2
import numpy as np
from config import WIDTH, HEIGHT

def find_card_contour(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_contour = None
    max_area = 0
    for contour in contours:
        approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > 10000 and area > max_area:
                max_area = area
                best_contour = approx
    return best_contour

def get_perspective_corrected_card(frame, contour):
    pts = contour.reshape(4, 2)
    pts = sorted(pts, key=lambda point: point[1])
    top_two, bottom_two = pts[:2], pts[2:]
    top_left, top_right = sorted(top_two, key=lambda point: point[0])
    bottom_left, bottom_right = sorted(bottom_two, key=lambda point: point[0])
    ordered_pts = np.array([top_left, top_right, bottom_right, bottom_left], dtype="float32")
    dst = np.array([[0, 0], [WIDTH - 1, 0], [WIDTH - 1, HEIGHT - 1], [0, HEIGHT - 1]], dtype="float32")
    matrix = cv2.getPerspectiveTransform(ordered_pts, dst)
    warped = cv2.warpPerspective(frame, matrix, (WIDTH, HEIGHT))
    height, width, _ = warped.shape
    if width > height:
        for _ in range(3):
            warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
            height, width, _ = warped.shape
            if width <= height:
                break
    return warped

def contours_are_similar(contour1, contour2, tolerance=0.01):
    x1, y1, w1, h1 = cv2.boundingRect(contour1)
    x2, y2, w2, h2 = cv2.boundingRect(contour2)
    area1 = w1 * h1
    area2 = w2 * h2
    area_diff_ratio = abs(area1 - area2) / (area1 + 1)
    return area_diff_ratio < tolerance
