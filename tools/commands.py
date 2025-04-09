from langchain_core.tools import tool
from openai import OpenAI
import time
import socket
import components.initializer as init
import cv2
import base64
import ast

client = OpenAI()
host = init.HOST
port = int(init.PORT)

workspace_limits = {
    "reach_radius": 0.5,  # Maximum reach in meters
    "joint_limits": {
        "base": [-6.28, 6.28],       # J1 in radians
        "shoulder": [-3.14, 3.14],   # J2 in radians
        "elbow": [-3.14, 3.14],      # J3 in radians
        "wrist1": [-6.28, 6.28],     # J4 in radians
        "wrist2": [-6.28, 6.28],     # J5 in radians
        "wrist3": [-6.28, 6.28]      # J6 in radians
    }
}

home_position = [0.0, -1.36136, -1.62316, -0.26180, 1.57080, 0.0]

# Global variable to track the current joint positions
current_position = home_position.copy()

def encode_image(image_path):
    """
    Encodes an image to a base64 string.
    
    Args:
        image_path (str): Path to the image file.

    Returns:
        str: Base64 encoded string of the image.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
      
@tool
def describe_vision(user_command):
    """
    Captures a frame from the robot's camera and sends it to the Vision API for analysis.

    Description:
        This tool is used to understand the environment through the robot's camera. It takes a picture
        from the video stream, sends it to the Vision API, and returns a description of what the camera sees.

    Args:
        user_command (str): The command to analyze the image captured by the robot's camera.

    Returns:
        str: A description of the captured image or an error message if the API call fails.
    """
    try:
        # Capture a frame from the video stream
        from detection import vs  # Assuming vs is initialized in the detection module
        frame = vs.read()
        if frame is None:
            return "Error: Unable to capture image from the camera."

        # Save the frame as an image
        image_path = "captured_frame.jpg"
        cv2.imwrite(image_path, frame)

        # Encode the image to base64
        base64_image = encode_image(image_path)

        # Send the request to the Vision API
        response = client.chat.completions.create(
            model="gpt-4o",  # Replace with the model supporting vision
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_command,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
        )

        # Extract and return the response content
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error using Vision API: {e}"

@tool
def send_command_to_robot(ur_script_command):
    """
    Sends a URScript command to the robot.

    Description:
        This tool sends a URScript command to the robot by establishing a socket
        connection directly within the function. The command is formatted and transmitted
        to the robot, ensuring it is executed as expected. Use this tool to control or 
        send instructions to the robot.

    Args:
        ur_script_command (str): The URScript command to be sent to the robot. 
                                 This should be a valid URScript command string.

    Returns:
        None
    """
    try:
        # Remove any code fences or extra whitespace
        ur_script_command = ur_script_command.strip('`').strip()

        # Print the command being sent
        print(f"Sending URScript command:\n{ur_script_command}")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            # Ensure the command ends with a newline character
            if not ur_script_command.endswith('\n'):
                ur_script_command += '\n'

            # Send the URScript command
            s.sendall(ur_script_command.encode('utf-8'))
        
            # Wait for the robot to process the command
            time.sleep(0.5)

    except Exception as e:
        print(f"Error sending command to robot: {e}")

# @tool
# def generate_urscript(user_command):
#     """
#     Generates URScript commands from a user's natural language input.

#     Description:
#         This tool uses the OpenAI API to convert natural language commands 
#         into URScript commands for controlling a UR3e robot. The tool ensures 
#         that generated commands adhere to predefined rules for safety and accuracy 
#         within the robot's operational boundaries.

#     Args:
#         user_command (str): The natural language command to be interpreted 
#                             into URScript code.

#     Returns:
#         str: The generated URScript command or a message indicating that the 
#              movement is not possible due to workspace limitations.
#     """

