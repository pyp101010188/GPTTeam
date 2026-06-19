import torch, cv2

model = torch.hub.load('ultralytics/yolov5', 'custom', path='best.pt')
model.conf = 0.4

cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if not ret: break
    results = model(frame)
    annotated = results.render()[0]
    cv2.imshow('YOLOv5', annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()