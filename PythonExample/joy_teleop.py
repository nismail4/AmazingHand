import sys

import pygame
import time
import math
import numpy as np
import threading
import queue
import traceback
from movements import *

import os

# To be able to use pygame in "headless" mode
# set SDL to use the dummy NULL video driver, so it doesn't need a windowing system.
os.environ["SDL_VIDEODRIVER"] = "dummy"

msg = """
This node takes inputs from a controller and publishes them
as Twist messages in SI units. Tested on a SONY Dual shock 4 controller
and an XBOX controller.

Left joy: holonomic translations
Right joy: rotation

L2/L1 : increase/decrease only linear speed (additive) +-0.05m/s
R2/R1 : increase/decrease only angular speed (additive) +-0.2rad/s

CTRL-C  or press CIRCLE on the controller to quit
"""

# PS4 controller:
# Button  0 = X
# Button  1 = O
# Button  2 = Triangle
# Button  3 = Square
# Button  4 = l1
# Button  5 = r1
# Button  6 = l2
# Button  7 = r2
# Button  8 = share
# Button  9 = options
# Button 10 = ps_button
# Button 11 = joy_left
# Button 12 = joy_right

# XBOX controller:
# Button  0 = A
# Button  1 = B
# Button  2 = X
# Button  3 = Y
# Button  4 = LB
# Button  5 = RB
# Button  6 = back
# Button  7 = start
# Button  8 = big central button
# LT and RT are axis (like a joy)

# When using the XBOX controller, most of it is the same,
# except that you must use Start and Back to increase the max speeds.


def sign(x):
    if x >= 0:
        return 1
    else:
        return -1