#     messages = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a robotic control assistant specialized in converting human language instructions into URScript commands for a UR3e robot.\n"
#                 "Follow these steps for every command:\n"
#                 "1. Retrieve the robot's current position using the URScript command get_actual_joint_positions().\n"
#                 "   - Use the retrieved joint positions as the starting point for all calculations.\n"
#                 "2. Analyze the user's intent and break it down into specific joint movements relative to the current position.\n"
#                 "   - If the user specifies a movement direction (e.g., 'move up', 'move forward') without a distance, assume a default distance of 0.1 meters.\n"
#                 "3. Translate the intent into robot terms by calculating the necessary joint angle adjustments for the movement.\n"
#                 "   - For example, if the user asks to move left by 300 degrees (converted to radians), you must calculate the corresponding joint movement.\n"
#                 "4. Ensure that the URScript command is generated as a single line. The robot software only understands commands written in one line.\n"
#                 "   - For example, instead of:\n"
#                 "       current_joint_positions = get_actual_joint_positions()\n"
#                 "       movej([current_joint_positions[0] + 300 * (3.14159 / 180), ...])\n"
#                 "     You must generate:\n"
#                 "       movej([get_actual_joint_positions()[0] + 300 * (3.14159 / 180), get_actual_joint_positions()[1], get_actual_joint_positions()[2], get_actual_joint_positions()[3], get_actual_joint_positions()[4], get_actual_joint_positions()[5]], a=1.0, v=0.5)\n"
#                 "5. Always use movej for all movements. You must never use movel or any other motion commands.\n"
#                 "6. Ensure the movement respects the robot's workspace limits (joint limits, reach radius).\n"
#                 "7. If the requested movement is still not feasible after calculations, explain why.\n\n"
#                 "Examples of using movej as a single-line command:\n"
#                 "- Example 1: Rotate the base joint (J1) by 300 degrees (converted to radians) from its current position:\n"
#                 "  movej([get_actual_joint_positions()[0] + 300 * (3.14159 / 180), get_actual_joint_positions()[1], get_actual_joint_positions()[2], get_actual_joint_positions()[3], get_actual_joint_positions()[4], get_actual_joint_positions()[5]], a=1.0, v=0.5)\n"
#                 "- Example 2: Move up by 0.1 meters relative to the current position:\n"
#                 "  Assume this involves adjusting J2. You must calculate the adjustment and generate:\n"
#                 "  movej([get_actual_joint_positions()[0], get_actual_joint_positions()[1] + calculated_offset, get_actual_joint_positions()[2], get_actual_joint_positions()[3], get_actual_joint_positions()[4], get_actual_joint_positions()[5]], a=1.2, v=0.8)\n"
#                 "- Example 3: Return to the home position:\n"
#                 "  movej([0.0, -1.36136, -1.62316, -0.26180, 1.57080, 0.0], a=1.0, v=0.5)\n\n"
#                 "The home position of the robot is [0.0, -1.36136, -1.62316, -0.26180, 1.57080, 0.0].\n\n"
#                 "For multi-step trajectories, generate sequential single-line movej commands relative to the robot's position at each step. "
#                 "Retrieve the current position dynamically within each command to ensure accuracy.\n\n"
#                 "If the user provides an ambiguous command (e.g., 'move up'), always calculate the movement relative to the current position. "
#                 "Provide only the URScript code unless movement is not possible."
#             )
#         },
#         {
#             "role": "user",
#             "content": f"Convert the following command into URScript:\n\n{user_command}"
#         }
#     ]

#     try:
#         completion = client.chat.completions.create(
#             model=init.DEFAULT_CHAT_MODEL,
#             messages=messages,
#             max_tokens=150,
#             temperature=0
#         )

#         ur_script_command = completion.choices[0].message.content.strip()
#         # Remove any code fences or markdown syntax
#         ur_script_command = ur_script_command.strip('').strip()
#         return ur_script_command
#     except Exception as e:
#         print(f"Error interpreting command: {e}")
#         return None



# safety limits
# base joint: -25 degrees to 25 degrees (should be within this range)
# shoulder (2nd) joint: -120 degrees to -70 degrees
# elbow joint: -120 degrees to -70 degrees

# @tool
# def generate_urscript_absolute(user_command):
#     """
#     Generates URScript commands from a user's natural language input using absolute movements.
#     The robot's current joint positions are stored in the global variable 'current_position'.
#     """
#     messages = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a robotic control assistant specialized in converting human language instructions "
#                 "into URScript commands for a UR3e robot.\n"
#                 "The robot's current joint positions are stored in the variable 'current_position'. Initially, "
#                 "this is set to [0.0, -1.36136, -1.62316, -0.26180, 1.57080, 0.0].\n"
#                 "Follow these steps for every command:\n"
#                 "1. Use current_position as the starting point for calculations.\n"
#                 "2. Analyze the user's intent and calculate the target absolute joint positions by applying "
#                 "the requested adjustments to current_position.\n"
#                 "- If the user requests the base (joint 1) to rotate clockwise, use a negative value.\n"
#                 "- If the user requests the base (joint 1) to rotate anticlockwise, use a positive value.\n\n"
#                 "3. Generate a single-line movej command using the computed absolute joint values (explicit numbers only).\n"
#                 "4. Ensure the command respects the robot's workspace limits.\n"
#                 "Provide only the URScript code as a single-line command unless the movement is not possible."
#             )
#         },
#         {
#             "role": "user",
#             "content": f"Convert the following command into URScript using current_position as the starting point:\n\n{user_command}"
#         }
#     ]

#     try:
#         completion = client.chat.completions.create(
#             model=init.DEFAULT_CHAT_MODEL,
#             messages=messages,
#             max_tokens=150,
#             temperature=0
#         )
#         ur_script_command = completion.choices[0].message.content.strip()
#         # Ensure the command is a single line
#         ur_script_command = " ".join(ur_script_command.split())
#         return ur_script_command
#     except Exception as e:
#         print(f"Error interpreting command: {e}")
#         return None
    
