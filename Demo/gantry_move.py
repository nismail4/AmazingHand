from dora import Node
import serial
import time

gantry = 0

def send_command(cmd):
    print(f"Sending: {cmd.strip()}")
    gantry.write(cmd.encode())

    timeout = time.time() + 2
    while time.time() < timeout:
        if gantry.in_waiting:
            response = gantry.readline().decode().strip()
            print(f"Arduino said: {response}")
            if "ok" in response or "ALARM" in response:
                return response
    return "TIMEOUT"
# 1. Initialize Gantry (USB-A port)
# Verify the COM port in Device Manager; it will be different from the hand (COM8)
gantry = serial.Serial('COM5', 115200, timeout=1) 
#time.sleep(2)
#send_command("$X\n")     # Unlock the startup alarm
#send_command("$H\n")
#time.sleep(90)
#send_command("G10 P0 L20 X0\n")
#send_command("G10 P0 L20 Y0\n")
#send_command("G90\n")    # Set to Absolute Mode (for tracking)
#send_command("G21\n")    # Ensure we are in Millimeters

# 1. Initialize and Home
send_command("$X\n") # Unlock startup alarm
print("Starting Homing Cycle...")
gantry.write(b"$H\n") # Start homing

# Instead of time.sleep(90), wait for the physical 'ok' from the homing finish
homing_complete = False
while not homing_complete:
    if gantry.in_waiting:
        line = gantry.readline().decode().strip()
        print(f"Homing status: {line}")
        if "ok" in line:
            homing_complete = True
    time.sleep(0.1)

# Post-Homing Setup
send_command("G90\n") # Absolute Mode
send_command("G21\n") # Millimeters

# --- Main Dora Loop ---
node = Node()
history_x, history_y = [], []
BUFFER_SIZE = 5
MOVE_THRESHOLD = 4.0  # mm (Adjust this: higher = steadier, lower = more sensitive)
SEND_INTERVAL = 0.04   # seconds (20Hz)
FEEDRATE = 8000        # mm/min adjust for gantry speed
SYNC_EVERY = 10
commands_sent = 0
last_target_x = 0
last_target_y = 0
last_send_time = 0

def send_init(cmd):
      gantry.write(cmd.encode())
      time.sleep(0.1)

send_init("G90\n") 
send_init("$110=5000\n") # Max speed X
send_init("$111=5000\n") # Max speed Y
send_init("$120=400\n")  # Acceleration X (High = Snappy)
send_init("$121=400\n")  # Acceleration Y (High = Snappy)

commands_sent = 0 
last_target_x = 0
last_target_y = 0
last_send_time = 0

print("Gantry ready. Starting loop...")

# --- Main Dora Loop ---
for event in node:
    if event["type"] == "INPUT" and event["id"] == "wrist_pos":
        try:
            # 1. Get Hand Pos
            val = event["value"].to_pylist()
            wrist = val[0] if isinstance(val[0], list) else val
            
            # 2. Map (330mm workspace)
            tx = (1 - max(0.1, min(0.9, wrist[0]))) * 330
            ty = (1 - max(0.1, min(0.9, wrist[1]))) * 330

            # 3. Micro-Smoothing
            history_x.append(tx); history_y.append(ty)
            if len(history_x) > BUFFER_SIZE:
                history_x.pop(0); history_y.pop(0)

            sx = sum(history_x) / len(history_x)
            sy = sum(history_y) / len(history_y)

            # 4. The Jogging Logic
            now = time.time()
            if now - last_send_time > SEND_INTERVAL:
                dx = abs(sx - last_target_x)
                dy = abs(sy - last_target_y)

                if dx > MOVE_THRESHOLD or dy > MOVE_THRESHOLD:
                    # THE SECRET SAUCE: 
                    # $J= (Jogging) is better than G0/G1 for real-time.
                    # It tells GRBL: "Go here now, and if a new $J comes, move there instead."
                    jog_cmd = f"$J=G21G90X{sx:.2f}Y{sy:.2f}F{FEEDRATE}\n"
                    gantry.write(jog_cmd.encode())
                    
                    last_target_x, last_target_y = sx, sy
                
                last_send_time = now

            # 5. Continuous Buffer Flush
            # If we don't read the 'ok' responses, the Arduino's output buffer fills up
            # and slows down the whole chip.
            if gantry.in_waiting:
                gantry.read_all()

        except Exception:
            continue

# for event in node:
#     if event["type"] == "INPUT" and event["id"] == "wrist_pos":
#         # Ensure we are converting the Arrow tensor/list correctly
#         try:
#             wrist_values = event["value"].to_pylist()
#             # If the output is a nested list like [[x, y]], take the first element
#             wrist = wrist_values[0] if isinstance(wrist_values[0], list) else wrist_values
            
#             wristx = wrist[0]
#             wristy = wrist[1]
#             print(f"Received Wrist: X={wristx:.2f}, Y={wristy:.2f}") # Debugging line
#         except Exception as e:
#             print(f"Data conversion error: {e}")
#             continue
#         # wrist[0] = X, wrist[1] = Y
#         wrist_values = event["value"].to_pylist()
#         wrist = wrist_values[0] if isinstance(wrist_values[0], list) else wrist_values
#         print(wrist)

#         wristx = wrist[0]
#         wristy = wrist[1]

#         if(wristx < 0.1):
#             wristx = 0.1

#         if (wristx > 0.9):
#             wristx = 0.9
        
#         if(wristy < 0.1):
#             wristy = 0.1

#         if (wristy > 0.9):
#             wristy = 0.9
        
#         # 2. Mapping to Workspace (Change 200 to your physical limit in mm)
#         target_x = (1 - wristx) * 330 #Flip X for gantry
#         target_y = (1 - wristy) * 330 # Flip Y for correct camera orientation
#         print(target_x,target_y)

#         history_x.append(target_x)
#         history_y.append(target_y)
#         if len(history_x) > BUFFER_SIZE:
#                 history_x.pop(0)
#                 history_y.pop(0)

#         smoothed_x = sum(history_x) / len(history_x)
#         smoothed_y = sum(history_y) / len(history_y)

#         current_time = time.time()
#         if current_time - last_send_time > SEND_INTERVAL:
            
#             # Calculate the delta (change) from the last move we actually sent
#             dx = abs(smoothed_x - last_target_x)
#             dy = abs(smoothed_y - last_target_y)

#             if dx > MOVE_THRESHOLD or dy > MOVE_THRESHOLD:
#                     # Construct and send the move
#                     command = f"G0 X{smoothed_x:.2f} Y{smoothed_y:.2f}\n"
#                     send_command(command)
                    
#                     # IMPORTANT: Update these so we have a new baseline for the next move
#                     last_target_x = smoothed_x
#                     last_target_y = smoothed_y
#                     last_send_time = current_time
#             else:
#                     # Optional: print for debugging to see if threshold is working
#                     # print(f"Ignored small move: dx={dx:.1f}, dy={dy:.1f}")
#                     pass

#             #command = f"G0 X{target_x:.2f} Y{target_y:.2f}\n"
#             # gantry.write(command.encode())
            
#             # Update the timestamp
#             # last_send_time = current_time
            
#             # Non-blocking clear of the 'ok' messages to keep the line fast
#             if gantry.in_waiting:
#                 gantry.read_all()
        
#         # 3. Send G-Code
#         # command = f"G0 X{target_x:.2f} Y{target_y:.2f}\n"
#         # if 'gantry' in globals():
#         #    send_command(command)

