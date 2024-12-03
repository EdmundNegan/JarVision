import components.initializer as init
import URBasic
import socket

def initialize_robot():
    """
    Initializes the robot by establishing a socket connection and creating the URBasic robot object.

    Returns:
        tuple: A tuple containing the robot object and the socket connection, or (None, None) if an error occurs.
    """
    host = init.HOST
    port = int(init.PORT)
    print("Host: ", host)
    print("Port: ", port)

    # Initialize socket connection
    try:
        # Create the socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect to the robot
        s.connect((host, port))
        print(f"Connected to robot at {host}:{port}")
    except Exception as e:
        print(f"Error initializing socket connection: {e}")
        return None, None

    # Initialize the robot using URBasic
    try:
        robot_model = URBasic.robotModel.RobotModel()
        robot = URBasic.urScriptExt.UrScriptExt(host=host, robotModel=robot_model)
        robot.reset_error()
        print("Robot initialized and errors reset.")
        return robot, s
    except Exception as e:
        print(f"Error initializing robot: {e}")
        s.close()
        return None, None