@tool
def generate_urscript_from_current_position(user_command: str):
    """
    Generates URScript from user input, using global current_position (initially
    [0.0, -1.36136, -1.62316, -0.26180, 1.57080, 0.0]) as the baseline.

    - Interprets commands like "rotate 40° clockwise" relative to current_position.
    - Computes absolute angles and returns a single-line movej command.
    - Respects workspace limits.

    Args:
        user_command (str): The natural language command.

    Returns:
        str: The URScript command or an explanation if not possible.
    """
    global current_position

    print(f"CURRENT POSITION: {current_position}")


    messages = [
        {
            "role": "system",
            "content": (
                "You are a robotic control assistant specialized in converting human language instructions "
                "into URScript commands for a UR3e robot.\n"
                "The robot's current joint positions are stored in the variable 'current_position'. Initially, "
                "this is set to [0.0, -1.36136, -1.62316, -0.26180, 1.57080, 0.0].\n"
                "Follow these steps for every command:\n"
                "1. Use current_position as the starting point for calculations.\n"
                "2. Analyze the user's intent and break it down into specific joint movements relative to "
                "the current position (e.g., 'move up', 'rotate left'). Determine which joint(s) need "
                "adjustment and by how much.\n"
                "3. Calculate the target absolute joint positions by applying these relative adjustments to "
                "the starting values.\n"
                "- If the user requests the base (joint 1) to rotate clockwise, use a negative value.\n"
                "- If the user requests the base (joint 1) to rotate anticlockwise, use a positive value.\n\n"
                "4. Generate a single-line movej command using the computed absolute joint values (explicit numbers only).\n"
                "5. Ensure the command respects the robot's workspace limits.\n"
                "Provide only the URScript code as a single-line command unless the movement is not possible.\n\n"
                "Examples:\n"
                " - Go Home: movej([0.0, -1.36136, -1.62316, -0.26180, 1.57080, 0.0], a=1.0, v=0.5)\n"
                " - Rotate Base Clockwise by 5 Degrees: movej([-0.0873, -1.36136, -1.62316, -0.26180, 1.57080, 0.0], a=1.4, v=1.05)\n"
                " - Rotate Base Anticlockwise by 5 Degrees: movej([0.0873, -1.36136, -1.62316, -0.26180, 1.57080, 0.0], a=1.4, v=1.05)\n"
                " - Move Up by 0.1 Meters: movej([0.0, -1.26136, -1.62316, -0.26180, 1.57080, 0.0], a=1.2, v=0.8)\n\n"
                f"The robot's current joint positions are: {current_position}\n"
            )
        },
        {
            "role": "user",
            "content": (
                f"Convert the following command, starting at current_position={current_position}:\n\n"
                f"{user_command}"
            )
        }
    ]

    try:
        completion = client.chat.completions.create(
            model=init.DEFAULT_CHAT_MODEL,
            messages=messages,
            max_tokens=150,
            temperature=0
        )
        ur_script_command = completion.choices[0].message.content.strip()
        # Make sure it's a single line
        ur_script_command = " ".join(ur_script_command.split())
        return ur_script_command
    except Exception as e:
        print(f"Error interpreting command: {e}")
        return None

@tool
def send_command_to_robot_and_update(ur_script_command, new_position=None, relative_change=None):
    """
    Sends a URScript command to the robot and updates the global current_position.
    """
    global current_position
    try:
        cmd = ur_script_command.strip('`').strip()
        print(f"Sending URScript command:\n{cmd}")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            if not cmd.endswith('\n'):
                cmd += '\n'
            s.sendall(cmd.encode('utf-8'))
            time.sleep(0.5)

        # Update current_position if new_position or relative_change is provided.
        if new_position is not None:
            current_position = new_position.copy()
        elif relative_change is not None:
            # relative_change must be a list of numeric deltas, e.g. [-0.7854, 0, 0, 0, 0, 0]
            current_position = [cur + delta for cur, delta in zip(current_position, relative_change)]
        else:
            # Attempt to extract absolute joint values from the URScript command.
            start = cmd.find('[')
            end = cmd.find(']')
            if start != -1 and end != -1:
                list_str = cmd[start:end+1]
                try:
                    parsed = ast.literal_eval(list_str)
                    if isinstance(parsed, list) and len(parsed) == 6:
                        current_position = parsed
                    else:
                        print("Parsed joint positions are not valid.")
                except Exception as parse_err:
                    print(f"Failed to parse joint positions: {parse_err}")

        print(f"Updated current_position: {current_position}")

    except Exception as e:
        print(f"Error sending command to robot: {e}")