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


def _clip_line_to_image(p, v, W, H, eps=1e-12):
    """
    p, v en pixels (float). Renvoie deux points (x,y) en pixels (float)
    correspondant aux intersections de la droite avec le cadre image.
    """
    ts = []

    # x = 0 et x = W-1
    if abs(v[0]) > eps:
        for x in (0.0, float(W - 1)):
            t = (x - p[0]) / v[0]
            y = p[1] + t * v[1]
            if 0.0 <= y <= (H - 1):
                ts.append(t)

    # y = 0 et y = H-1
    if abs(v[1]) > eps:
        for y in (0.0, float(H - 1)):
            t = (y - p[1]) / v[1]
            x = p[0] + t * v[0]
            if 0.0 <= x <= (W - 1):
                ts.append(t)

    if len(ts) < 2:
        return None  # cas dégénéré

    t0, t1 = min(ts), max(ts)
    return (p + t0 * v, p + t1 * v)


def draw_line_normalized(img, p01, v01, color=(0, 0, 255), thickness=2):
    """
    p01: (x,y) dans [0,1]
    v01: (vx,vy) direction dans [0,1] (non nulle), y descend
    """
    H, W = img.shape[:2]

    # point -> pixels
    p = np.array([p01[0] * (W - 1), p01[1] * (H - 1)], dtype=float)

    # direction -> pixels (important si W != H), puis normalisation
    v = np.array([v01[0] * (W - 1), v01[1] * (H - 1)], dtype=float)
    n = np.linalg.norm(v)
    if n < 1e-9:
        return img
    v /= n

    seg = _clip_line_to_image(p, v, W, H)
    if seg is None:
        return img

    p0, p1 = seg
    pt0 = (int(round(p0[0])), int(round(p0[1])))
    pt1 = (int(round(p1[0])), int(round(p1[1])))

    cv2.line(img, pt0, pt1, color, thickness, lineType=cv2.LINE_AA)
    return img


