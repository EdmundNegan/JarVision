# Description: This is the main script for the face tracking robot. It uses the URBasic library to control the robot and OpenCV to detect faces and objects in the video stream.
import math
import time
import cv2
from detection import find_faces_dnn, detect_objects_yolo
from detection import vs  # Ensure vs is properly initialized in detection module
from robot_control import set_lookorigin, move_to_face 
import conversation_handler as convo
from components.connection import initialize_robot
import threading
from imutils.video import VideoStream

"""SETTINGS AND VARIABLES ________________________________________________________________"""
ACCELERATION = 0.4  # Robot acceleration value
VELOCITY = 0.4  # Robot speed value
# The Joint position the robot starts at
robot_startposition = (math.radians(0),
                    math.radians(-78),
                    math.radians(-93),
                    math.radians(-15),
                    math.radians(90),
                    math.radians(0))
# Global variables
running = True
mode = "chatbot"
lock = threading.Lock()
robot_position = [0, 0]

def show_video():
    """Continuously show the video stream and handle modes."""
    global running, mode, robot_position
    current_mode = None # keep track of current mode
    while running:
        frame = vs.read()
        if frame is None:
            continue

        # Process frame based on mode
        with lock:
            if current_mode != mode:  # Mode has changed
                cv2.destroyAllWindows()  # Close the previous video stream window
                current_mode = mode  # Update the tracked current mode

        if current_mode == "face":
            target_positions, new_frame = find_faces_dnn(frame)
            if target_positions:
                robot_position = move_to_face(target_positions, robot_position, robot, origin)
            cv2.imshow("Face Tracking", new_frame)

        elif current_mode == "object":
            target_positions, labels, new_frame = detect_objects_yolo(frame)
            if target_positions:
                robot_position = move_to_face(target_positions, robot_position, robot, origin)
            cv2.imshow("Object Tracking", new_frame)

        else:  # Default mode
            cv2.imshow("Robot Camera View", frame)

        # Exit face/object tracking mode
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC key to switch back to chatbot
            with lock:
                mode = "chatbot"
            print("Switching back to chatbot mode.")

    cv2.destroyAllWindows()
    vs.stop()


def chatbot_interaction():
    """Handle chatbot interaction."""
    global running, mode
    print("Welcome to the UR Agent Chatbot!\nType 'face' to switch to face tracking mode or 'object' to switch to object detection mode.\nType 'exit' to quit the program.") 
    while running:
        question = input("You: ").strip()
        if question.lower() == 'exit':
            running = False
            break

        with lock:
            if "face" in question.lower():
                mode = "face"
                print("Agent: Switching to face tracking mode.\nPress 'ESC' to switch back to chatbot mode.")
            elif "object" in question.lower():
                mode = "object"
                print("Agent: Switching to object detection mode.\nPress 'ESC' to switch back to chatbot mode.")
            else:
                response = convo.handle_conversation(question)
                print(f"Agent: {response}")


if __name__ == "__main__":
    # Initialize the robot
    robot, socket_connection = initialize_robot()
    if not (robot and socket_connection):
        print("Failed to initialize robot")
        exit(1)

    robot.reset_error()
    time.sleep(1)
    robot.movej(q=robot_startposition, a=ACCELERATION, v=VELOCITY)
    origin = set_lookorigin(robot)
    robot.init_realtime_control()
    time.sleep(1)

    # Start threads
    video_thread = threading.Thread(target=show_video)
    chatbot_thread = threading.Thread(target=chatbot_interaction)
    video_thread.start()
    chatbot_thread.start()

    # Wait for threads to finish
    video_thread.join()
    chatbot_thread.join()