# -*- coding: gbk -*-
import os
import warnings
import cv2
import numpy as np
import joblib
from ultralytics import YOLO
from log_manager import LogManager

warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

# 检测参数
MIN_CONFIDENCE = 0.4
MIN_KEYPOINTS = 10

YOLO_IMG_SIZE = 320

# 跌倒检测阈值
FALL_BODY_ANGLE_THRESHOLD = 55
FALL_HEIGHT_RATIO_THRESHOLD = 1.2
FALL_MIN_CONFIDENCE = 0.75
FALL_CONFIRM_FRAMES = 3

# 只检测跌倒
LABEL_NAMES = {2: "DOWN"}
STATE_TO_CN = {"DOWN": "跌倒"}
COLOR_MAP = {
    "DOWN": (0, 0, 255),
}


class FallDetector:
    def __init__(self, model_dir: str):
        self.pose_model = None
        self.classifier = None
        self.scaler = None
        self.models_loaded = False
        self._fall_history = {}
        self._max_history = FALL_CONFIRM_FRAMES
        self._load_models(model_dir)

    def _load_models(self, model_dir: str):
        try:
            pose_model_path = os.path.join(model_dir, "yolov8n-pose.pt")
            if not os.path.exists(pose_model_path):
                LogManager.append_log(f"Pose model not found: {pose_model_path}", "ERROR")
                return
            self.pose_model = YOLO(pose_model_path)
            LogManager.append_log("YOLOv8-Pose model loaded", "INFO")

            classifier_path = os.path.join(model_dir, "fall_multi_person_model.pkl")
            if not os.path.exists(classifier_path):
                LogManager.append_log(f"Classifier model not found: {classifier_path}", "ERROR")
                return

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.classifier = joblib.load(classifier_path)
                if hasattr(self.classifier, 'estimators_'):
                    for estimator in self.classifier.estimators_:
                        if not hasattr(estimator, 'monotonic_cst'):
                            estimator.monotonic_cst = None

            LogManager.append_log("Classifier model loaded", "INFO")

            scaler_path = os.path.join(model_dir, "feature_scaler_multi.pkl")
            if os.path.exists(scaler_path):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self.scaler = joblib.load(scaler_path)
                LogManager.append_log("Feature scaler loaded", "INFO")

            self.models_loaded = True
            LogManager.append_log("All models loaded successfully", "INFO")

        except Exception as e:
            LogManager.append_log(f"Failed to load models: {str(e)}", "ERROR")
            self.models_loaded = False

    @staticmethod
    def calculate_angle(p1, p2, p3):
        if p1 is None or p2 is None or p3 is None:
            return 180.0
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 180.0
        cos_angle = np.dot(v1, v2) / (norm1 * norm2)
        cos_angle = np.clip(cos_angle, -1, 1)
        return np.degrees(np.arccos(cos_angle))

    def extract_features(self, keypoints_norm, confidences):
        features = []
        for i in range(17):
            features.extend([keypoints_norm[i, 0], keypoints_norm[i, 1], confidences[i]])

        angle_defs = [
            (5, 7, 9), (6, 8, 10),
            (11, 5, 7), (12, 6, 8),
            (5, 11, 13), (6, 12, 14),
            (11, 13, 15), (12, 14, 16),
        ]

        for i1, i2, i3 in angle_defs:
            p1 = tuple(keypoints_norm[i1]) if confidences[i1] > MIN_CONFIDENCE else None
            p2 = tuple(keypoints_norm[i2]) if confidences[i2] > MIN_CONFIDENCE else None
            p3 = tuple(keypoints_norm[i3]) if confidences[i3] > MIN_CONFIDENCE else None
            angle = self.calculate_angle(p1, p2, p3)
            features.append(angle / 180.0)

        hip_x = (keypoints_norm[11, 0] + keypoints_norm[12, 0]) / 2
        hip_y = (keypoints_norm[11, 1] + keypoints_norm[12, 1]) / 2

        key_indices = [0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        for idx in key_indices:
            features.append(keypoints_norm[idx, 0] - hip_x)
            features.append(keypoints_norm[idx, 1] - hip_y)

        head_y = keypoints_norm[0, 1]
        ankle_y = max(keypoints_norm[15, 1], keypoints_norm[16, 1])
        body_height = abs(ankle_y - head_y)
        body_width = abs(keypoints_norm[5, 0] - keypoints_norm[6, 0])

        features.append(body_height)
        features.append(body_width)
        features.append(body_height / (body_width + 1e-6))

        return np.array(features, dtype=np.float32).reshape(1, -1)

    def detect_persons(self, image):
        if not self.models_loaded:
            return []

        h, w = image.shape[:2]
        try:
            results = self.pose_model(image, verbose=False, imgsz=YOLO_IMG_SIZE, device='cpu')
        except:
            return []

        detected = []
        for result in results:
            if result.keypoints is None:
                continue
            keypoints_data = result.keypoints.data.cpu().numpy()

            for kp in keypoints_data:
                xy = kp[:, :2]
                conf = kp[:, 2]
                valid_count = np.sum(conf > MIN_CONFIDENCE)
                if valid_count < MIN_KEYPOINTS:
                    continue

                core_indices = [0, 5, 6, 11, 12]
                core_valid = sum(1 for i in core_indices if conf[i] > MIN_CONFIDENCE)
                if core_valid < 4:
                    continue

                if not self._validate_body_structure(xy, conf):
                    continue

                xy_norm = xy.copy()
                xy_norm[:, 0] /= w
                xy_norm[:, 1] /= h

                features = self.extract_features(xy_norm, conf)
                if self.scaler is not None:
                    features = self.scaler.transform(features)

                pred_label = self.classifier.predict(features)[0]
                pred_proba = self.classifier.predict_proba(features)[0]
                pred_conf = pred_proba[pred_label]

                pred_conf = np.clip(pred_conf, 0.0, 1.0)
                pred_state = LABEL_NAMES.get(pred_label, "UNKNOWN")

                # 只保留跌倒
                if pred_state != "DOWN":
                    continue

                # 二次验证跌倒
                if pred_state == 'DOWN':
                    is_valid_fall, fall_conf = self._verify_fall_pose(xy, conf, h, w)
                    fall_conf = np.clip(fall_conf, 0.0, 1.0)
                    if not is_valid_fall:
                        continue
                    pred_conf = max(pred_conf, fall_conf)

                valid_mask = conf > MIN_CONFIDENCE
                valid_xy = xy[valid_mask]
                x1, y1 = valid_xy.min(axis=0)
                x2, y2 = valid_xy.max(axis=0)
                margin = 20
                x1 = max(0, int(x1 - margin))
                y1 = max(0, int(y1 - margin))
                x2 = min(w, int(x2 + margin))
                y2 = min(h, int(y2 + margin))

                detected.append({
                    'bbox': (x1, y1, x2, y2),
                    'state': pred_state,
                    'confidence': pred_conf,
                    'keypoints': xy,
                    'keypoints_conf': conf
                })
        return detected

    def _validate_body_structure(self, xy, conf):
        try:
            if conf[5] > MIN_CONFIDENCE and conf[6] > MIN_CONFIDENCE and conf[11] > MIN_CONFIDENCE and conf[12] > MIN_CONFIDENCE:
                shoulder_width = np.linalg.norm(xy[5] - xy[6])
                hip_width = np.linalg.norm(xy[11] - xy[12])
                if shoulder_width > 0 and hip_width > 0:
                    ratio = shoulder_width / hip_width
                    if ratio < 0.3 or ratio > 3.0:
                        return False
        except:
            pass
        return True

    def _verify_fall_pose(self, xy, conf, img_h, img_w):
        fall_score = 0.0
        max_score = 5.0

        try:
            if conf[5] > MIN_CONFIDENCE and conf[6] > MIN_CONFIDENCE and conf[11] > MIN_CONFIDENCE and conf[12] > MIN_CONFIDENCE:
                shoulder_center = (xy[5] + xy[6]) / 2
                hip_center = (xy[11] + xy[12]) / 2
                torso = shoulder_center - hip_center
                torso_norm = np.linalg.norm(torso)
                if torso_norm > 1e-6:
                    vertical = np.array([0, -1])
                    cos_angle = np.dot(torso, vertical) / torso_norm
                    body_angle = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))
                    if body_angle > FALL_BODY_ANGLE_THRESHOLD:
                        fall_score += 2.0
        except:
            pass

        try:
            if conf[0] > MIN_CONFIDENCE and conf[15] > MIN_CONFIDENCE and conf[16] > MIN_CONFIDENCE:
                head_y = xy[0, 1]
                ankle_y = max(xy[15, 1], xy[16, 1])
                body_height = abs(ankle_y - head_y)
                body_width = abs(xy[5, 0] - xy[6, 0])
                if body_width > 0:
                    ratio = body_height / body_width
                    if ratio < FALL_HEIGHT_RATIO_THRESHOLD:
                        fall_score += 2.0
        except:
            pass

        try:
            bottom = self._analyze_ground_contact(xy, conf, img_h, img_w)
            fall_score += bottom
            hori = self._analyze_horizontal_distribution(xy, conf, img_h, img_w)
            fall_score += hori
        except:
            pass

        confidence = fall_score / max_score
        return fall_score >= 3.0, confidence

    def _analyze_horizontal_distribution(self, xy, conf, img_h, img_w):
        score = 0.0
        pts = []
        keys = [0, 5, 6, 11, 12, 13, 14, 15, 16]
        for i in keys:
            if conf[i] > MIN_CONFIDENCE:
                pts.append((xy[i, 0], xy[i, 1]))
        if len(pts) < 4:
            return 0
        pts = np.array(pts)
        xv = np.var(pts[:, 0])
        yv = np.var(pts[:, 1])
        if yv <= 0:
            return 0
        r = xv / yv
        if r > 3: score += 2
        elif r > 1.5: score += 1
        yr = (pts[:, 1].max() - pts[:, 1].min()) / img_h
        if yr < 0.25: score += 1
        return max(0, score)

    def _analyze_ground_contact(self, xy, conf, img_h, img_w):
        score = 0.0
        bottom = img_h * 0.7
        cnt = 0
        total = 0
        keys = [0, 5, 6, 11, 12, 13, 14, 15, 16]
        for i in keys:
            if conf[i] > MIN_CONFIDENCE:
                total += 1
                if xy[i, 1] > bottom:
                    cnt += 1
        if total > 0 and cnt / total > 0.6:
            score += 1.5
        return score

    @staticmethod
    def draw_results(image, detected, draw_timestamp=False, only_down=True):
        import time
        img = image.copy()
        skeleton = [(0, 1), (0, 2), (1, 3), (2, 4),
                    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
                    (5, 11), (6, 12), (11, 12),
                    (11, 13), (13, 15), (12, 14), (14, 16)]

        for p in detected:
            state = p['state']
            if state != 'DOWN':
                continue
            x1, y1, x2, y2 = p['bbox']
            color = (0, 0, 255)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            kp = p['keypoints']
            kpc = p['keypoints_conf']
            for j1, j2 in skeleton:
                if kpc[j1] > MIN_CONFIDENCE and kpc[j2] > MIN_CONFIDENCE:
                    cv2.line(img, (int(kp[j1,0]), int(kp[j1,1])),
                             (int(kp[j2,0]), int(kp[j2,1])), color, 2)
            for j in range(17):
                if kpc[j] > MIN_CONFIDENCE:
                    cx, cy = int(kp[j,0]), int(kp[j,1])
                    cv2.circle(img, (cx, cy), 4, (255,255,255), -1)
                    cv2.circle(img, (cx, cy), 3, color, -1)
            cf = p['confidence']
            txt = f"FALL {cf:.0%}"
            cv2.rectangle(img, (x1, y1-25), (x1+120, y1), color, -1)
            cv2.putText(img, txt, (x1+5, y1-6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

        if draw_timestamp:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(img, ts, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 3)
            cv2.putText(img, ts, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        return img