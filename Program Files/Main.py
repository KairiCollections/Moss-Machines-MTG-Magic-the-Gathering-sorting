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
from config import CROP_SIZE, SORTING_MODES, EXCLUDED_SETS, SERIAL_PORT, BAUD_RATE, START_MARKER, END_MARKER, MAX_ATTEMPTS_NAME, TIMEOUT_NAME
from detection import find_card_contour, get_perspective_corrected_card
from detectname import find_text, compare_strings
from hashing import hash_image_color, compute_distances_for_image
from InventoryTracker import CheckInventory
from sorting import print_sorting_options, draw_info_as_json, get_bin_number, get_name

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

def handle_unrecognized_card(display_frame, card_approx, reason="Unknown"):
    start_time = time.time()
    cv2.drawContours(display_frame, [card_approx], -1, (0, 0, 255), 2)
    cv2.putText(display_frame, "Unrecognized Card", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(display_frame, f"Reason: {reason}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(display_frame, "Bin: 33", (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.imshow("Detected Card", display_frame)
    logger.info(f"Card unrecognized: {reason} | Processing time: {time.time() - start_time:.3f}s")
    #send_to_arduino("RejectCard")

def handle_recognized_card(display_frame, chosen_info, current_sorting_mode, threshold, choice2, name2):
    start_time = time.time()
    draw_info_as_json(display_frame, chosen_info, start_x=10, start_y=30, line_height=20)
    if choice2 == "Y":
        chosen_info = CheckInventory(chosen_info)
    name = get_name(chosen_info)
    similarity = 0.0
    similarity = compare_strings(name,name2)
    card_result = get_bin_number(chosen_info, current_sorting_mode, threshold)
    cv2.putText(display_frame, f"Bin: {card_result}", (10, 200),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Detected Card", display_frame)
    if similarity >= 0.6:
        print(f"Similarity: {similarity} Name: {name} and Name2:{name2} and Similarity: {similarity})")
        print("Similarity was good, forwarding to Arduino.")
        time.sleep(0.1)
        #send_to_arduino(card_result)
    else:
        print(f"Similarity: {similarity} Name: {name} and Name2:{name2} and Similarity: {similarity})")
        print("Similarity was too low")
    logger.info(f"Card recognized | Total processing time: {time.time() - start_time:.3f}s")

def process_card_approx(frame, card_approx, current_sorting_mode, threshold, choice2):
    start_time = time.time()
    warped = get_perspective_corrected_card(frame, card_approx)
    warp_time = time.time()
    cropped_upright = warped[:CROP_SIZE, :CROP_SIZE]
    img_pil_upright = Image.fromarray(cv2.cvtColor(cropped_upright, cv2.COLOR_BGR2RGB))
    rotated180 = cv2.rotate(warped, cv2.ROTATE_180)
    cropped_rotated = rotated180[:CROP_SIZE, :CROP_SIZE]
    img_pil_rotated = Image.fromarray(cv2.cvtColor(cropped_rotated, cv2.COLOR_BGR2RGB))
    crop_rotate_time = time.time()
    
    upright_id, upright_dist = hash_image_color(img_pil_upright, hash_size=16)
    rotated_id, rotated_dist = hash_image_color(img_pil_rotated, hash_size=16)
    hash_time = time.time()
    
    all_distances = compute_distances_for_image(img_pil_upright, hash_size=16)
    distance_time = time.time()
    
    allowed_distances = [(cid, dist) for cid, dist in all_distances
                         if CARD_DATA_BY_ID.get(cid, {}).get('set', '').lower() not in EXCLUDED_SETS]
    allowed_distances.sort(key=lambda x: x[1])
    sort_time = time.time()
    
    logger.info(f"Card processing times - Warp: {warp_time-start_time:.3f}s, Crop/Rotate: {crop_rotate_time-warp_time:.3f}s, "
                f"Hashing: {hash_time-crop_rotate_time:.3f}s, Distance: {distance_time-hash_time:.3f}s, "
                f"Sort: {sort_time-distance_time:.3f}s, Total: {sort_time-start_time:.3f}s")
    
    if allowed_distances:
        chosen_id = allowed_distances[0][0]
        chosen_info = extract_card_info(chosen_id)
        return chosen_id, chosen_info
    return None, None

def detect_card_name(frame, card_approx):
    start_time = time.time()
    namearray = []
    attempts = 0
    start_time_outer = time.time()
    while len(namearray) < 2 and attempts < MAX_ATTEMPTS_NAME and time.time() - start_time_outer < TIMEOUT_NAME:
        attempt_start = time.time()
        time.sleep(0.1)
        text_found = find_text(frame, card_approx)
        attempts += 1
        if text_found:
            namearray.append(text_found)
        logger.debug(f"Name detection attempt {attempts} took {time.time() - attempt_start:.3f}s")
    
    if len(namearray) < 1:
        logger.warning(f"Could not find name. Total time: {time.time() - start_time_outer:.3f}s")
        return None
    else:
        text_counts = Counter(namearray)
        name = text_counts.most_common(1)[0][0]
        logger.info(f"Name detection completed in {time.time() - start_time:.3f}s | "
                   f"Total attempts: {attempts} | Best name: {name}")
        return name

def main():
    # Initialize serial, sorting options, etc.
    # init_serial()
    print_sorting_options()
    choice = input("Enter the number of the sorting method: ").strip()
    choice2 = input("Track inventory (Option unfinished)? (Y/N): ").strip() if choice in ["3", "6"] else "N"
    current_sorting_mode = SORTING_MODES.get(choice, "color")
    threshold = input("Enter a price threshold: ").strip() if current_sorting_mode == "buy" else 1000000
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Cannot open webcam.")
        sys.exit(1)

    frame_count = 0
    total_processing_time = 0
    
    while True:
        frame_start = time.time()
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to grab frame.")
            break

        # Show the original camera feed in a window
        cv2.imshow("Camera Feed", frame)

        # Find card contour in the current frame
        card_approx = find_card_contour(frame)

        # Always display the current frame with overlays
        display_frame = frame.copy()

        if card_approx is not None:
            # Detect card name in the current frame
            name = detect_card_name(frame, card_approx)

            if name is None:
                handle_unrecognized_card(display_frame, card_approx, reason="Name not found")
            else:
                # Process the card approximation for recognition
                chosen_id, chosen_info = process_card_approx(frame, card_approx, current_sorting_mode, threshold, choice2)
                if chosen_info:
                    handle_recognized_card(display_frame, chosen_info, current_sorting_mode, threshold, choice2, name)
                else:
                    handle_unrecognized_card(display_frame, card_approx, reason="Card data not found")
            
            # Show the detection result with overlays
            cv2.imshow("Detected Card", display_frame)
        else:
            # If no card found, just show the original frame
            cv2.imshow("Detected Card", display_frame)

        # Frame timing and stats
        frame_count += 1
        total_processing_time += time.time() - frame_start
        avg_time = total_processing_time / frame_count if frame_count > 0 else 0
        logger.info(f"Frame {frame_count} processed in {time.time() - frame_start:.3f}s | "
                    f"Avg frame time: {avg_time:.3f}s")

        # Exit condition
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
