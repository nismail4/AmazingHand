from dora import Node
import serial
import time

# 1. Initialize Gantry (USB-A port)
# Verify the COM port in Device Manager; it will be different from the hand (COM8)
try:
    gantry = serial.Serial('COM5', 115200, timeout=0.1) 
    time.sleep(2)
    gantry.write(b"G90\n") # Set to Absolute Positioning
except:
    print("Gantry Arduino not found. Check COM port.")

node = Node()

for event in node:
    if event["type"] == "INPUT" and event["id"] == "wrist_pos":
        # wrist[0] = X, wrist[1] = Y
        wrist = event["value"].to_pylist()
        
        # 2. Mapping to Workspace (Change 200 to your physical limit in mm)
        target_x = wrist[0] * 200
        target_y = (1 - wrist[1]) * 200 # Flip Y for correct camera orientation
        
        # 3. Send G-Code
        command = f"G0 X{target_x:.2f} Y{target_y:.2f}\n"
        if 'gantry' in globals():
            gantry.write(command.encode())