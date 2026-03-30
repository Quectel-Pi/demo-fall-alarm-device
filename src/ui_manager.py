# -*- coding: gbk -*-
"""
UI管理类
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QSizePolicy, QTextEdit, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QFont, QTextCursor
from log_manager import LogManager
from camera_manager import CameraManager


# 预览尺寸
PREVIEW_WIDTH = 1280
PREVIEW_HEIGHT = 720


class ScalableLabel(QLabel):
    """可自适应比例缩放的预览标签，支持双击切换全屏"""
    
    def __init__(self, aspect_ratio=16/9, parent=None):
        super().__init__(parent)
        self._aspect_ratio = aspect_ratio
        self._pixmap = None
        self._cached_size = None
        self._cached_pixmap = None
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background:#333; color:white; border-radius:8px;")
        self.setAlignment(Qt.AlignCenter)
    
    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self._cached_size = None
        self._update_scaled_pixmap()
    
    def _update_scaled_pixmap(self):
        if not self._pixmap:
            return
        current_size = self.size()
        if self._cached_size == current_size and self._cached_pixmap:
            super().setPixmap(self._cached_pixmap)
            return
        img_w = self._pixmap.width()
        img_h = self._pixmap.height()
        scale = min(current_size.width() / img_w, current_size.height() / img_h)
        target_w = int(img_w * scale)
        target_h = int(img_h * scale)
        if target_w > 0 and target_h > 0:
            self._cached_pixmap = self._pixmap.scaled(
                target_w, target_h,
                Qt.KeepAspectRatio,
                Qt.FastTransformation
            )
            self._cached_size = current_size
            super().setPixmap(self._cached_pixmap)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap:
            self._update_scaled_pixmap()
    
    def hasHeightForWidth(self):
        return True
    
    def heightForWidth(self, width):
        return int(width / self._aspect_ratio)
    
    def get_scale_offset(self):
        if not self._pixmap:
            return 1.0, 0, 0
        img_w = self._pixmap.width()
        img_h = self._pixmap.height()
        label_w = self.width()
        label_h = self.height()
        scale = min(label_w / img_w, label_h / img_h)
        disp_w = img_w * scale
        disp_h = img_h * scale
        offset_x = (label_w - disp_w) / 2
        offset_y = (label_h - disp_h) / 2
        return scale, offset_x, offset_y
    
    def mouseDoubleClickEvent(self, event):
        """双击切换全屏/还原预览"""
        if event.button() == Qt.LeftButton:
            if hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), '_toggle_fullscreen_preview'):
                self.parent().parent()._toggle_fullscreen_preview()
        super().mouseDoubleClickEvent(event)


class UIManager(QWidget):
    """主界面管理类"""
    
    def setup_styles(self):
        """设置界面样式"""
        self.setStyleSheet("""
        QWidget {
            background-color: #1e1e2e;
            color: #cdd6f4;
            font-size: 12px;
        }
        QLabel {
            background-color: transparent;
        }
        /* 滚动区域样式 */
        QScrollArea {
            background-color: transparent;
            border: none;
        }
        QScrollBar:vertical {
            background-color: #313244;
            width: 10px;
            border-radius: 5px;
            margin: 2px;
        }
        QScrollBar::handle:vertical {
            background-color: #585b70;
            border-radius: 5px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #6c7086;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        #tips_label {
            background-color: #313244;
            color: #cdd6f4;
            font-size: 14px;
            border-radius: 8px;
            padding: 12px 15px;
            min-height: 40px;
            border: 2px solid #585b70;
            margin-bottom: 15px;
        }
        /* 统一的GroupBox样式 */
        QGroupBox {
            color: #89b4fa;
            font-weight: bold;
            border: 2px solid #585b70;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
            background-color: #313244;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            margin-top: 5px;
            margin-left: 5px;
            background: transparent;
            padding: 0 8px;
        }
        /* Log区域内部样式 */
        #log_text_edit {
            background-color: #1a1a28;
            color: #cdd6f4;
            font-family: Consolas, Monaco, monospace;
            font-size: 11px;
            border: none;
            border-radius: 0;
            padding: 8px;
            min-height: 140px;
        }
        /* 功能按钮样式 */
        QPushButton[func_btn=true] {
            background-color: #89b4fa;
            color: #1e1e2e;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 10px;
            font-size: 13px;
            min-height: 35px;
        }
        QPushButton[func_btn=true]:hover { background-color: #74c7ec; }
        QPushButton[func_btn=true]:pressed { background-color: #585b70; }
        /* 相机控制按钮 */
        QPushButton[start_btn=true] {
            background-color: #a6e3a1;
            color: #1e1e2e;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 10px;
            font-size: 14px;
            min-height: 40px;
        }
        QPushButton[start_btn=true]:hover { background-color: #94e08d; }
        QPushButton[start_btn=true]:pressed { background-color: #7dd674; }
        QPushButton[stop_btn=true] {
            background-color: #f38ba8;
            color: #1e1e2e;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 10px;
            font-size: 14px;
            min-height: 40px;
        }
        QPushButton[stop_btn=true]:hover { background-color: #f17499; }
        QPushButton[stop_btn=true]:pressed { background-color: #eb5f85; }
        QPushButton[capture_btn=true] {
            background-color: #f9c74f;
            color: #1e1e2e;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 10px;
            font-size: 14px;
            min-height: 40px;
        }
        QPushButton[capture_btn=true]:hover { background-color: #f7bc35; }
        QPushButton[capture_btn=true]:pressed { background-color: #f5b21b; }
        """)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_styles()
        
        # 获取路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        model_dir = os.path.join(project_dir, "model")
        picture_dir = os.path.join(project_dir, "picture")
        
        # 初始化相机管理器
        self._camera_manager = CameraManager(model_dir, picture_dir)
        
        # 全屏状态
        self._is_fullscreen_preview = False
        
        # 窗口配置
        self.setWindowTitle("Fall Alarm System")
        self._setup_window_size()
        
        # 初始化布局
        self._init_main_layout()
        
        # 初始化日志
        LogManager.append_log("Fall Alarm System starting...", "INFO")
        
        if self._camera_manager.is_models_loaded():
            LogManager.append_log("Models loaded successfully", "INFO")
            self.update_tips("Status: Ready - Click 'Start Camera' to begin detection [Ready]")
        else:
            LogManager.append_log("Models failed to load", "ERROR")
            self.update_tips("Status: Error - Models failed to load [Error]")
        
        # 定时器配置
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)
        self._preview_timer.start(33)  # 30 FPS
        
        # 日志刷新定时器
        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._refresh_log)
        self._log_timer.start(100)
        
        LogManager.append_log("UI initialized successfully", "INFO")
    
    def _setup_window_size(self):
        """根据屏幕大小自适应设置窗口尺寸"""
        screen = self.screen()
        if screen is None:
            self.setMinimumSize(800, 600)
            self.resize(1200, 800)
            return
        
        available_geometry = screen.availableGeometry()
        screen_width = available_geometry.width()
        screen_height = available_geometry.height()
        
        window_width = int(screen_width * 0.85)
        window_height = int(screen_height * 0.85)
        
        min_width = min(800, int(screen_width * 0.5))
        min_height = min(600, int(screen_height * 0.5))
        self.setMinimumSize(min_width, min_height)
        
        self.resize(
            min(window_width, screen_width - 50),
            min(window_height, screen_height - 50)
        )
        
        self._center_window(available_geometry)
    
    def _center_window(self, available_geometry: QRect):
        """将窗口居中显示"""
        window_width = self.width()
        window_height = self.height()
        x = available_geometry.x() + (available_geometry.width() - window_width) // 2
        y = available_geometry.y() + (available_geometry.height() - window_height) // 2
        self.move(x, y)
    
    def _init_main_layout(self):
        """初始化主布局"""
        main_v = QVBoxLayout(self)
        main_v.setContentsMargins(20, 20, 20, 20)
        main_v.setSpacing(10)
        
        self.tips_label = QLabel()
        self.tips_label.setObjectName("tips_label")
        self.tips_label.setTextFormat(Qt.RichText)
        self.tips_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        main_v.addWidget(self.tips_label)
        
  
        self.bottom_h_layout = QHBoxLayout()
        self.bottom_h_layout.setSpacing(20)
        self.bottom_h_layout.setStretch(6, 4)
        
    
        left_w = QWidget()
        left_v = QVBoxLayout(left_w)
        left_v.setContentsMargins(0, 0, 0, 0)
        left_v.setSpacing(15)
        
        self.preview_label = ScalableLabel(aspect_ratio=PREVIEW_WIDTH/PREVIEW_HEIGHT)
        self.preview_label.setText("Click 'Start Camera' to begin preview")
        left_v.addWidget(self.preview_label, stretch=8)
        
        # 控制按钮
        btn_w = QWidget()
        btn_v = QVBoxLayout(btn_w)
        btn_v.setSpacing(10)
        
        self.btn_start = QPushButton("Start Camera")
        self.btn_start.setProperty("start_btn", True)
        self.btn_start.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.btn_stop = QPushButton("Stop Camera")
        self.btn_stop.setProperty("stop_btn", True)
        self.btn_stop.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    
        
        btn_v.addWidget(self.btn_start)
        btn_v.addWidget(self.btn_stop)
        left_v.addWidget(btn_w, stretch=2)
        
        self.bottom_h_layout.addWidget(left_w)
        
        # ===== 右栏：日志区 =====
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.right_scroll.setFrameShape(QScrollArea.NoFrame)
        
        self.right_widget = QWidget()
        right_v = QVBoxLayout(self.right_widget)
        right_v.setContentsMargins(5, 0, 5, 0)
        right_v.setSpacing(10)
        
        # 日志区域
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(0, 0, 0, 0)
        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("log_text_edit")
        self.log_edit.setReadOnly(True)
        self.log_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.log_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.log_edit.setMinimumHeight(120)
        log_layout.addWidget(self.log_edit)
        right_v.addWidget(log_group, stretch=1)
        
        right_v.addStretch()
        
        self.right_scroll.setWidget(self.right_widget)
        self.bottom_h_layout.addWidget(self.right_scroll)
        main_v.addLayout(self.bottom_h_layout)
        
        # 绑定按钮事件
        self._bind_events()
    
    def _bind_events(self):
        """绑定按钮事件"""
        self.btn_start.clicked.connect(self._start_camera)
        self.btn_stop.clicked.connect(self._stop_camera)
    
    def _start_camera(self):
        """启动相机"""
        if not self._camera_manager.is_models_loaded():
            LogManager.append_log("Cannot start camera: Models not loaded", "ERROR")
            self.update_tips("Status: Error - Models not loaded [Error]")
            return
        
        # 自动检测并启动相机
        success = self._camera_manager.start_preview()
        if success:
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.update_tips("Status: Camera running - Detection active [Active]")
        else:
            LogManager.append_log("Failed to start camera", "ERROR")
            self.update_tips("Status: Error - No available camera found [Error]")
    
    def _stop_camera(self):
        """停止相机"""
        self._camera_manager.stop_preview()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.preview_label.clear()
        self.preview_label.setText("Click 'Start Camera' to begin preview")
        self.update_tips("Status: Camera stopped [Stopped]")
    
    def _capture_frame(self):
        success, message = self._camera_manager.capture_frame()
        if success:
            LogManager.append_log(f"Frame captured: {message}", "INFO")
            self.update_tips(f"Status: Frame captured successfully [Success]")
        else:
            LogManager.append_log(f"Capture failed: {message}", "ERROR")
            self.update_tips(f"Status: Capture failed - {message} [Error]")
    
    def _toggle_fullscreen_preview(self):
        """切换预览区全屏/还原状态"""
        self._is_fullscreen_preview = not self._is_fullscreen_preview
        
        if self._is_fullscreen_preview:
            self.bottom_h_layout.setStretch(0, 100)
            self.bottom_h_layout.setStretch(1, 0)
            self.right_scroll.hide()
            self.preview_label.setStyleSheet("background:#333; color:white; border-radius:0px;")
        else:
            self.bottom_h_layout.setStretch(0, 6)
            self.bottom_h_layout.setStretch(1, 4)
            self.right_scroll.show()
            self.preview_label.setStyleSheet("background:#333; color:white; border-radius:8px;")
    
    def update_tips(self, text):
        """更新提示信息"""
        self.tips_label.setText(text)
    
    def _update_preview(self):
        """更新预览画面"""
        self._camera_manager.update_preview_frame(self.preview_label)
        
    
    def _refresh_log(self):
        """刷新日志显示"""
        new_log_lines = LogManager.get_log_lines()
        
        html = """
        <style>
            body {
                background-color: #1a1a28;
                color: #cdd6f4;
                font-family: Consolas, monospace;
                font-size: 11px;
                line-height: 1.3;
                margin: 0;
                padding: 0;
            }
            .log-info { color: #cdd6f4; }
            .log-warn { color: #f9c74f; }
            .log-error { color: #f38ba8; }
            .log-debug { color: #89b4fa; }
        </style>
        <body>
        """
        
        for line in new_log_lines:
            if "[ERROR]" in line:
                html += f"<div class='log-error'>{line}</div>"
            elif "[WARN]" in line:
                html += f"<div class='log-warn'>{line}</div>"
            elif "[DEBUG]" in line:
                html += f"<div class='log-debug'>{line}</div>"
            else:
                html += f"<div class='log-info'>{line}</div>"
        
        html += "</body>"
        
        if self.log_edit.toHtml() != html:
            scroll = self.log_edit.verticalScrollBar()
            old_value = scroll.value()
            old_max = scroll.maximum()
            was_at_bottom = (old_value >= old_max - 5)
            
            self.log_edit.setHtml(html)
            
            if was_at_bottom:
                cursor = self.log_edit.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.log_edit.setTextCursor(cursor)
                self.log_edit.ensureCursorVisible()
            else:
                new_max = scroll.maximum()
                if new_max > 0:
                    new_value = int(old_value * new_max / max(old_max, 1))
                    scroll.setValue(new_value)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self._camera_manager.stop_preview()
        LogManager.append_log("Application closed", "INFO")
        event.accept()

