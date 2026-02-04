import argparse
import os
import time

import cv2
import numpy as np
import math
import pyarrow as pa
from dora import Node
import mediapipe as mp
from scipy.spatial.transform import Rotation

from typing import Callable, Iterable, Tuple, Optional

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

# https://mediapipe.readthedocs.io/en/latest/solutions/hands.html


import json
from pathlib import Path
from typing import Any, Dict, Tuple


import os
import json
from pathlib import Path
from typing import Any, Tuple

from one_euro_filter import OneEuroDictFilter, OneEuro3D

CALIBRATION_KEYS = ("index_finger", "middle_finger", "ring_finger", "thumb")


def load_current_calibration(
    path: str | Path | None = None,
) -> Tuple[Any, Any, Any, Any]:
    if path is None:
        path = os.environ.get(
            "CURRENT_CALIBRATION_FILE",
            "HandTracking/HandTracking/current_calibration.json",
        )

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Calibration file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    missing = [k for k in CALIBRATION_KEYS if k not in data]
    if missing:
        raise KeyError(f"Missing calibration keys in {path}: {missing}")

    index_length = data["index_finger"]
    middle_length = data["middle_finger"]
    ring_length = data["ring_finger"]
    thumb_length = data["thumb"]
    return index_length, middle_length, ring_length, thumb_length


def point_on_line_at_distance(
    p1: np.ndarray,
    p2: np.ndarray,
    distance: float,
) -> np.ndarray:
    """
    Create a point on the line defined by p1 and p2, at a given distance from p2,
    in the direction from p2 toward p1.

    Args:
        p1: First 3D point (shape: (3,))
        p2: Second 3D point (shape: (3,))
        distance: Distance from p2 to the new point

    Returns:
        A new 3D point lying on the line (p1, p2)

    Raises:
        ValueError: If p1 and p2 are identical
    """
    direction = p1 - p2
    norm = np.linalg.norm(direction)

    if norm == 0.0:
        raise ValueError("p1 and p2 must be different points")

    unit_direction = direction / norm
    new_point = p2 + unit_direction * distance
    return new_point


