from rustypot import Scs0009PyController
import time
import numpy as np

# Speed
MaxSpeed = 7
CloseSpeed = 3

# Fingers middle poses
# replace values by your calibration results
MiddlePos_1 = [
    3,
    0,
    -8,
    -13,
    2,
    -5,
    -12,
    -5,
]
MiddlePos_2 = [3, -3, -1, -10, 5, 2, -7, 3]


c = Scs0009PyController(
    serial_port="/dev/grippers",
    baudrate=1000000,
    timeout=0.05,  # 0.05
)


def TurnOnHand():
    c.write_torque_enable(1, 1)  # (Lowest ID , #1 = On / 2 = Off / 3 = Free )


def TurnOffHand():
    c.write_torque_enable(1, 2)  # (Lowest ID , #1 = On / 2 = Off / 3 = Free )


def OpenHand(side: int):
    print("Opening hand")
    Move_Index(-35, 35, MaxSpeed, side)
    Move_Middle(-35, 35, MaxSpeed, side)
    Move_Ring(-35, 35, MaxSpeed, side)
    Move_Thumb(-35, 35, MaxSpeed, side)


def CloseHand(side: int):
    print("Closing hand")
    Move_Index(90, -90, CloseSpeed, side)
    Move_Middle(90, -90, CloseSpeed, side)
    Move_Ring(90, -90, CloseSpeed, side)
    Move_Thumb(
        90, -90, CloseSpeed + 4, side
    )  # Higher Speed to be sure thumb is passing under index


def OpenHand_Progressive(side: int):
    print("Opening hand progressively")
    Move_Index(-35, 35, MaxSpeed - 2, side)
    time.sleep(0.2)
    Move_Middle(-35, 35, MaxSpeed - 2, side)
    time.sleep(0.2)
    Move_Ring(-35, 35, MaxSpeed - 2, side)
    time.sleep(0.2)
    Move_Thumb(-35, 35, MaxSpeed - 2, side)


def SpreadHand(side: int):
    print("Spreading hand")
    if side == 1:  # Right hand
        Move_Index(4, 90, MaxSpeed, 1)
        Move_Middle(-32, 32, MaxSpeed, 1)
        Move_Ring(-90, -4, MaxSpeed, 1)
        Move_Thumb(-90, -4, MaxSpeed, 1)
    if side == 2:  # Left hand
        Move_Index(-90, 0, MaxSpeed, 2)
        Move_Middle(-32, 32, MaxSpeed, 2)
        Move_Ring(-4, 90, MaxSpeed, 2)
        Move_Thumb(-4, 90, MaxSpeed, 2)


def ClenchHand(side: int):
    print("Clenching hand")
    if side == 1:  # Right hand
        Move_Index(-60, 0, MaxSpeed, 1)
        Move_Middle(-35, 35, MaxSpeed, 1)
        Move_Ring(0, 70, MaxSpeed, 1)
        Move_Thumb(-4, 90, MaxSpeed, 1)
    if side == 2:  # Left hand
        Move_Index(0, 60, MaxSpeed, 2)
        Move_Middle(-35, 35, MaxSpeed, 2)
        Move_Ring(-70, 0, MaxSpeed, 2)
        Move_Thumb(-90, -4, MaxSpeed, 2)


def Index_Pointing(side: int):
    print("Index Pointing")
    Move_Index(-40, 40, MaxSpeed, side)
    Move_Middle(90, -90, MaxSpeed, side)
    Move_Ring(90, -90, MaxSpeed, side)
    Move_Thumb(90, -90, MaxSpeed, side)


def Nonono(side: int):
    print("No no no")
    Index_Pointing(side)
    for i in range(3):
        time.sleep(0.2)
        Move_Index(-10, 80, MaxSpeed, side)
        time.sleep(0.2)
        Move_Index(-80, 10, MaxSpeed, side)

    Move_Index(-35, 35, MaxSpeed, side)
    time.sleep(0.4)


def Perfect(side: int):
    print("Perfect gesture")
    Move_Index(55, -55, MaxSpeed - 3, side)
    Move_Middle(0, -0, MaxSpeed, side)
    Move_Ring(-20, 20, MaxSpeed, side)
    if side == 1:
        Move_Thumb(85, 10, MaxSpeed, side)
    if side == 2:
        Move_Thumb(-10, -85, MaxSpeed, side)


