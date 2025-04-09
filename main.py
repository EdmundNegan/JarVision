import math
import time
import cv2
import threading
import sys
import json
import os
import pyttsx3  # Added for text-to-speech

from detection import find_faces_dnn, detect_objects_yolo # , get_depth_value_at
from detection import vs  # Ensure vs is properly initialized in detection module
from robot_control import set_lookorigin, move_to_face 
import conversation_handler as convo
from components.connection import initialize_robot
from imutils.video import VideoStream

# For voice input
from vosk import Model, KaldiRecognizer
import pyaudio

import components.initializer as init

# ---------------------------
# Text-to-Speech Function
# ---------------------------
def speak_text(text):
    """
    Convert text to speech using pyttsx3.
    This function initializes the engine, adjusts the speech rate, and speaks out the provided text.
    """
    engine = pyttsx3.init()
    rate = engine.getProperty('rate')
    engine.setProperty('rate', rate - 25)  # Slow down a bit if needed
    engine.say(text)
    engine.runAndWait()

# ---------------------------
# SETTINGS AND VARIABLES
# ---------------------------
ACCELERATION = 0.4  # Robot acceleration value
VELOCITY = 0.4      # Robot speed value
latest_joint_positions = [0.0, -1.36136, -1.62316, -0.26180, 1.57080, 0.0]     
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

# ---------------------------
# VIDEO STREAM HANDLING
# ---------------------------
def show_video():
    """Continuously show the video stream and handle modes."""
    global running, mode, robot_position
    current_mode = None  # Keep track of current mode
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
                # face_x, face_y = target_positions[0]
                # depth = get_depth_value_at(face_x, face_y)
                # print(f"Face is approximately {depth} mm away.")
                robot_position = move_to_face(target_positions, robot_position, robot, origin)
            cv2.imshow("Face Tracking", new_frame)

        elif current_mode == "object":
            target_positions, labels, new_frame = detect_objects_yolo(frame)
            if target_positions:
                # object_x, object_y = target_positions[0]
                # depth = get_depth_value_at(object_x, object_y)
                # print(f"Object is approximately {depth} mm away.")
                robot_position = move_to_face(target_positions, robot_position, robot, origin)
            cv2.imshow("Object Tracking", new_frame)

        else:  # Default mode
            cv2.imshow("Robot Camera View", frame)

        # Check for ESC key to switch back to chatbot mode
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC key pressed
            with lock:
                mode = "chatbot"
            speak_text("Switching back to chatbot mode.")

    cv2.destroyAllWindows()
    vs.stop()

# ---------------------------
# CONVERSATION THREADS
# ---------------------------
def text_conversation():
    """Handle text-based chatbot interaction with voice output."""
    global running, mode
    welcome_message = (
        "Welcome to the UR Agent Chatbot! "
        "Type 'face' to switch to face tracking mode or 'object' to switch to object detection mode. "
        "Type 'exit' to quit the program."
    )
    speak_text(welcome_message)
    while running:
        question = input("You: ").strip()
        if question.lower() == 'exit':
            speak_text("Goodbye!")
            running = False
            break

        with lock:
            if "face" in question.lower():
                mode = "face"
                speak_text("Switching to face tracking mode. Press ESC to switch back to chatbot mode.")
            elif "object" in question.lower():
                mode = "object"
                speak_text("Switching to object detection mode. Press ESC to switch back to chatbot mode.")
            else:
                response = convo.handle_conversation(question)
                speak_text(response)

def init_voice_input():
    """
    Initialize the Vosk model and audio stream.
    Returns the audio stream and recognizer.
    """
    vosk_model_path = os.path.abspath(init.VOSK_MODEL)
    model = Model(vosk_model_path)
    recognizer = KaldiRecognizer(model, 16000)
    mic = pyaudio.PyAudio()
    stream = mic.open(format=pyaudio.paInt16,
                      channels=1,
                      rate=16000,
                      input=True,
                      frames_per_buffer=8192)
    speak_text("Audio model compiled successfully. Ready for audio.")
    stream.start_stream()
    return stream, recognizer

def speechToText(stream, recognizer):
    """
    Capture a single phrase from the microphone and return its text representation.
    Returns None if the user says 'quit' or 'exit'.
    """
    while True:
        data = stream.read(4096, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            text = recognizer.Result()
        else:
            text = recognizer.PartialResult()

        if text:
            textDict = json.loads(text)
            if 'text' in textDict and textDict['text']:
                recognized_text = textDict['text'].strip().lower()
                if "quit" in recognized_text or "exit" in recognized_text:
                    return None
                return recognized_text

def voice_conversation():
    """Handle voice-based chatbot interaction with voice output."""
    global running, mode
    speak_text("Welcome to the UR Agent Voice Interface! Say 'quit' or 'exit' to stop.")
    stream, recognizer = init_voice_input()

    while running:
        user_input = speechToText(stream, recognizer)
        if user_input is None:
            speak_text("Goodbye!")
            running = False
            break

        with lock:
            if "face" in user_input:
                mode = "face"
                speak_text("Switching to face tracking mode. Press ESC to switch back to chatbot mode.")
            elif "object" in user_input:
                mode = "object"
                speak_text("Switching to object detection mode. Press ESC to switch back to chatbot mode.")
            else:
                response = convo.handle_conversation(user_input)
                speak_text(response)

# ---------------------------
# MAIN EXECUTION BLOCK
# ---------------------------
if __name__ == "__main__":
    # Choose conversation mode based on a command-line argument.
    # Run with "voice" to use voice input; otherwise, text input is used.
    conversation_mode = mode
    if len(sys.argv) > 1 and sys.argv[1].lower() == "voice":
        conversation_mode = "voice"

    # Initialize the robot and socket connection
    robot, socket_connection = initialize_robot()
    if not (robot and socket_connection):
        speak_text("Failed to initialize robot.")
        exit(1)

    robot.reset_error()
    time.sleep(1)
    robot.movej(q=robot_startposition, a=ACCELERATION, v=VELOCITY)
    origin = set_lookorigin(robot)
    robot.init_realtime_control()
    time.sleep(1)

    # Start threads: video thread is always started, conversation thread is based on selected mode.
    video_thread = threading.Thread(target=show_video)
    if conversation_mode == "voice":
        conversation_thread = threading.Thread(target=voice_conversation)
    else:
        conversation_thread = threading.Thread(target=text_conversation)
    
    video_thread.start()
    conversation_thread.start()

    # Wait for threads to finish before exiting
    video_thread.join()
    conversation_thread.join()