class AHJoyTeleop:
    def __init__(self):
        print("Starting ah_teleop_joy!")

        pygame.init()
        pygame.display.init()
        pygame.joystick.init()

        self.nb_joy = pygame.joystick.get_count()
        if self.nb_joy < 1:
            print("No controller detected.")
        print("nb joysticks: {}".format(self.nb_joy))
        self.j = pygame.joystick.Joystick(0)
        # The joyticks dont come back at a perfect 0 position when released.
        # Any abs(value) below min_joy_position will be assumed to be 0
        self.min_joy_position = 0.03
        self.joy_activation_threshold = 0.5
        self.lin_speed_ratio = 0.15

        self.prev_joy2 = -1
        self.prev_joy5 = -1
        self.prev_joy0 = -1
        self.prev_joy1 = -1
        self.prev_hat = (0, 0)

        self.current_hand_used = "right"
        self.current_finger_used = "index"

        self.current_command = None
        # self.command_lock = threading.Lock()
        # self.sdk_command_queue = queue.Queue()

        # self.command_thread = threading.Thread(target=self.run_AH_command, daemon=True)
        # self.command_thread.start()

        self.main_tick()

    def run_AH_command(self):
        """Thread for managing AH commands."""
        try:
            # while True:
            #     time.sleep(0.01)  # Avoid busy waiting

            # with self.command_lock:
            #     command = self.current_command
            #     self.current_command = None  # Clear the command after reading

            # if command is None:
            #     continue

            # Execute the command
            try:
                if self.current_command == "open_right_hand":
                    OpenHand(1)
                elif self.current_command == "open_left_hand":
                    OpenHand(2)
                elif self.current_command == "close_right_hand":
                    CloseHand(1)
                elif self.current_command == "close_left_hand":
                    CloseHand(2)
                elif self.current_command == "pinch":
                    if self.current_hand_used == "right":
                        Pinched(1)
                    elif self.current_hand_used == "left":
                        Pinched(2)
                    elif self.current_hand_used == "both":
                        Pinched(1)
                        Pinched(2)
                elif self.current_command == "index_point":
                    if self.current_hand_used == "right":
                        Index_Pointing(1)
                    elif self.current_hand_used == "left":
                        Index_Pointing(2)
                    elif self.current_hand_used == "both":
                        Index_Pointing(1)
                        Index_Pointing(2)
                elif self.current_command == "perfect":
                    if self.current_hand_used == "right":
                        Perfect(1)
                    elif self.current_hand_used == "left":
                        Perfect(2)
                    elif self.current_hand_used == "both":
                        Perfect(1)
                        Perfect(2)
                elif self.current_command == "spread_hand":
                    if self.current_hand_used == "right":
                        SpreadHand(1)
                    elif self.current_hand_used == "left":
                        SpreadHand(2)
                    elif self.current_hand_used == "both":
                        SpreadHand(1)
                        SpreadHand(2)
                else:
                    print(f"Unknown command: {self.current_command}")
                self.current_command = None  # Clear command after execution
            except Exception as e:
                print(f"Error executing ReachySDK command: {e}")
        except Exception as e:
            print(f"Failed to initialize ReachySDK: {e}")

    def set_command(self, command):
        """Set a new command if none is currently being executed."""
        if self.current_command is None:
            self.current_command = command
        else:
            print("Cannot set command; one is already being executed.")

    def tick_controller(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.emergency_shutdown()
            elif event.type == pygame.JOYBUTTONDOWN:

                if self.j.get_button(4):  # lb
                    print("open Left hand")
                    self.set_command("open_left_hand")
                if self.j.get_button(5):  # rb
                    print("open Right hand")
                    self.set_command("open_right_hand")

                if self.j.get_button(6):  # l2
                    print("Pressed button 6")

                if self.j.get_button(7):  # r2
                    print("Pressed button 7")

                if self.j.get_button(3):  # Y
                    self.set_command("index_point")
                if self.j.get_button(2):  # X
                    self.set_command("spread_hand")
                if self.j.get_button(0):  # A
                    self.set_command("perfect")
                if self.j.get_button(1):
                    self.set_command("pinch")  # B

            elif event.type == pygame.JOYAXISMOTION:
                curr_joy2 = self.j.get_axis(2)  # LT
                curr_joy5 = self.j.get_axis(5)  # RT
                if curr_joy2 > 0 and self.prev_joy2 <= 0:
                    print("close Left hand")
                    self.set_command("close_left_hand")
                if curr_joy5 > 0 and self.prev_joy5 <= 0:
                    print("close Right hand")
                    self.set_command("close_right_hand")
                self.prev_joy2 = curr_joy2
                self.prev_joy5 = curr_joy5

            elif event.type == pygame.JOYHATMOTION:
                curr_hat = self.j.get_hat(0)
                if curr_hat == (0, 1) and self.prev_hat != (0, 1):
                    self.current_finger_used = "middle"
                    print("Current finger used: MIDDLE")
                if curr_hat == (0, -1) and self.prev_hat != (0, -1):
                    self.current_finger_used = "thumb"
                    print("Current finger used: THUMB")
                if curr_hat == (1, 0) and self.prev_hat != (1, 0):
                    self.current_finger_used = "ring"
                    print("Current finger used: RING")
                if curr_hat == (-1, 0) and self.prev_hat != (-1, 0):
                    self.current_finger_used = "index"
                    print("Current finger used: INDEX")
                self.prev_hat = curr_hat

            elif event.type == pygame.JOYBUTTONUP:
                pass

        if self.nb_joy != pygame.joystick.get_count():
            print("Controller disconnected!")
            self.emergency_shutdown()

    def print_controller(self):
        # Get the name from the OS for the controller/joystick.
        name = self.j.get_name()
        print("Joystick name: {}".format(name))

        # Usually axis run in pairs, up/down for one, and left/right for
        # the other.
        axes = self.j.get_numaxes()
        print("Number of axes: {}".format(axes))

        for i in range(axes):
            axis = self.j.get_axis(i)
            print("Axis {} value: {:>6.3f}".format(i, axis))

        buttons = self.j.get_numbuttons()
        print("Number of buttons: {}".format(buttons))

        for i in range(buttons):
            button = self.j.get_button(i)
            print("Button {:>2} value: {}".format(i, button))

    def infos_from_joystick(self):
        if (
            abs(self.j.get_axis(0)) > self.joy_activation_threshold
            and abs(self.prev_joy0) <= self.joy_activation_threshold
        ):
            if -self.j.get_axis(0) > 0:
                self.current_hand_used = "left"
                print("Current hand used: LEFT")
            else:
                self.current_hand_used = "right"
                print("Current hand used: RIGHT")
        self.prev_joy0 = self.j.get_axis(0)

        if (
            abs(self.j.get_axis(1)) > self.joy_activation_threshold
            and abs(self.prev_joy1) <= self.joy_activation_threshold
        ):
            if -self.j.get_axis(1) > 0:
                self.current_hand_used = "both"
                print("Current hand used: BOTH")
        self.prev_joy1 = self.j.get_axis(1)

        if abs(self.j.get_axis(3)) < self.min_joy_position:
            x = 0.0
        else:
            x = -self.j.get_axis(3) * self.lin_speed_ratio

        if abs(self.j.get_axis(4)) < self.min_joy_position:
            y = 0.0
        else:
            y = -self.j.get_axis(4) * self.lin_speed_ratio

        return x, y

    def emergency_shutdown(self):
        print("Emergency shutdown!")
        TurnOffHand()

    def main_tick(self):
        while True:
            # print("Tick!!")
            self.tick_controller()
            x, y = self.infos_from_joystick()
            self.run_AH_command()
            # self.print_controller()
            time.sleep(0.1)


def main():
    try:
        teleop = AHJoyTeleop()
    except Exception as e:
        traceback.print_exc()
    finally:
        teleop.emergency_shutdown()


if __name__ == "__main__":
    main()
