# -*- coding: gbk -*-
import os
import sys
import glob
import threading
import time
import cv2
import numpy as np
import requests
from PySide6.QtGui import QImage, QPixmap
from log_manager import LogManager
from fall_detector import FallDetector
from light_control import LightController

SERVER_IP = "118.25.198.12"
SERVER_UPLOAD_URL = f"http://{SERVER_IP}:8000/upload_fall"

class CameraManager:
    PREVIEW_WIDTH = 640
    PREVIEW_HEIGHT = 360
    DETECT_INTERVAL = 0.15
    FALL_CONFIDENCE_THRESHOLD = 0.75
    FALL_DISPLAY_DURATION = 1.0

    def __init__(self, model_dir: str, picture_dir: str):
        self._preview_thread = None
        self._detect_thread = None
        self._preview_running = False
        self._detect_running = False
        self._frame_lock = threading.Lock()
        self._current_frame = None
        self._display_frame = None
        self._frame_ready = False
        self._detector = FallDetector(model_dir)
        self._picture_dir = picture_dir
        os.makedirs(picture_dir, exist_ok=True)
        self._fall_count = 0
        self._last_fall_save_time = 0
        self._fall_save_interval = 1.0
        self._current_camera_index = -1
        self._cached_detected = []
        self._detect_lock = threading.Lock()
        self._detect_frame = None
        self._detect_frame_lock = threading.Lock()
        self._preview_fps = 0
        self._detect_fps = 0
        self._light_controller = LightController()
        self._last_fall_time = 0
        self._last_fall_detected_time = 0
        LogManager.append_log("Camera manager initialized", "INFO")

    def is_models_loaded(self):
        return self._detector.models_loaded

    @staticmethod
    def detect_available_cameras(max_check: int = 10):
        available = []
        if sys.platform.startswith('linux'):
            devs = glob.glob('/dev/video*')
            devs = sorted(devs, key=lambda x: int(x.replace('/dev/video', '')))
            for d in devs:
                try:
                    idx = int(d.replace('/dev/video', ''))
                    cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
                    if cap.isOpened():
                        ret, f = cap.read()
                        if ret: available.append(idx)
                    cap.release()
                except:
                    continue
        else:
            for i in range(max_check):
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, f = cap.read()
                        if ret: available.append(i)
                    cap.release()
                except:
                    continue
        return available

    def start_preview(self, camera_index: int = None):
        self.stop_preview()
        if camera_index is None:
            cam_list = self.detect_available_cameras()
            if not cam_list: return False
            camera_index = cam_list[0]

        self._preview_running = True
        self._detect_running = True
        self._frame_ready = False
        self._fall_count = 0
        self._last_fall_save_time = 0
        self._last_fall_detected_time = 0
        self._current_camera_index = camera_index

        with self._detect_lock: self._cached_detected = []
        with self._detect_frame_lock: self._detect_frame = None
        with self._frame_lock:
            self._current_frame = None
            self._display_frame = None

        self._preview_thread = threading.Thread(target=self._preview_thread_func, args=(camera_index,), daemon=True)
        self._detect_thread = threading.Thread(target=self._detect_thread_func, daemon=True)
        self._preview_thread.start()
        self._detect_thread.start()
        time.sleep(0.1)
        LogManager.append_log(f"Camera started: {camera_index}", "INFO")
        return True

    def stop_preview(self):
        LogManager.append_log("Stopping camera...", "INFO")
        self._light_controller.turn_off()
        self._preview_running = False
        self._detect_running = False
        if self._preview_thread: self._preview_thread.join(timeout=2)
        if self._detect_thread: self._detect_thread.join(timeout=2)
        with self._frame_lock:
            self._current_frame = None
            self._display_frame = None
        LogManager.append_log("Camera stopped", "INFO")

    def _save_fall_detection(self, frame, detected):
        now = time.time()
        if now - self._last_fall_save_time < self._fall_save_interval:
            return
        self._last_fall_save_time = now
        out = FallDetector.draw_results(frame, detected, draw_timestamp=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        fn = f"fall_{ts}.jpg"
        fp = os.path.join(self._picture_dir, fn)
        cv2.imwrite(fp, out)
        LogManager.append_log(f"Fall saved: {fn}", "WARN")
        threading.Thread(target=self._upload, args=(fp, fn), daemon=True).start()

    def _upload(self, fp, fn):
        try:
            with open(fp, 'rb') as f:
                r = requests.post(SERVER_UPLOAD_URL, files={"file": (fn, f, "image/jpeg")}, timeout=10)
            if r.status_code == 200:
                LogManager.append_log(f"Upload OK: {fn}", "INFO")
        except:
            LogManager.append_log(f"Upload failed: {fn}", "ERROR")

    def _preview_thread_func(self, idx):
        if sys.platform.startswith('linux'):
            cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
        else:
            cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            LogManager.append_log("Camera open failed", "ERROR")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.PREVIEW_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.PREVIEW_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        for _ in range(5): cap.read()

        cnt = 0
        t0 = time.time()
        while self._preview_running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue
            cnt += 1
            now = time.time()
            with self._detect_lock:
                res = self._cached_detected.copy()
            if len(res) == 0 and (now - self._last_fall_detected_time) < self.FALL_DISPLAY_DURATION:
                with self._detect_lock:
                    res = self._cached_detected.copy()
            # 绘制结果
            if len(res) > 0:
                disp = FallDetector.draw_results(frame, res, only_down=True)
            else:
                disp = frame.copy()
            rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
            with self._frame_lock:
                self._current_frame = frame.copy()
                self._display_frame = rgb
            self._frame_ready = True
            with self._detect_frame_lock:
                self._detect_frame = frame.copy()
            # FPS统计
            if time.time() - t0 > 5:
                self._preview_fps = cnt / (time.time() - t0)
                t0 = time.time()
                cnt = 0
        cap.release()

    def _detect_thread_func(self):
        LogManager.append_log("Detection thread started", "INFO")
        last = 0
        cnt = 0
        t0 = time.time()
        err = 0
        while self._detect_running:
            now = time.time()
            # 自动关灯
            if self._light_controller.is_light_on and now - self._last_fall_time > 10:
                self._light_controller.turn_off()

            if now - last >= self.DETECT_INTERVAL:
                with self._detect_frame_lock:
                    if self._detect_frame is None:
                        time.sleep(0.05)
                        continue
                    f = self._detect_frame.copy()

                try:
                    persons = self._detector.detect_persons(f)
                    cnt += 1
                    err = 0
                    fall_persons = []
                    # 只保留跌倒的人
                    for p in persons:
                        if p['state'] == 'DOWN' and p['confidence'] >= self.FALL_CONFIDENCE_THRESHOLD:
                            fall_persons.append(p)
                    # 更新缓存的跌倒结果
                    with self._detect_lock:
                        self._cached_detected = fall_persons.copy()
                    # 如果检测到跌倒，更新最后检测时间
                    if len(fall_persons) > 0:
                        self._last_fall_detected_time = now
                        self._fall_count += len(fall_persons)
                        self._save_fall_detection(f, fall_persons)
                        self._light_controller.turn_on()
                        self._last_fall_time = now
                    last = now

                except Exception as e:
                    err += 1
                    LogManager.append_log(f"Detection error: {str(e)}", "ERROR")
                    if err > 10:
                        time.sleep(5)
                        err = 0
                    else:
                        time.sleep(0.5)
            else:
                time.sleep(0.01)

            if now - t0 > 5:
                self._detect_fps = cnt / (now - t0)
                t0 = now
                cnt = 0
        LogManager.append_log("Detection thread stopped", "INFO")

    def update_preview_frame(self, label):
        if not label or not self._frame_ready:
            return
        with self._frame_lock:
            if self._display_frame is None:
                return
            img = self._display_frame.copy()
        h, w, ch = img.shape
        qimg = QImage(img.data, w, h, ch * w, QImage.Format.Format_RGB888)
        label.setPixmap(QPixmap.fromImage(qimg))
        self._frame_ready = False

    def capture_frame(self):
        with self._frame_lock:
            if self._current_frame is None:
                return False, "No frame"
            f = self._current_frame.copy()
        persons = self._detector.detect_persons(f)
        fall_persons = [p for p in persons if p['state'] == 'DOWN']
        out = FallDetector.draw_results(f, fall_persons, draw_timestamp=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        fn = f"capture_{ts}.jpg"
        fp = os.path.join(self._picture_dir, fn)
        cv2.imwrite(fp, out)
        return True, fp

    def get_detection_stats(self):
        return {
            'fall': self._fall_count,
            'preview_fps': self._preview_fps,
            'detect_fps': self._detect_fps
        }

def mat_to_qimage(mat):
    if mat is None: return QImage()
    rgb = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB)
    h,w,c = rgb.shape
    return QImage(rgb.data, w, h, w*c, QImage.Format.Format_RGB888).copy()