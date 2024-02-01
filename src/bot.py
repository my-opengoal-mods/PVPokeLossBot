import os
import sys
import time
import cv2
import logging

from src import image_service
from src import screenshot
from src.adb_commands import send_adb_tap, turn_screen_off


def is_ingame(image_file: str) -> bool:
    return image_file.startswith("ingame_") or image_file == "enemy_charge_attack.png"


def load_image_templates():
    image_dir = "./images"
    template_images = {}
    images = os.listdir(image_dir)
    for image in images:
        if image.endswith(".png"):
            img_template = cv2.imread(os.path.join(image_dir, image), cv2.IMREAD_COLOR)
            template_images[image] = img_template
    logging.info(f"Loaded {len(template_images)} image templates.")
    return template_images


def run():
    # Time the bot will stay in game until it forfeits
    time_to_stay_in_game = 5

    # Start the timer until bot forfeits the game
    start_time = time.time()

    template_images = load_image_templates()

    game_entered = False
    waiting_for_device = False

    while True:
        # Capture a screenshot and save it to a file
        if not screenshot.capture_screenshot("screenshot.png"):
            if waiting_for_device:
                print(".", end="", flush=True)
            else:
                logging.info(
                    "Error capturing screenshot. Waiting until phone is connected."
                )
                waiting_for_device = True

            # sys.exit(1)
            time.sleep(5)
            continue

        if waiting_for_device:
            waiting_for_device = False
            # print to jump to the next line after only printing ...... without jumping to next line
            print()

        # Check if the timer has run out
        elapsed_time = time.time() - start_time
        if game_entered and elapsed_time > time_to_stay_in_game:
            logging.info("Timer has run out. Forfeit the game.")
            send_adb_tap(75, 460)
            time.sleep(1)
            send_adb_tap(429, 1254)
            time.sleep(1)

        # Load the screenshot as an image
        img_screenshot = cv2.imread("screenshot.png", cv2.IMREAD_COLOR)

        # Check if any of the image files match the screenshot
        max_val = 0
        max_image_file: str = ""
        max_coords = None
        for image_file, img_template in template_images.items():
            result = image_service.find_image(img_screenshot, img_template)
            if result:
                val, coords = result
            else:
                # handle case where find_image returns None
                val, coords = 0, None

            # Update the maximum value and corresponding image file and coordinates if necessary
            if val > max_val:
                max_val = val
                max_image_file = image_file
                max_coords = coords

        # Check if the maximum value is above a certain threshold
        if max_val > 0.90:
            logging.info(f"Image {max_image_file} matches with {max_val * 100}%")

            # If not ingame reset timer
            if is_ingame(max_image_file):
                if not game_entered:
                    start_time = time.time()
                    game_entered = True

                # Send tap to attack
                send_adb_tap(500, 1400)
            else:
                start_time = time.time()
                game_entered = False

                # Send an ADB command to tap on the corresponding coordinates
                send_adb_tap(max_coords[0], max_coords[1])

            if max_image_file.startswith("max_number_of_games_played_text."):
                turn_screen_off()
                logging.info("Max number of games played. Exit program.")
                sys.exit(1)

        time.sleep(2)
