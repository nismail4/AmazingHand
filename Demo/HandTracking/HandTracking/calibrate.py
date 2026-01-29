import argparse
import os
import time

import cv2
import numpy as np
import pyarrow as pa
from dora import Node
import mediapipe as mp
from scipy.spatial.transform import Rotation

from typing import Callable, Iterable, Tuple, Optional

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

import json
import os
from typing import Callable, Any, Dict

from pathlib import Path


# https://mediapipe.readthedocs.io/en/latest/solutions/hands.html


import numpy as np

AH_FINGER_SIZE = 0.063  # length of index finger

CALIBRATION_FILE = "HandTracking/HandTracking/user_calibration.json"

CALIBRATION_KEYS = (
    "index_finger",
    "middle_finger",
    "ring_finger",
    "thumb",
)

TEMP_CALIBRATION_FILE = Path("HandTracking/HandTracking/current_calibration.json")


def calibrate():
    cap = cv2.VideoCapture(0)

    with mp_hands.Hands(
        model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence=0.5
    ) as hands:
        ret, frame = cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        # process

        frame.flags.writeable = False
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame)
        # img_width,img_height,_ =image.shape
        # Draw the hand annotations on the image.
        frame.flags.writeable = True
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        results = hands.process(frame)
        if results.multi_hand_landmarks:

            for index, handedness_classif in enumerate(results.multi_handedness):
                if (
                    handedness_classif.classification[0].score > 0.8
                ):  # let's considere only one right hand

                    hand_landmarks = results.multi_hand_world_landmarks[index]  # metric
                    hand_landmarks_norm = results.multi_hand_landmarks[
                        index
                    ]  # normalized

                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks_norm,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )

                    index_length = compute_distance_between_two_3d_points(
                        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP],
                        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP],
                    )
                    middle_length = compute_distance_between_two_3d_points(
                        hand_landmarks.landmark[
                            mp_hands.HandLandmark.MIDDLE_FINGER_TIP
                        ],
                        hand_landmarks.landmark[
                            mp_hands.HandLandmark.MIDDLE_FINGER_MCP
                        ],
                    )
                    ring_length = compute_distance_between_two_3d_points(
                        hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP],
                        hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP],
                    )
                    thumb_length = compute_distance_between_two_3d_points(
                        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP],
                        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_CMC],
                    )
                    cv2.imshow("MediaPipe Hands", frame)
                    cv2.waitKey(500)
                    cv2.destroyAllWindows()
                    return [index_length, middle_length, ring_length, thumb_length]


def compute_distance_between_two_3d_points(p1, p2) -> float:
    """
    Calibrates the distance between two 3D points.

    Args:
        p1 (Point3D): The first 3D point.
        p2 (Point3D): The second 3D point.

    Returns:
        float: The distance between the two points.
    """
    distance = np.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2 + (p2.z - p1.z) ** 2)
    return distance


def start_hand_spread_calibration(
    calibration_fn: Callable[[], float],
    countdown_seconds: int = 3,
    prompt: str = "Spread your hand as wide as possible, then press Enter to start calibration...",
):
    """
    Start a user-guided calibration sequence:
    1) Prompt the user to spread their hand and press Enter
    2) After Enter, show a countdown
    3) Run the provided calibration function

    Args:
        calibration_fn: A zero-argument function that runs calibration and returns a float.
                        (Wrap your real calibration call in a lambda if it needs arguments.)
        countdown_seconds: Number of seconds for the countdown.
        prompt: Instruction shown to the user.

    Returns:
        Whatever `calibration_fn` returns (typically a float).
    """
    input(prompt)

    for remaining in range(countdown_seconds, 0, -1):
        print(f"Calibrating in {remaining}...")
        time.sleep(1)

    print("Calibrating now.")
    result = calibration_fn()
    print(f"Calibration result: {result}")

    ratio_result = [AH_FINGER_SIZE / length for length in result]
    print(f"Normalized calibration result: {ratio_result}")
    return ratio_result


def save_user_calibration(
    calibration_fn: Callable[[], Dict[str, float]], file_path: str = CALIBRATION_FILE
) -> None:
    """
    Save a new user's calibration to the global calibration file.

    The calibration function must return a dictionary with the exact keys:
    {index_finger, middle_finger, ring_finger, thumb}

    Args:
        calibration_fn: Function returning calibration values.
        file_path: Path to the calibration JSON file.
    """
    user_name = input("Enter user name for calibration: ").strip()

    if not user_name:
        raise ValueError("User name cannot be empty.")

    # Load existing calibrations
    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if user_name in data:
        raise ValueError(f"User '{user_name}' already exists.")

    values = calibration_fn()

    # Validate returned values
    if not isinstance(values, (list, tuple)):
        raise TypeError("Calibration function must return a list or tuple.")

    if len(values) != len(CALIBRATION_KEYS):
        raise ValueError(
            f"Calibration function must return {len(CALIBRATION_KEYS)} values."
        )

    for i, v in enumerate(values):
        if not isinstance(v, (int, float)):
            raise ValueError(f"Calibration value at index {i} must be numeric.")

    # Map list -> dict using fixed keys
    calibration_data: Dict[str, float] = {
        key: float(value) for key, value in zip(CALIBRATION_KEYS, values)
    }

    data[user_name] = calibration_data

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    with open(TEMP_CALIBRATION_FILE, "w", encoding="utf-8") as f:
        json.dump(calibration_data, f, indent=4)

    print(f"Calibration saved for user '{user_name}'.")


if __name__ == "__main__":

    save_user_calibration(
        lambda: start_hand_spread_calibration(
            calibration_fn=lambda: calibrate(),
            countdown_seconds=3,
        )
    )
