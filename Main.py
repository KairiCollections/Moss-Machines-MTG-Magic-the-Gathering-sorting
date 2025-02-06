#Imports
import cv2
import logging
import serial
import sys
import time
from collections import Counter
from PIL import Image
from ultralytics import YOLO
from cards import extract_card_info, CARD_DATA_BY_ID
from config import CROP_SIZE, SORTING_MODES, EXCLUDED_SETS, SERIAL_PORT, BAUD_RATE, START_MARKER, END_MARKER, MAX_ATTEMPTS_NAME, TIMEOUT_NAME, MODEL_PATH
from detection import find_card_contour, get_perspective_corrected_card
from detectname import find_text, compare_strings
from hashing import hash_image_color, compute_distances_for_image
from InventoryTracker import CheckInventory
from sorting import print_sorting_options, draw_info_as_json, get_bin_number, get_mana_cost, get_name

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("ultralytics").setLevel(logging.WARNING)

def init_serial():
    global ser
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
    print(f"Serial port {SERIAL_PORT} opened. Baudrate {BAUD_RATE}.")
    wait_for_arduino()

def send_to_arduino(send_str):
    if send_str:
        ser.write(send_str.encode('utf-8'))
        wait_for_arduino()

def recv_from_arduino():
    ck = ""
    x = "z"
    while ord(x) != START_MARKER:
        x = ser.read()
    while ord(x) != END_MARKER:
        if ord(x) != START_MARKER:
            ck += x.decode("utf-8")
        x = ser.read()
    return ck

def wait_for_arduino():
    msg = ""
    while "Arduino is ready" not in msg:
        while ser.in_waiting == 0:
            pass
        msg = recv_from_arduino()
        print(msg)

def load_model(model_path):
    try:
        model = YOLO(model_path)
        print("Model loaded successfully.")
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

def get_detections(model, frame):
    results = model(frame)
    detections = [(box.xyxy[0][0].item(), results[0].names[int(box.cls.item())], box.conf.item())
                  for box in results[0].boxes]
    detections.sort(key=lambda x: x[0])
    annotated_frame = results[0].plot()
    cv2.imshow("YOLOv11 Mana", annotated_frame)
    return detections

def preprocess_detections(detections):
    cost = "".join(label.replace("_", "") for _, label, _ in detections)
    for color in ["hite", "lue", "lack", "ed", "reen"]:
        cost = cost.replace(color, "")
    return cost

def handle_unrecognized_card(display_frame, card_approx, reason="Unknown"):
    cv2.drawContours(display_frame, [card_approx], -1, (0, 0, 255), 2)
    cv2.putText(display_frame, "Unrecognized Card", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(display_frame, f"Reason: {reason}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(display_frame, "Bin: 33", (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.imshow("Detected Card", display_frame)
    cv2.imshow("YOLOv11 Mana", display_frame)
    logger.info(f"Card unrecognized: {reason}")
    send_to_arduino("RejectCard")

def handle_recognized_card(display_frame, chosen_info, current_sorting_mode, threshold, res, choice2, name2):
    draw_info_as_json(display_frame, chosen_info, start_x=10, start_y=30, line_height=20)
    if choice2 == "Y":
        chosen_info = CheckInventory(chosen_info)
    manacost = get_mana_cost(chosen_info)
    name = get_name(chosen_info)
    similarity = 0.0
    similarity = compare_strings(name,name2)
    print(manacost)
    card_result = get_bin_number(chosen_info, current_sorting_mode, threshold)
    cv2.putText(display_frame, f"Bin: {card_result}", (10, 200),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Detected Card", display_frame)
    cv2.imshow("YOLOv11 Mana", display_frame)
    if (manacost == res and similarity >= 0.5) or similarity >= 0.8:
        print(f"Similarity: {similarity} Name: {name}")
        print("Mana cost check or similarity was good, forwarding to Arduino.")
        time.sleep(1)
        send_to_arduino(card_result)
    else:
        print(f"{manacost} and {res} do not match" if manacost != res else "")
        print(f"{name} and {name2} similarity score was too low" if similarity < 0.5 else "")
    logger.info(f"Card recognized: {name} (Mana: {manacost}, Similarity: {similarity}), Bin: {card_result}") # Use logging

def process_card_approx(frame, card_approx, res, current_sorting_mode, threshold, choice2):
    warped = get_perspective_corrected_card(frame, card_approx)
    cropped_upright = warped[:CROP_SIZE, :CROP_SIZE]
    img_pil_upright = Image.fromarray(cv2.cvtColor(cropped_upright, cv2.COLOR_BGR2RGB))
    rotated180 = cv2.rotate(warped, cv2.ROTATE_180)
    cropped_rotated = rotated180[:CROP_SIZE, :CROP_SIZE]
    img_pil_rotated = Image.fromarray(cv2.cvtColor(cropped_rotated, cv2.COLOR_BGR2RGB))
    upright_id, upright_dist = hash_image_color(img_pil_upright, hash_size=16)
    rotated_id, rotated_dist = hash_image_color(img_pil_rotated, hash_size=16)
    all_distances = compute_distances_for_image(img_pil_upright, hash_size=16)
    allowed_distances = [(cid, dist) for cid, dist in all_distances
                         if CARD_DATA_BY_ID.get(cid, {}).get('set', '').lower() not in EXCLUDED_SETS]
    allowed_distances.sort(key=lambda x: x[1])
    if allowed_distances:
        chosen_id = allowed_distances[0][0]
        chosen_info = extract_card_info(chosen_id)
        return chosen_id, chosen_info
    return None, None

def detect_card_name(frame, card_approx):
    namearray = []
    attempts = 0
    start_time = time.time()
    while len(namearray) < 15 and attempts < MAX_ATTEMPTS_NAME and time.time() - start_time < TIMEOUT_NAME:
        time.sleep(0.1)
        text_found = find_text(frame, card_approx)
        attempts += 1
        if text_found:
            namearray.append(text_found)
    if len(namearray) < 5:
        logger.warning("Could not find enough names.")
        return None
    else:
        text_counts = Counter(namearray)
        name = text_counts.most_common(1)[0][0]
        return name

def main():
    init_serial()
    print_sorting_options()
    choice = input("Enter the number of the sorting method: ").strip()
    choice2 = input("Track inventory? (Y/N): ").strip() if choice in ["3", "6"] else "N"
    current_sorting_mode = SORTING_MODES.get(choice, "color")
    threshold = input("Enter a price threshold: ").strip() if current_sorting_mode == "buy" else 1000000
    model, cap = load_model(MODEL_PATH), cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Cannot open webcam.")
        sys.exit(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to grab frame.")
            break
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        display_frame = frame.copy()
        cv2.imshow("Detected Card", display_frame)
        detections = get_detections(model, frame)
        res = preprocess_detections(detections)
        card_approx = find_card_contour(frame)

        if card_approx is not None:
            name = detect_card_name(frame, card_approx)
            if name is None:
                handle_unrecognized_card(display_frame, card_approx, reason="Name not found")
            else:
                chosen_id, chosen_info = process_card_approx(frame, card_approx, res, current_sorting_mode, threshold, choice2)
                if chosen_info:
                    handle_recognized_card(display_frame, chosen_info, current_sorting_mode, threshold, res, choice2, name)
                else:
                    handle_unrecognized_card(display_frame, card_approx, reason="Card data not found")
        else:
            logger.info("No card detected.")
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()