import cv2

cap = cv2.VideoCapture(0)  # Change 0 to 1 or 2 if needed

if not cap.isOpened():
    print("Error: Cannot access the webcam. Please check your camera setup.")
    exit(1)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    cv2.imshow("Test Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
