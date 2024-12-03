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
# Flag to control the threads
running = True

def show_video():
    """Continuously show the video stream."""
    global running
    while running:
        frame = vs.read()
        if frame is None:
            continue

        # Show the frame in a window
        cv2.imshow("Robot Camera View", frame)

        # Exit if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            running = False
            break

    # Clean up when exiting
    cv2.destroyAllWindows()
    vs.stop()

def chatbot_interaction():
    """Handle chatbot interaction."""
    global running
    print("Welcome to the UR Agent Chatbot! Type 'exit' to quit.")
    while running:
        question = input("You: ").strip()
        if question.lower() == 'exit':
            running = False
            break

        # Handle chatbot conversation
        response = convo.handle_conversation(question)
        print(f"Agent: {response}")


if __name__ == "__main__":
    # initialize the robot
    robot, socket_connection = initialize_robot()
    print("initialising robot")
    robot.reset_error()
    time.sleep(1)
    if robot and socket_connection:
        print("Robot initialized successfully")
    else:
        print("Failed to initialize robot")

    # Move Robot to the midpoint of the lookplane
    robot.movej(q=robot_startposition, a=ACCELERATION, v=VELOCITY)

    robot_position = [0,0]
    origin = set_lookorigin(robot)  # Set the origin of the robot coordinate system
    robot.init_realtime_control()  # starts the realtime control loop on the Universal-Robot Controller
    time.sleep(1) # just a short wait to make sure everything is initialised
    
    #################################################################################:          
    #################################################################################
    ############### start the agent chatbot and video stream threads ################
    video_thread = threading.Thread(target=show_video)
    chatbot_thread = threading.Thread(target=chatbot_interaction)
    video_thread.start()
    chatbot_thread.start()
    # Wait for both threads to complete
    video_thread.join()
    chatbot_thread.join()