def process_img(hand_proc, image, finger_lengths, res_filt, coord_system_filt):
    image.flags.writeable = False
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hand_proc.process(image)
    # img_width,img_height,_ =image.shape
    # Draw the hand annotations on the image.
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    r_res = None
    l_res = None
    if results.multi_hand_landmarks:

        # print('Handedness:', results.multi_handedness)
        # print(results.multi_hand_world_landmarks)

        for index, handedness_classif in enumerate(results.multi_handedness):
            if (
                handedness_classif.classification[0].score > 0.8
            ):  # let's considere only one right hand

                hand_landmarks = results.multi_hand_world_landmarks[index]  # metric
                hand_landmarks_norm = results.multi_hand_landmarks[index]  # normalized

                ## INDEX FINGER
                tip1_x = (
                    hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].x
                    - hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].x
                )

                tip1_y = (
                    hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y
                    - hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].y
                )
                tip1_z = (
                    hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].z
                    - hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].z
                )

                ### MIDDLE FINGER
                tip2_x = (
                    hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].x
                    - hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].x
                )
                tip2_y = (
                    hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
                    - hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y
                )
                tip2_z = (
                    hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].z
                    - hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].z
                )

                ### RING FINGER
                tip3_x = (
                    hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].x
                    - hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP].x
                )
                tip3_y = (
                    hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y
                    - hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP].y
                )
                tip3_z = (
                    hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].z
                    - hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP].z
                )

                ### THUMB EXTENSION
                thumb_tip_extended = point_on_line_at_distance(
                    np.array(
                        [
                            hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP].x,
                            hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP].y,
                            hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP].z,
                        ]
                    ),
                    np.array(
                        [
                            hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x,
                            hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y,
                            hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].z,
                        ]
                    ),
                    distance=-0.02,
                )

                ### THUMB FINGER
                tip4_x = (
                    thumb_tip_extended[0]
                    - hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_CMC].x
                )

                tip4_y = (
                    thumb_tip_extended[1]
                    - hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_CMC].y
                )

                tip4_z = (
                    thumb_tip_extended[2]
                    - hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP].z
                )

                ### INDEX EXTENSION
                index_tip_extended = point_on_line_at_distance(
                    np.array(
                        [
                            hand_landmarks.landmark[
                                mp_hands.HandLandmark.INDEX_FINGER_DIP
                            ].x,
                            hand_landmarks.landmark[
                                mp_hands.HandLandmark.INDEX_FINGER_DIP
                            ].y,
                            hand_landmarks.landmark[
                                mp_hands.HandLandmark.INDEX_FINGER_DIP
                            ].z,
                        ]
                    ),
                    np.array(
                        [
                            hand_landmarks.landmark[
                                mp_hands.HandLandmark.INDEX_FINGER_TIP
                            ].x,
                            hand_landmarks.landmark[
                                mp_hands.HandLandmark.INDEX_FINGER_TIP
                            ].y,
                            hand_landmarks.landmark[
                                mp_hands.HandLandmark.INDEX_FINGER_TIP
                            ].z,
                        ]
                    ),
                    distance=-0.04,
                )

                ### Z THUMB MODIFICATION IF BENT
                if (
                    np.linalg.norm(
                        [
                            hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x
                            - hand_landmarks.landmark[
                                mp_hands.HandLandmark.RING_FINGER_MCP
                            ].x,
                            hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y
                            - hand_landmarks.landmark[
                                mp_hands.HandLandmark.RING_FINGER_MCP
                            ].y,
                        ]
                    )
                    < 0.02
                ):
                    tip4_z = hand_landmarks.landmark[
                        mp_hands.HandLandmark.RING_FINGER_MCP
                    ].z

                ### PINCH MANAGEMENT
                # Detect pinch if index finger and thumb are close
                if handedness_classif.classification[0].label == "Right":
                    right_pinch_detected = False
                    right_index_thumb_relative_pos = 0.0
                    if (
                        np.linalg.norm(
                            [
                                hand_landmarks.landmark[
                                    mp_hands.HandLandmark.THUMB_TIP
                                ].x
                                - hand_landmarks.landmark[
                                    mp_hands.HandLandmark.INDEX_FINGER_TIP
                                ].x,
                                hand_landmarks.landmark[
                                    mp_hands.HandLandmark.THUMB_TIP
                                ].y
                                - hand_landmarks.landmark[
                                    mp_hands.HandLandmark.INDEX_FINGER_TIP
                                ].y,
                            ]
                        )
                        < 0.02
                    ):
                        right_pinch_detected = True
                        right_index_thumb_relative_pos = (
                            thumb_tip_extended[0] - index_tip_extended[0]
                        )

                if handedness_classif.classification[0].label == "Left":
                    left_pinch_detected = False
                    left_index_thumb_relative_pos = 0.0
                    if (
                        np.linalg.norm(
                            [
                                hand_landmarks.landmark[
                                    mp_hands.HandLandmark.THUMB_TIP
                                ].x
                                - hand_landmarks.landmark[
                                    mp_hands.HandLandmark.INDEX_FINGER_TIP
                                ].x,
                                hand_landmarks.landmark[
                                    mp_hands.HandLandmark.THUMB_TIP
                                ].y
                                - hand_landmarks.landmark[
                                    mp_hands.HandLandmark.INDEX_FINGER_TIP
                                ].y,
                            ]
                        )
                        < 0.02
                    ):
                        left_pinch_detected = True
                        left_index_thumb_relative_pos = (
                            thumb_tip_extended[0] - index_tip_extended[0]
                        )

                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks_norm,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style(),
                )

                # rotate everything in a hand referential
                origin = np.array(
                    [
                        hand_landmarks_norm.landmark[mp_hands.HandLandmark.WRIST].x,
                        hand_landmarks_norm.landmark[mp_hands.HandLandmark.WRIST].y,
                        hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].z,
                    ]
                )  # wrist base as the origin

                # Filter origin
                # origin = coord_system_filt["origin"].filter(origin)

                mid_mcp = np.array(
                    [
                        hand_landmarks_norm.landmark[
                            mp_hands.HandLandmark.MIDDLE_FINGER_MCP
                        ].x,
                        hand_landmarks_norm.landmark[
                            mp_hands.HandLandmark.MIDDLE_FINGER_MCP
                        ].y,
                        hand_landmarks_norm.landmark[
                            mp_hands.HandLandmark.MIDDLE_FINGER_MCP
                        ].z,
                    ]
                )  # base of the middle finger

                # Filter mid_mcp
                # mid_mcp = coord_system_filt["middle_finger_MCP"].filter(mid_mcp)

                unit_z = (
                    mid_mcp - origin
                )  # z is unit vector from base of wrist toward base of middle finger
                unit_z = unit_z / np.linalg.norm(unit_z)

                index_mcp = np.array(
                    [
                        hand_landmarks_norm.landmark[
                            mp_hands.HandLandmark.INDEX_FINGER_MCP
                        ].x,
                        hand_landmarks_norm.landmark[
                            mp_hands.HandLandmark.INDEX_FINGER_MCP
                        ].y,
                        hand_landmarks_norm.landmark[
                            mp_hands.HandLandmark.INDEX_FINGER_MCP
                        ].z,
                    ]
                )  # base of the index finger

                # Filter index_mcp
                # index_mcp = coord_system_filt["index_finger_MCP"].filter(index_mcp)

                if handedness_classif.classification[0].label == "Right":
                    vec_towards_y = (
                        origin - index_mcp
                    )  # vector from index torwards index finger
                if handedness_classif.classification[0].label == "Left":
                    vec_towards_y = (
                        index_mcp - origin
                    )  # vector from wrist base towards pinky base

                unit_x = np.cross(
                    vec_towards_y, unit_z
                )  # we say unit x is the cross product of z and the vector towards index finger

                unit_x = unit_x / np.linalg.norm(unit_x)

                unit_y = np.cross(unit_z, unit_x)

                if handedness_classif.classification[0].label == "Right":
                    R = np.array([unit_x, -unit_y, unit_z]).reshape(
                        (3, 3)
                    )  # -y because of mirror?
                if handedness_classif.classification[0].label == "Left":
                    R = np.array([unit_x, -unit_y, unit_z]).reshape(
                        (3, 3)
                    )  # -y because of mirror?

                tip1 = R @ np.array([tip1_x, tip1_y, tip1_z])
                tip2 = R @ np.array([tip2_x, tip2_y, tip2_z])
                tip3 = R @ np.array([tip3_x, tip3_y, tip3_z])
                tip4 = R @ np.array([tip4_x, tip4_y, tip4_z])

                tip1_extended = R @ np.array(
                    [
                        index_tip_extended[0]
                        - hand_landmarks.landmark[
                            mp_hands.HandLandmark.INDEX_FINGER_MCP
                        ].x,
                        index_tip_extended[1]
                        - hand_landmarks.landmark[
                            mp_hands.HandLandmark.INDEX_FINGER_MCP
                        ].y,
                        index_tip_extended[2]
                        - hand_landmarks.landmark[
                            mp_hands.HandLandmark.INDEX_FINGER_MCP
                        ].z,
                    ]
                )

                # Adjust index finger position when bent
                if tip1[2] <= 0.03:
                    tip1[1] = 0

                if handedness_classif.classification[0].label == "Right":

                    if right_pinch_detected:
                        tip4 = np.array(
                            [0.03, -0.02 - right_index_thumb_relative_pos, 0.1]
                        )
                        tip1[2] = tip1_extended[2]
                        tip1[1] += right_index_thumb_relative_pos
                        tip1[0] -= 0.02

                    r_res = [
                        {
                            "r_tip1": tip1 * finger_lengths[0],
                            "r_tip2": tip2 * finger_lengths[1],
                            "r_tip3": tip3 * finger_lengths[2],
                            "r_tip4": tip4 * finger_lengths[3],
                        }
                    ]

                    l_res = [
                        {
                            "l_tip1": tip1 * finger_lengths[0],
                            "l_tip2": tip2 * finger_lengths[1],
                            "l_tip3": tip3 * finger_lengths[2],
                            "l_tip4": tip4 * finger_lengths[3],
                        }
                    ]

                    # Filter r_res
                    # sample = r_res[0]
                    # filtered = res_filt.update(sample)
                    # r_res = [filtered]

                elif handedness_classif.classification[0].label == "Left":

                    if left_pinch_detected:
                        tip4 = np.array(
                            [0.03, 0.02 - left_index_thumb_relative_pos, 0.1]
                        )
                        tip1[2] = tip1_extended[2]
                        tip1[1] += left_index_thumb_relative_pos
                        tip1[0] -= 0.02
                    l_res = [
                        {
                            "l_tip1": tip1 * finger_lengths[0],
                            "l_tip2": tip2 * finger_lengths[1],
                            "l_tip3": tip3 * finger_lengths[2],
                            "l_tip4": tip4 * finger_lengths[3],
                        }
                    ]
    return image, r_res, l_res