def Victory(side: int):
    print("Victory gesture")
    if side == 1:  # Right hand
        Move_Index(-15, 65, MaxSpeed, side)
        Move_Middle(-65, 15, MaxSpeed, side)
        Move_Ring(90, -90, MaxSpeed, side)
        Move_Thumb(90, -90, MaxSpeed, side)
    if side == 2:  # Left hand
        Move_Index(-65, 15, MaxSpeed, side)
        Move_Middle(-15, 65, MaxSpeed, side)
        Move_Ring(90, -90, MaxSpeed, side)
        Move_Thumb(90, -90, MaxSpeed, side)


def Pinched(side: int):
    print("Pinched gesture")
    Move_Index(90, -90, MaxSpeed, side)
    Move_Middle(90, -90, MaxSpeed, side)
    Move_Ring(90, -90, MaxSpeed, side)
    if side == 1:  # Right hand
        Move_Thumb(5, -75, MaxSpeed, side)
    if side == 2:  # Left hand
        Move_Thumb(75, -5, MaxSpeed, side)


def Scissors(side: int):
    print("Scissors gesture")
    Victory(side)
    for i in range(3):
        time.sleep(0.2)
        if side == 1:  # Right hand
            Move_Index(-50, 20, MaxSpeed, side)
            Move_Middle(-20, 50, MaxSpeed, side)
        if side == 2:  # Left hand
            Move_Index(-20, 50, MaxSpeed, side)
            Move_Middle(-50, 20, MaxSpeed, side)
        time.sleep(0.2)
        if side == 1:  # Right hand
            Move_Index(-15, 65, MaxSpeed, side)
            Move_Middle(-65, 15, MaxSpeed, side)
        if side == 2:  # Left hand
            Move_Index(-65, 15, MaxSpeed, side)
            Move_Middle(-15, 65, MaxSpeed, side)


def Fuck(side: int):
    print("Fuck gesture")
    Move_Index(90, -90, MaxSpeed, side)
    Move_Middle(-35, 35, MaxSpeed, side)
    Move_Ring(90, -90, MaxSpeed, side)
    if side == 1:  # Right hand
        Move_Thumb(5, -75, MaxSpeed, side)
    if side == 2:  # Left hand
        Move_Thumb(75, -5, MaxSpeed, side)


# Fingers


def Move_Index(Angle_1, Angle_2, Speed, Hand):
    if Hand == 1:  # Right hand finger
        c.write_goal_speed(1, Speed)
        time.sleep(0.0002)
        c.write_goal_speed(2, Speed)
        time.sleep(0.0002)
        Pos_1 = np.deg2rad(MiddlePos_1[0] + Angle_1)
        Pos_2 = np.deg2rad(MiddlePos_1[1] + Angle_2)
        c.write_goal_position(1, Pos_1)
        c.write_goal_position(2, Pos_2)
        time.sleep(0.0002)

    if Hand == 2:  # Left hand finger
        c.write_goal_speed(11, Speed)
        time.sleep(0.0002)
        c.write_goal_speed(12, Speed)
        time.sleep(0.0002)
        Pos_1 = np.deg2rad(MiddlePos_2[0] + Angle_1)
        Pos_2 = np.deg2rad(MiddlePos_2[1] + Angle_2)
        c.write_goal_position(11, Pos_1)
        c.write_goal_position(12, Pos_2)
        time.sleep(0.0002)


def Move_Middle(Angle_1, Angle_2, Speed, Hand):
    if Hand == 1:  # Right hand finger
        c.write_goal_speed(3, Speed)
        time.sleep(0.0002)
        c.write_goal_speed(4, Speed)
        time.sleep(0.0002)
        Pos_1 = np.deg2rad(MiddlePos_1[2] + Angle_1)
        Pos_2 = np.deg2rad(MiddlePos_1[3] + Angle_2)
        c.write_goal_position(3, Pos_1)
        c.write_goal_position(4, Pos_2)
        time.sleep(0.0002)
    if Hand == 2:  # Left hand finger
        c.write_goal_speed(13, Speed)
        time.sleep(0.0002)
        c.write_goal_speed(14, Speed)
        time.sleep(0.0002)
        Pos_1 = np.deg2rad(MiddlePos_2[2] + Angle_1)
        Pos_2 = np.deg2rad(MiddlePos_2[3] + Angle_2)
        c.write_goal_position(13, Pos_1)
        c.write_goal_position(14, Pos_2)
        time.sleep(0.0002)


