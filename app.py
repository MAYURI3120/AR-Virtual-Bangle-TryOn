from flask import Flask, jsonify, Response
from flask_cors import CORS
import cv2
import mediapipe as mp
import threading

app = Flask(__name__)
CORS(app)

# Mediapipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5)

# OpenCV video capture
cap = cv2.VideoCapture(0)

wrist_coordinates = []

def process_camera_feed():
    global wrist_coordinates
    while True:
        success, frame = cap.read()
        if not success:
            continue

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        wrist_coordinates = []

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                h, w, _ = frame.shape
                wrist_coordinates.append({
                    "x": int(wrist.x * w),
                    "y": int(wrist.y * h)
                })

camera_thread = threading.Thread(target=process_camera_feed, daemon=True)
camera_thread.start()

@app.route('/get-wrist-coordinates', methods=['GET'])
def get_wrist_coordinates():
    if wrist_coordinates:
        return jsonify({"wrists": wrist_coordinates})
    else:
        return jsonify({"message": "No hands detected"}), 404

def generate_video_feed():
    while True:
        success, frame = cap.read()
        if not success:
            continue

        if wrist_coordinates:
            for wrist in wrist_coordinates:
                cv2.circle(frame, (wrist["x"], wrist["y"]), 10, (0, 255, 0), -1)

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video-feed', methods=['GET'])
def video_feed():
    return Response(generate_video_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
