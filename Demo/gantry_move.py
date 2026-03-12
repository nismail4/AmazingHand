from dora import Node
import serial
import time

gantry = 0

def send_command(cmd):
    print(f"Sending: {cmd.strip()}")
    gantry.write(cmd.encode())
    response = gantry.readline().decode().strip() # Wait for Arduino to answer
    print(f"Arduino said: {response}")
# 1. Initialize Gantry (USB-A port)
# Verify the COM port in Device Manager; it will be different from the hand (COM8)
gantry = serial.Serial('COM5', 115200, timeout=1) 
time.sleep(2)
send_command("$X\n")     # Unlock the startup alarm
send_command("$H\n")
time.sleep(15)
send_command("G10 P0 L20 X0\n")
send_command("G10 P0 L20 Y0\n")
send_command("G90\n")    # Set to Absolute Mode (for tracking)
send_command("G21\n")    # Ensure we are in Millimeters

node = Node()

for event in node:
    if event["type"] == "INPUT" and event["id"] == "wrist_pos":
        # wrist[0] = X, wrist[1] = Y
        wrist = event["value"].to_pylist()
        wrist = wrist[0]
        print(wrist)

        wristx = wrist[0]
        wristy = wrist[1]

        if(wristx < 0.1):
            wristx = 0.1

        if (wristx > 0.9):
            wristx = 0.9
        
        if(wristy < 0.1):
            wristy = 0.1

        if (wristy > 0.9):
            wristy = 0.9
        
        # 2. Mapping to Workspace (Change 200 to your physical limit in mm)
        target_x = wristx * 330
        target_y = (1 - wristy) * 330 # Flip Y for correct camera orientation
        print(target_x,target_y)
        
        # 3. Send G-Code
        command = f"G0 X{target_x:.2f} Y{target_y:.2f}\n"
        if 'gantry' in globals():
            send_command(command)