def draw_two_lines_red(img, p01_a, v01_a, p01_b, v01_b, thickness=2):
    draw_line_normalized(img, p01_a, v01_a, color=(0, 255, 0), thickness=thickness)
    draw_line_normalized(img, p01_b, v01_b, color=(0, 0, 255), thickness=thickness)
    return img


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

                # for hand_landmarks in results.multi_hand_landmarks:
                #     tip_x=hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].x-hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].x
                #     tip_y=hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y-hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].y
                #     tip_z=hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].z-hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].z
                #     print(f'TIP: {tip_x} {tip_y} {tip_z}')
                #     mp_drawing.draw_landmarks(
                #         image,
                #         hand_landmarks,
                #         mp_hands.HAND_CONNECTIONS,
                #         mp_drawing_styles.get_default_hand_landmarks_style(),
                #         mp_drawing_styles.get_default_hand_connections_style())

                hand_landmarks = results.multi_hand_world_landmarks[index]  # metric
                # hand_landmarks=results.multi_hand_landmarks[index] #normalized
                hand_landmarks_norm = results.multi_hand_landmarks[index]  # normalized

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

                # print(
                #     f"{hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP].z:.3f}, {hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].z:.3f}"
                # )

                ### TEST THUMB EXTENSION HANDLING
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

                ### TEST INDEX EXTENSION HANDLING
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

                if handedness_classif.classification[0].label == "Right":
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

                    ### TEST Z THUMB MODIFICATION IF BENT
                    if (
                        np.linalg.norm(
                            [
                                hand_landmarks.landmark[
                                    mp_hands.HandLandmark.THUMB_TIP
                                ].x
                                - hand_landmarks.landmark[
                                    mp_hands.HandLandmark.RING_FINGER_MCP
                                ].x,
                                hand_landmarks.landmark[
                                    mp_hands.HandLandmark.THUMB_TIP
                                ].y
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

                    # Detect pinch if index finger and thumb are close
                    # PINCH MANAGEMENT
                    right_pinch_detected = False
                    index_thumb_relative_pos = 0.0
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
                        # print("YEah")
                        right_pinch_detected = True
                        index_thumb_relative_pos = (
                            thumb_tip_extended[0] - index_tip_extended[0]
                        )

                ### END OF TEST

                ### NO THUMB EXTENSION

                # if handedness_classif.classification[0].label == "Right":
                #     tip4_x = (
                #         hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x
                #         - hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_CMC].x
                #     )

                #     tip4_y = (
                #         hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y
                #         - hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_CMC].y
                #     )

                #     tip4_z = (
                #         hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].z
                #         - hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_CMC].z
                #     )

                #     # Detect pinch if index finger and thumb are close
                #     if (
                #         np.linalg.norm(
                #             [
                #                 hand_landmarks.landmark[
                #                     mp_hands.HandLandmark.THUMB_TIP
                #                 ].x
                #                 - hand_landmarks.landmark[
                #                     mp_hands.HandLandmark.INDEX_FINGER_TIP
                #                 ].x,
                #                 hand_landmarks.landmark[
                #                     mp_hands.HandLandmark.THUMB_TIP
                #                 ].y
                #                 - hand_landmarks.landmark[
                #                     mp_hands.HandLandmark.INDEX_FINGER_TIP
                #                 ].y,
                #             ]
                #         )
                #         < 0.02
                #     ):
                #         pinch_detected = True
                #         index_thumb_relative_pos = (
                #             hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x
                #             - hand_landmarks.landmark[
                #                 mp_hands.HandLandmark.INDEX_FINGER_TIP
                #             ].x
                #         )

                ### END OF MODIFICATIONS

                if handedness_classif.classification[0].label == "Left":
                    tip4_x = (
                        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x
                        - hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP].x
                    )
                    tip4_y = (
                        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y
                        - hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP].y
                    )
                    tip4_z = (
                        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].z
                        - hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP].z
                    )

                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks_norm,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style(),
                )

                # define a new hand frame centered at marker WRIST (n°0) with z along the vector (WRIST,MIDDLE_FINGER_MCP) (0,9) and x is the "third dimension" normal to the plan of the palm (WRIST,MIDDLE_FINGER_MCP)x(WRIST,PINKY_MCP)
                # origin=np.array([hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].x,hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].y,hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].z])
                # mid_mcp=np.array([hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].x,hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y,hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].z])
                # unit_z=mid_mcp-origin
                # unit_z=unit_z/np.linalg.norm(unit_z)
                # pinky_mcp=np.array([hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP].x,hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP].y,hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP].z])

                # rotate everything in a hand referential
                origin = np.array(
                    [
                        hand_landmarks_norm.landmark[mp_hands.HandLandmark.WRIST].x,
                        hand_landmarks_norm.landmark[mp_hands.HandLandmark.WRIST].y,
                        hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].z,
                    ]
                )  # wrist base as the origin

                # Filter origin
                origin = coord_system_filt["origin"].filter(origin)

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

                mid_mcp = coord_system_filt["middle_finger_MCP"].filter(mid_mcp)

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

                index_mcp = coord_system_filt["index_finger_MCP"].filter(index_mcp)

                # print(f"ORIGIN: {origin} MID: {mid_mcp}")

                if handedness_classif.classification[0].label == "Right":
                    vec_towards_y = (
                        # pinky_mcp - origin
                        origin
                        - index_mcp
                    )  # vector from wrist base towards pinky base
                if handedness_classif.classification[0].label == "Left":
                    vec_towards_y = (
                        index_mcp - origin
                    )  # vector from wrist base towards pinky base
                # unit_x=np.cross(unit_z,vec_towards_y)
                # vec_towards_y=pinky_mcp-origin #vector from wrist base towards pinky base

                unit_x = np.cross(
                    vec_towards_y, unit_z
                )  # we say unit x is the cross product of z and the vector towards pinky

                unit_x = unit_x / np.linalg.norm(unit_x)

                unit_y = np.cross(unit_z, unit_x)
                # unit_y=np.cross(unit_x,unit_z)

                if handedness_classif.classification[0].label == "Right":
                    # A=np.array([unit_x,unit_y,unit_z]).reshape((3,3))
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

                if tip1[2] <= 0.03:
                    tip1[1] = 0
                # scale=0.01
                # image = cv2.drawFrameAxes(image, K, disto, rotV, origin, scale)

                # res=[{'r_tip1': [tip1_x,tip1_y,tip1_z],'r_tip2': [tip2_x,tip2_y,tip2_z],'r_tip3': [tip3_x,tip3_y,tip3_z],'r_tip4': [tip4_x,tip4_y,tip4_z]}]
                if handedness_classif.classification[0].label == "Right":

                    # Adjust index finger position when bent

                    if right_pinch_detected:
                        # tip4 = np.array([0.03, -0.03 - index_thumb_relative_pos, 0.1])
                        tip4 = np.array([0.03, -0.02 - index_thumb_relative_pos, 0.1])
                        tip1[2] = tip1_extended[2]
                        tip1[1] += index_thumb_relative_pos

                    r_res = [
                        {
                            "r_tip1": tip1 * finger_lengths[0],
                            "r_tip2": tip2 * finger_lengths[1],
                            "r_tip3": tip3 * finger_lengths[2],
                            "r_tip4": tip4 * finger_lengths[3],
                        }
                    ]
                    # print(
                    #     f"RIGHT: {tip1_x:.3f} {tip1_y:.3f} {tip1_z:.3f} => {tip1}. {unit_x} {unit_y} {unit_z}"
                    # )

                    # draw_two_lines_red(
                    #     image,
                    #     [
                    #         hand_landmarks_norm.landmark[
                    #             mp_hands.HandLandmark.THUMB_MCP
                    #         ].x,
                    #         hand_landmarks_norm.landmark[
                    #             mp_hands.HandLandmark.THUMB_MCP
                    #         ].y,
                    #     ],
                    #     unit_z,
                    #     [
                    #         hand_landmarks_norm.landmark[
                    #             mp_hands.HandLandmark.THUMB_MCP
                    #         ].x,
                    #         hand_landmarks_norm.landmark[
                    #             mp_hands.HandLandmark.THUMB_MCP
                    #         ].y,
                    #     ],
                    #     unit_y,
                    #     thickness=2,
                    # )

                    # print(
                    #     f"DIstance: {hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].z}, {hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].z}, {hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].z}"
                    # )
                    # print(f"lengths: {finger_lengths}")
                    sample = r_res[0]
                    filtered = res_filt.update(sample)
                    r_res = [filtered]

                elif handedness_classif.classification[0].label == "Left":
                    l_res = [
                        {"l_tip1": tip1, "l_tip2": tip2, "l_tip3": tip3, "l_tip4": tip4}
                    ]
                    # print(f"LEFT: {tip1_x:.3f} {tip1_y:.3f} {tip1_z:.3f} => {tip1}. {unit_x} {unit_y} {unit_z}")
    # Flip the image horizontally for a selfie-view display.
    return image, r_res, l_res


# cv2.imshow('MediaPipe Hands', cv2.flip(image, 1))


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
