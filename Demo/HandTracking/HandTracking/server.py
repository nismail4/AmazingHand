"""Data acquisition server.

Manages a recording session with a LeRobot robot.
Uses the provided LeRobot functions to record episodes and manage datasets.
Provides gRPC services for dataset management and session control.
"""

from concurrent import futures
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, Optional

import grpc
from google.protobuf.empty_pb2 import Empty

from amazing_hand_api.amazing_hand_pb2 import (
    HandTeleoperationCommand,
    HandConfiguration,
    CalibrationData,
    FingerTipPosition,
)
from amazing_hand_api.amazing_hand_pb2_grpc import (
    add_AHTeleoperationServiceServicer_to_server,
)
from dora import Node
import pyarrow as pa


class AmazingHandServicer:
    """Servicer for data acquisition using LeRobot."""

    def __init__(
        self,
    ) -> None:
        """Initialize the data acquisition servicer."""
        self._logger = getLogger(__name__)
        self.node = Node()
        print("AmazingHandServicer initialized")

    def _register_to_server(self, server: Any) -> None:
        """Register the servicer to the gRPC server."""
        add_AHTeleoperationServiceServicer_to_server(self, server)

    def SendCalibrationData(
        self, request: CalibrationData, context: grpc.ServicerContext
    ) -> Empty:
        """Handle calibration data."""
        return Empty()

    def SendHandCommand(
        self, request: HandTeleoperationCommand, context: grpc.ServicerContext
    ) -> Empty:
        """Stop the current episode recording."""

        # if request.right_hand.index_pinch.pinch_value < 0.9:
        r_res = [
            {
                "r_tip1": [
                    request.right_hand.index.x * 0.87,
                    request.right_hand.index.y * 0.87,
                    request.right_hand.index.z * 0.87,
                ],
                "r_tip2": [
                    request.right_hand.middle.x * 0.75,
                    request.right_hand.middle.y * 0.75,
                    request.right_hand.middle.z * 0.75,
                ],
                "r_tip3": [
                    request.right_hand.ring.x * 0.77,
                    request.right_hand.ring.y * 0.77,
                    request.right_hand.ring.z * 0.77,
                ],
                "r_tip4": [
                    request.right_hand.thumb.x * 0.75,
                    request.right_hand.thumb.y * 0.75,
                    request.right_hand.thumb.z * 0.75,
                ],
            }
        ]

        # if request.right_hand.index_pinch.pinch_value > 0.9:

        def modulation(max_mod: float, value: float) -> float:
            return max_mod * value

        r_res[0]["r_tip1"][2] = r_res[0]["r_tip1"][2] + modulation(
            -0.03, request.right_hand.index_pinch.pinch_value
        )
        r_res[0]["r_tip4"][2] = r_res[0]["r_tip4"][2] + modulation(
            0.03, request.right_hand.index_pinch.pinch_value
        )
        r_res[0]["r_tip4"][0] = r_res[0]["r_tip4"][0] + modulation(
            -0.02, request.right_hand.index_pinch.pinch_value
        )

        # else:
        #     r_res = [
        #         {
        #             "r_tip1": [
        #                 request.right_hand.index.x * 0.9,
        #                 request.right_hand.index.y * 0.9,
        #                 request.right_hand.index.z * 0.9,
        #             ],
        #             "r_tip2": [
        #                 request.right_hand.middle.x * 0.9,
        #                 request.right_hand.middle.y * 0.9,
        #                 request.right_hand.middle.z * 0.9,
        #             ],
        #             "r_tip3": [
        #                 request.right_hand.ring.x * 0.9,
        #                 request.right_hand.ring.y * 0.9,
        #                 request.right_hand.ring.z * 0.9,
        #             ],
        #             "r_tip4": [
        #                 0.03,
        #                 -0.02,
        #                 0.1,
        #             ],
        #         }
        #     ]

        l_res = [
            {
                "l_tip1": [
                    request.left_hand.index.x,
                    request.left_hand.index.y,
                    request.left_hand.index.z,
                ],
                "l_tip2": [
                    request.left_hand.middle.x,
                    request.left_hand.middle.y,
                    request.left_hand.middle.z,
                ],
                "l_tip3": [
                    request.left_hand.ring.x,
                    request.left_hand.ring.y,
                    request.left_hand.ring.z,
                ],
                "l_tip4": [
                    request.left_hand.thumb.x,
                    request.left_hand.thumb.y,
                    request.left_hand.thumb.z,
                ],
            }
        ]

        if r_res is not None:
            self.node.send_output("r_hand_pos", pa.array(r_res))
        if l_res is not None:
            self.node.send_output("l_hand_pos", pa.array(l_res))
        return Empty()


def main() -> None:
    """Main function to start the gRPC server."""

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    amazing_hand_servicer = AmazingHandServicer()
    amazing_hand_servicer._register_to_server(server)
    server.add_insecure_port("[::]:50074")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    main()
