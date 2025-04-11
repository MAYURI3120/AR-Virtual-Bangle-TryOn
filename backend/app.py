from flask import Flask, jsonify, Response, send_from_directory
from flask_cors import CORS
import cv2
import mediapipe as mp
import threading
import os
import time
import numpy as np
import math

app = Flask(__name__)
CORS(app)

# Detect working camera index
def find_camera_index():
    for i in range(5):  # Check camera indexes 0 to 4
        temp_cap = cv2.VideoCapture(i)
        if temp_cap.isOpened():
            print(f"Camera found at index {i}")
            temp_cap.release()
            return i
    print("Error: No working camera found.")
    exit(1)

CAMERA_INDEX = find_camera_index()

# OpenCV video capture
cap = cv2.VideoCapture(0)  # Use DirectShow for Windows stability

if not cap.isOpened():
    print("Error: Cannot access the webcam. Please check your camera setup.")
    exit(1)

print("Camera found at index 0")
print("Waiting for the camera to initialize...")
time.sleep(2)

# Mediapipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.5)

# Global wrist coordinates and lock for thread safety
wrist_coordinates = []
wrist_lock = threading.Lock()

def calculate_hand_rotation(hand_landmarks):
    # Extract key landmarks
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    index_base = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
    pinky_base = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]

    # Convert to numpy arrays
    wrist_point = np.array([wrist.x, wrist.y, wrist.z])
    index_point = np.array([index_base.x, index_base.y, index_base.z])
    pinky_point = np.array([pinky_base.x, pinky_base.y, pinky_base.z])

    # Compute vector directions
    hand_direction = index_point - pinky_point
    hand_normal = np.cross(hand_direction, wrist_point - index_point)

    # Normalize vectors
    hand_direction /= np.linalg.norm(hand_direction)
    hand_normal /= np.linalg.norm(hand_normal)

    # Compute angles
    yaw = np.arctan2(hand_direction[1], hand_direction[0])  # Left/Right rotation
    pitch = np.arcsin(hand_normal[2])  # Up/Down tilt
    roll = np.arctan2(hand_normal[1], hand_normal[0])  # Rotation around wrist axis

    #return {"yaw": float(yaw), "pitch": float(pitch), "roll": float(roll)}
    return {
        "yaw": float(yaw + np.radians(5)),  # Slightly adjust left-right rotation
        "pitch": float(pitch - np.radians(5)),  # Tilt slightly downward
        "roll": float(roll + np.radians(10))  # Correct wrist curvature
    }

def process_camera_feed():
    global wrist_coordinates
    while True:
        success, frame = cap.read()
        if not success:
            print("Warning: Failed to capture frame from the camera.")
            time.sleep(0.1)  # Prevent CPU overload
            continue

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        with wrist_lock:
            wrist_coordinates.clear()
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                    h, w, _ = frame.shape

                    rotation_angles = calculate_hand_rotation(hand_landmarks)

                    wrist_coordinates.append({
                       "x": int((wrist.x * w)-10),
                        #"x": int((w - (wrist.x * w)) - 10),  # Inverting X-axis
                        "y": int((wrist.y * h)+10),
                        #"y": int(h - (wrist.y * h) + 10),  # Inverting Y-axis
                        "z": wrist.z,
                        "yaw": rotation_angles["yaw"],
                        "pitch": rotation_angles["pitch"],
                         "roll": rotation_angles["roll"]
                    })

                    print(f"Updated Wrist Position: X={(wrist.x * w) - 10}, Y={(wrist.y * h) + 10}, Z={wrist.z}")
                    print(
                        f"Rotation Angles: Yaw={math.degrees(rotation_angles['yaw'])}, Pitch={math.degrees(rotation_angles['pitch'])}, Roll={math.degrees(rotation_angles['roll'])}")
        time.sleep(0.03)  # Reduce CPU usage

# Start the camera processing thread
camera_thread = threading.Thread(target=process_camera_feed, daemon=True)
camera_thread.start()

@app.route('/')
def home():
    return "Flask server is running! Use /get_wrist_coordinates or /video-feed."

@app.route('/get_wrist_coordinates', methods=['GET'])
def get_wrist_coordinates():
    with wrist_lock:
        if wrist_coordinates:
            for wrist in wrist_coordinates:
                wrist["yaw"] = math.radians(15)  # Temporary placeholder
                wrist["pitch"] = math.radians(-10)  # Temporary placeholder
                wrist["roll"] = math.radians(30)  # Temporary placeholder

            return jsonify({"wrists": wrist_coordinates})
        else:
            return jsonify({"message": "No hands detected"}), 404

def generate_video_feed():
    while True:
        success, frame = cap.read()
        if not success:
            print("Warning: Failed to capture frame.")
            time.sleep(0.1)
            continue

        with wrist_lock:
            if wrist_coordinates:
                for wrist in wrist_coordinates:
                    cv2.circle(frame, (wrist["x"], wrist["y"]), 5, (0, 255, 0), -1)

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video-feed', methods=['GET'])
def video_feed():
    return Response(generate_video_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Serve favicon
FRONTEND_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/src"))

if not os.path.exists(os.path.join(FRONTEND_FOLDER, 'favicon.ico')):
    print("Warning: favicon.ico not found in", FRONTEND_FOLDER)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(FRONTEND_FOLDER, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        cap.release()