def main():

    node = Node()

    finger_lengths = load_current_calibration()

    pa.array([])  # initialize pyarrow array
    cap = cv2.VideoCapture(0)

    with mp_hands.Hands(
        model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence=0.5
    ) as hands:

        for event in node:

            event_type = event["type"]

            if event_type == "INPUT":
                event_id = event["id"]

                if event_id == "tick":
                    ret, frame = cap.read()

                    if not ret:
                        continue

                    frame = cv2.flip(frame, 1)
                    # process
                    res_filt = OneEuroDictFilter(
                        freq=100.0, min_cutoff=2.0, beta=0.02, d_cutoff=1.0
                    )

                    coord_system_filt = {
                        "origin": OneEuro3D(
                            freq=100.0, min_cutoff=2.0, beta=0.04, d_cutoff=1.0
                        ),
                        "middle_finger_MCP": OneEuro3D(
                            freq=100.0, min_cutoff=2.0, beta=0.04, d_cutoff=1.0
                        ),
                        "index_finger_MCP": OneEuro3D(
                            freq=100.0, min_cutoff=2.0, beta=0.04, d_cutoff=1.0
                        ),
                    }

                    frame, r_res, l_res = process_img(
                        hands, frame, finger_lengths, res_filt, coord_system_filt
                    )

                    if r_res is not None:
                        node.send_output("r_hand_pos", pa.array(r_res))
                    if l_res is not None:
                        node.send_output("l_hand_pos", pa.array(l_res))
                    # cv2.imshow('MediaPipe Hands', cv2.flip(frame, 1))
                    cv2.imshow("MediaPipe Hands", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

            elif event_type == "ERROR":
                raise RuntimeError(event["error"])


if __name__ == "__main__":
    main()