def Move_Ring(Angle_1, Angle_2, Speed, Hand):
    if Hand == 1:  # Right hand finger
        c.write_goal_speed(5, Speed)
        time.sleep(0.0002)
        c.write_goal_speed(6, Speed)
        time.sleep(0.0002)
        Pos_1 = np.deg2rad(MiddlePos_1[4] + Angle_1)
        Pos_2 = np.deg2rad(MiddlePos_1[5] + Angle_2)
        c.write_goal_position(5, Pos_1)
        c.write_goal_position(6, Pos_2)
        time.sleep(0.0002)

    if Hand == 2:  # Left hand finger
        c.write_goal_speed(15, Speed)
        time.sleep(0.0002)
        c.write_goal_speed(16, Speed)
        time.sleep(0.0002)
        Pos_1 = np.deg2rad(MiddlePos_2[4] + Angle_1)
        Pos_2 = np.deg2rad(MiddlePos_2[5] + Angle_2)
        c.write_goal_position(15, Pos_1)
        c.write_goal_position(16, Pos_2)
        time.sleep(0.0002)


def Move_Thumb(Angle_1, Angle_2, Speed, Hand):
    if Hand == 1:  # Right hand finger
        c.write_goal_speed(7, Speed)
        time.sleep(0.0002)
        c.write_goal_speed(8, Speed)
        time.sleep(0.0002)
        Pos_1 = np.deg2rad(MiddlePos_1[6] + Angle_1)
        Pos_2 = np.deg2rad(MiddlePos_1[7] + Angle_2)
        c.write_goal_position(7, Pos_1)
        c.write_goal_position(8, Pos_2)
        time.sleep(0.0002)

    if Hand == 2:  # Left hand finger
        c.write_goal_speed(17, Speed)
        time.sleep(0.0002)
        c.write_goal_speed(18, Speed)
        time.sleep(0.0002)
        Pos_1 = np.deg2rad(MiddlePos_2[6] + Angle_1)
        Pos_2 = np.deg2rad(MiddlePos_2[7] + Angle_2)
        c.write_goal_position(17, Pos_1)
        c.write_goal_position(18, Pos_2)
        time.sleep(0.0002)
        

def FlexionExtension(posY, Hand, Finger):
    def move(motor_1_id, motor_2_id, posY):
        motor_1_pos = c.read_goal_position(motor_1_id)
        motor_2_pos = c.read_goal_position(motor_2_id)
        goal_1 = float(motor_1_pos[0]) + float(posY)
        goal_2 = float(motor_2_pos[0]) - float(posY)
        c.write_goal_position(motor_1_id, goal_1)
        c.write_goal_position(motor_2_id, goal_2)

    if Hand == 1:  # Right hand finger
        if Finger == "index":
            move(1, 2, posY)
        elif Finger == "middle":
            move(3, 4, posY)
        elif Finger == "ring":
            move(5, 6, posY)
        elif Finger == "thumb":
            move(7, 8, posY)
    elif Hand == 2:
        if Finger == "index":
            move(11, 12, posY)
        if Finger == "middle":
            move(13, 14, posY)
        if Finger == "ring":
            move(15, 16, posY)
        if Finger == "thumb":
            move(17, 18, posY)


def AbductionAdduction(posX, Hand, Finger):
    def move(motor_1_id, motor_2_id, posX, side):
        motor_1_pos = c.read_goal_position(motor_1_id)
        motor_2_pos = c.read_goal_position(motor_2_id)
        if side == "left":
            goal_1 = float(motor_1_pos[0]) - float(posX)
            goal_2 = float(motor_2_pos[0]) - float(posX)
        if side == "right":
            goal_1 = float(motor_1_pos[0]) + float(posX)
            goal_2 = float(motor_2_pos[0]) + float(posX)
        c.write_goal_position(motor_1_id, goal_1)
        c.write_goal_position(motor_2_id, goal_2)

    if Hand == 1:  # Right hand finger
        if Finger == "index":
            move(1, 2, posX, "right")
        elif Finger == "middle":
            move(3, 4, posX, "right")
        elif Finger == "ring":
            move(5, 6, posX, "right")
        elif Finger == "thumb":
            move(7, 8, posX, "right")
    elif Hand == 2:
        if Finger == "index":
            move(11, 12, posX, "left")
        if Finger == "middle":
            move(13, 14, posX, "left")
        if Finger == "ring":
            move(15, 16, posX, "left")
        if Finger == "thumb":
            move(17, 18, posX, "left")