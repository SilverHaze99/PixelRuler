import sys
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import numpy as np
import cv2

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QSplitter, QFileDialog,
    QMessageBox, QInputDialog, QComboBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QScrollArea, QToolBar, QStatusBar, QDialog, QDialogButtonBox,
    QListWidgetItem, QLineEdit
)
from PySide6.QtCore import Qt, QPoint, QRect, Signal, QTimer, QPointF
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, QWheelEvent,
    QMouseEvent, QAction, QIcon, QFont, QPaintEvent, QCloseEvent, QKeySequence, QKeyEvent
)

# Globale Variable für den Asset-Pfad
ASSETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# Reference object database (bleibt unverändert)
REFERENCE_OBJECTS = {
    "iPhone 14": {"length": 147.5, "width": 71.5, "unit": "mm"},
    "iPhone 15": {"length": 147.6, "width": 71.6, "unit": "mm"},
    "Samsung Galaxy S24": {"length": 147.0, "width": 70.6, "unit": "mm"},
    "Credit Card": {"length": 85.60, "width": 53.98, "unit": "mm"},
    "Cigarette Pack": {"length": 87.0, "width": 55.0, "unit": "mm"},
    "Euro Coin (1€)": {"diameter": 23.25, "unit": "mm"},
    "US Quarter": {"diameter": 24.26, "unit": "mm"},
    "Standard Pen": {"length": 140.0, "unit": "mm"},
    "Custom": {"length": 0, "width": 0, "unit": "mm"}
}


class ReferenceObjectDialog(QDialog):
    # (Dieser Code bleibt unverändert)
    """Dialog for selecting or creating a reference object."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reference Object Selection")
        self.setMinimumWidth(400)
        self.reference_object = None
        
        # Dark theme styling for the dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #353535;
            }
            QLabel {
                color: white;
            }
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QComboBox:hover {
                border: 1px solid #2a82da;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #2a82da;
                border: 1px solid #555;
            }
            QLineEdit {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #2a82da;
            }
            QDoubleSpinBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #2a82da;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #2a82da;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
        """)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        ref_widget = QWidget()
        ref_layout = QFormLayout(ref_widget)
        
        self.object_combo = QComboBox()
        self.object_combo.addItems(REFERENCE_OBJECTS.keys())
        self.object_combo.currentTextChanged.connect(self.on_object_changed)
        ref_layout.addRow("Object:", self.object_combo)
        
        self.custom_widget = QWidget()
        custom_layout = QFormLayout(self.custom_widget)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter custom object name")
        self.length_input = QDoubleSpinBox()
        self.length_input.setRange(0.01, 10000)
        self.length_input.setSuffix(" mm")
        self.length_input.setValue(100)
        
        custom_layout.addRow("Name:", self.name_input)
        custom_layout.addRow("Length:", self.length_input)
        
        self.custom_widget.setVisible(False)
        ref_layout.addRow(self.custom_widget)
        
        layout.addWidget(ref_widget)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_object_changed(self, text):
        self.custom_widget.setVisible(text == "Custom")
    
    def get_reference_object(self) -> Optional[Dict]:
        selected = self.object_combo.currentText()
        
        if selected == "Custom":
            name = self.name_input.text().strip()
            length = self.length_input.value()
        
            if not name:
                custom_count = 1
                parent_window = self.parent()
                if parent_window and hasattr(parent_window, 'canvas'):
                    for m in parent_window.canvas.measurements:
                        if m.get('reference_object') and m['reference_object'].get('name', '').startswith('Custom Object'):
                            custom_count += 1
                name = f"Custom Object {custom_count}"
            
            if length > 0:
                return {"name": name, "length": length, "unit": "mm"}
            return None
        else:
            obj_data = REFERENCE_OBJECTS[selected].copy()
            obj_data["name"] = selected
            return obj_data


class ImageCanvas(QLabel):
    """Custom canvas widget for image display and interaction."""
    
    mouse_moved = Signal(int, int, int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555;")
        
        # --- FIX START: Fokus-Policy setzen, damit das Widget Tastendrücke empfängt ---
        self.setFocusPolicy(Qt.StrongFocus)
        # --- FIX ENDE ---
        
        self.cv_image = None
        self.display_pixmap = None
        
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.offset = QPointF(0.0, 0.0)
        self.pan_start = None
        self.mode = "measure"
        
        self.space_pan_active = False
        
        self.points: List[Tuple[float, float]] = []
        self.measurements: List[Dict] = []
        self.show_measurements = True
        
        self.setMouseTracking(True)
        self.current_mouse_pos = QPoint(0, 0)
        
        self.setCursor(Qt.CrossCursor)
    
    # --- FIX START: Tastendrücke direkt im Canvas verarbeiten ---
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.space_pan_active = True
            self.setCursor(Qt.OpenHandCursor)
            self.update() # Um z.B. die Live-Linie auszublenden
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.space_pan_active = False
            self.pan_start = None # Wichtig, um das Ziehen zu beenden
            self.set_mode(self.mode) # Setzt den Cursor auf den des aktuellen Werkzeugs zurück
            self.update() # Um z.B. die Live-Linie wieder einzublenden
        else:
            super().keyReleaseEvent(event)
    # --- FIX ENDE ---

    def load_image(self, file_path: str) -> bool:
        self.cv_image = cv2.imread(file_path)
        if self.cv_image is None: return False
        
        self.reset_view()
        self.points = []
        self.measurements = []
        self.update_display()
        return True

    def get_image_size(self) -> Optional[Tuple[int, int]]:
        if self.cv_image is not None:
            return (self.cv_image.shape[1], self.cv_image.shape[0])
        return None

    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)
        if not self.display_pixmap: return
            
        painter = QPainter(self)
        x = (self.width() - self.display_pixmap.width()) / 2 + self.offset.x()
        y = (self.height() - self.display_pixmap.height()) / 2 + self.offset.y()
        painter.drawPixmap(QPoint(int(x), int(y)), self.display_pixmap)

        if len(self.points) % 2 == 1 and self.mode == "measure" and not self.space_pan_active:
            start_point_img = self.points[-1]
            start_point_pixmap = self.to_screen_coords(start_point_img[0], start_point_img[1])
            start_x_widget = x + start_point_pixmap[0]
            start_y_widget = y + start_point_pixmap[1]
            
            end_point_widget = self.current_mouse_pos
            
            pen = QPen(QColor("yellow"), 1, Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(start_x_widget), int(start_y_widget), end_point_widget.x(), end_point_widget.y())

    def to_image_coords(self, screen_pos: QPointF) -> Tuple[float, float]:
        if self.cv_image is None or self.display_pixmap is None: return (0, 0)
        
        pixmap_origin_x = (self.width() - self.display_pixmap.width()) / 2 + self.offset.x()
        pixmap_origin_y = (self.height() - self.display_pixmap.height()) / 2 + self.offset.y()
        
        img_x = (screen_pos.x() - pixmap_origin_x) / self.zoom_factor
        img_y = (screen_pos.y() - pixmap_origin_y) / self.zoom_factor
        
        img_x = max(0, min(img_x, self.cv_image.shape[1]))
        img_y = max(0, min(img_y, self.cv_image.shape[0]))
        
        return (img_x, img_y)

    def to_screen_coords(self, img_x: float, img_y: float) -> Tuple[int, int]:
        if self.cv_image is None: return (0, 0)
        return (int(img_x * self.zoom_factor), int(img_y * self.zoom_factor))
    
    def update_display(self):
        if self.cv_image is None: return
        
        scaled_width = int(self.cv_image.shape[1] * self.zoom_factor)
        scaled_height = int(self.cv_image.shape[0] * self.zoom_factor)
        
        if scaled_width <= 0 or scaled_height <= 0: return
        
        interpolation = cv2.INTER_AREA if self.zoom_factor < 1.0 else cv2.INTER_LINEAR
        scaled_image = cv2.resize(self.cv_image, (scaled_width, scaled_height), interpolation=interpolation)
        
        height, width, channel = scaled_image.shape
        bytes_per_line = 3 * width
        rgb_image = cv2.cvtColor(scaled_image, cv2.COLOR_BGR2RGB)
        q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        if self.show_measurements:
            painter = QPainter(pixmap)
            self.draw_measurements(painter)
            painter.end()
        
        self.display_pixmap = pixmap
        self.update()

    def draw_measurements(self, painter: QPainter):
        # (Dieser Code bleibt unverändert)
        colors = [
            QColor(0, 255, 0), QColor(255, 0, 0), QColor(0, 0, 255),
            QColor(255, 255, 0), QColor(255, 0, 255), QColor(0, 255, 255)
        ]
        for i, m in enumerate(self.measurements):
            color = colors[i % len(colors)]
            pen = QPen(color, max(2, int(2 * self.zoom_factor)))
            painter.setPen(pen)
            
            start_x, start_y = self.to_screen_coords(m["start"]["x"], m["start"]["y"])
            end_x, end_y = self.to_screen_coords(m["end"]["x"], m["end"]["y"])
            painter.drawLine(start_x, start_y, end_x, end_y)
            
            radius = max(3, int(4 * self.zoom_factor))
            painter.setBrush(color)
            painter.drawEllipse(QPoint(start_x, start_y), radius, radius)
            painter.drawEllipse(QPoint(end_x, end_y), radius, radius)
            
            if self.zoom_factor > 0.3:
                mid_x = (start_x + end_x) / 2
                mid_y = (start_y + end_y) / 2
                text = f"#{m['id']}: {m['pixel_length']:.1f}px"
                if m.get("real_world_length"):
                    unit = m["reference_object"].get("unit", "mm")
                    text += f"\n{m['real_world_length']:.1f}{unit}"
                font = QFont("Arial", max(8, int(10 * self.zoom_factor)))
                painter.setFont(font)
                painter.drawText(int(mid_x), int(mid_y - 10), text)
    
    def mousePressEvent(self, event: QMouseEvent):
        if self.cv_image is None: return

        if self.space_pan_active and event.button() == Qt.LeftButton:
            self.pan_start = event.position()
            # --- FIX: Korrekter Cursor-Name ---
            self.setCursor(Qt.ClosedHandCursor)
            return

        if self.mode == "pan" or event.button() == Qt.MiddleButton:
            if event.button() == Qt.LeftButton or event.button() == Qt.MiddleButton:
                self.pan_start = event.position()
                # --- FIX: Korrekter Cursor-Name ---
                self.setCursor(Qt.ClosedHandCursor)
                return

        if event.button() == Qt.LeftButton and self.mode == "measure":
            img_x, img_y = self.to_image_coords(event.position())
            self.points.append((img_x, img_y))
            
            if len(self.points) % 2 == 0:
                start, end = self.points[-2], self.points[-1]
                pixel_length = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
                measurement = {
                    "id": len(self.measurements) + 1, "start": {"x": start[0], "y": start[1]},
                    "end": {"x": end[0], "y": end[1]}, "pixel_length": pixel_length,
                    "timestamp": datetime.now().isoformat(), "reference_object": None,
                    "real_world_length": None, "scale_factor": None
                }
                self.handle_new_measurement(measurement)
            
            self.update()

    def handle_new_measurement(self, measurement: Dict):
        # (Dieser Code bleibt unverändert)
        main_window = self.window()
        if not isinstance(main_window, PixelRulerMainWindow): return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Reference Object?")
        msg_box.setText("Is this measurement a reference object?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        msg_box.setStyleSheet("QMessageBox { background-color: #353535; } QMessageBox QLabel { color: white; } QPushButton { background-color: #2a2a2a; color: white; border: 1px solid #555; padding: 5px 15px; border-radius: 3px; } QPushButton:hover { background-color: #3a3a3a; border: 1px solid #2a82da; }")
        
        reply = msg_box.exec()

        ref_obj = None
        if reply == QMessageBox.Yes:
            dialog = ReferenceObjectDialog(self)
            if dialog.exec():
                ref_obj = dialog.get_reference_object()
            else:
                if len(self.points) >= 2: self.points.pop(); self.points.pop()
                self.update()
                main_window.status_bar.showMessage("Measurement cancelled.")
                return

        if ref_obj:
            pixel_length = measurement["pixel_length"]
            if pixel_length > 0:
                real_length = ref_obj.get("length") or ref_obj.get("diameter")
                if real_length:
                    scale_factor = real_length / pixel_length
                    measurement["scale_factor"] = float(scale_factor)
                    measurement["real_world_length"] = float(pixel_length * scale_factor)
            measurement["reference_object"] = ref_obj
        
        main_window.add_measurement_with_history(measurement)

    def mouseMoveEvent(self, event: QMouseEvent):
        self.current_mouse_pos = event.position().toPoint()
        if self.cv_image is not None:
            img_x, img_y = self.to_image_coords(event.position())
            self.mouse_moved.emit(self.current_mouse_pos.x(), self.current_mouse_pos.y(), int(img_x), int(img_y))
        
        if self.pan_start is not None:
            delta = event.position() - self.pan_start
            self.offset += delta
            self.pan_start = event.position()
            self.update()
        
        if self.mode == "measure" and len(self.points) % 2 == 1:
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.pan_start is not None:
            if self.space_pan_active or self.mode == 'pan':
                self.setCursor(Qt.OpenHandCursor)
        self.pan_start = None
        self.update()
    
    def wheelEvent(self, event: QWheelEvent):
        # (Dieser Code bleibt unverändert)
        if self.cv_image is None: return

        mouse_pos = event.position()
        img_coord_before_zoom = self.to_image_coords(mouse_pos)

        if event.angleDelta().y() > 0: self.zoom_factor *= 1.15
        else: self.zoom_factor /= 1.15
        self.zoom_factor = max(self.min_zoom, min(self.zoom_factor, self.max_zoom))

        new_pixmap_width = self.cv_image.shape[1] * self.zoom_factor
        new_pixmap_height = self.cv_image.shape[0] * self.zoom_factor
        center_x = (self.width() - new_pixmap_width) / 2
        center_y = (self.height() - new_pixmap_height) / 2
        
        new_offset_x = mouse_pos.x() - center_x - (img_coord_before_zoom[0] * self.zoom_factor)
        new_offset_y = mouse_pos.y() - center_y - (img_coord_before_zoom[1] * self.zoom_factor)
        self.offset = QPointF(new_offset_x, new_offset_y)

        self.update_display()
    
    def delete_last_measurement(self):
        if self.measurements:
            deleted_measurement = self.measurements.pop()
            if len(self.points) >= 2: self.points.pop(); self.points.pop()
            self.update_display()
            return deleted_measurement
        return None
    
    def clear_measurements(self):
        old_measurements = self.measurements[:]
        self.measurements = []
        self.points = []
        self.update_display()
        return old_measurements
    
    def toggle_measurements(self):
        self.show_measurements = not self.show_measurements
        self.update_display()
    
    def reset_view(self):
        self.zoom_factor = 1.0
        self.offset = QPointF(0, 0)
        self.update_display()
    
    def set_mode(self, mode: str):
        self.mode = mode
        if mode == "pan": self.setCursor(Qt.OpenHandCursor)
        else: self.setCursor(Qt.CrossCursor)


class PixelRulerMainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PixelRuler - Professional Measurement Tool")
        self.setGeometry(100, 100, 1400, 900)
        
        if not os.path.exists(ASSETS_PATH):
            print(f"Warning: 'assets' directory not found at {ASSETS_PATH}. Icons will not be loaded.")
            self.assets_available = False
        else:
            self.assets_available = True
        
        self.setWindowIcon(self.get_icon("app-icon"))
        
        self.current_image_path = ""
        self.is_dirty = False
        
        self.undo_stack = []
        self.redo_stack = []
        
        self.init_ui()
    
    def get_icon(self, name: str) -> QIcon:
        """Loads an icon from the assets folder, supporting both svg and png."""
        if not self.assets_available: return QIcon()
        for ext in ['svg', 'png']:
            path = os.path.join(ASSETS_PATH, f"{name}.{ext}")
            if os.path.exists(path): return QIcon(path)
        print(f"Warning: Icon '{name}' not found in assets folder.")
        return QIcon()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        self.canvas = ImageCanvas()
        self.canvas.mouse_moved.connect(self.on_mouse_moved)
        splitter.addWidget(self.canvas)
        
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        splitter.setSizes([1000, 400])
        main_layout.addWidget(splitter)
        
        self.create_toolbar()
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Load an image to begin")
    
    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        load_action = QAction(self.get_icon("folder-open"), "Load Image", self)
        save_meas_action = QAction(self.get_icon("save"), "Save Measurements", self)
        save_img_action = QAction(self.get_icon("image"), "Save Annotated Image", self)
        
        load_action.triggered.connect(self.load_image)
        save_meas_action.triggered.connect(self.save_measurements)
        save_img_action.triggered.connect(self.save_annotated_image)
        
        toolbar.addAction(load_action)
        toolbar.addAction(save_meas_action)
        toolbar.addAction(save_img_action)
        toolbar.addSeparator()
        
        measure_action = QAction(self.get_icon("edit-2"), "Measure", self)
        measure_action.setCheckable(True); measure_action.setChecked(True)
        measure_action.triggered.connect(lambda: self.set_tool("measure"))
        toolbar.addAction(measure_action)
        
        pan_action = QAction(self.get_icon("move"), "Pan", self)
        pan_action.setCheckable(True)
        pan_action.triggered.connect(lambda: self.set_tool("pan"))
        toolbar.addAction(pan_action)
        self.tool_actions = [measure_action, pan_action]
        
        toolbar.addSeparator()

        self.undo_action = QAction(self.get_icon("corner-up-left"), "Undo", self)
        self.redo_action = QAction(self.get_icon("corner-up-right"), "Redo", self)
        self.undo_action.triggered.connect(self.undo)
        self.redo_action.triggered.connect(self.redo)
        
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.redo_action.setShortcut(QKeySequence.Redo)
        
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)
        toolbar.addSeparator()
        self.update_undo_redo_status()
        
        reset_view_action = QAction(self.get_icon("refresh-cw"), "Reset View", self)
        toggle_meas_action = QAction(self.get_icon("eye"), "Toggle Measurements", self)
        reset_view_action.triggered.connect(self.canvas.reset_view)
        toggle_meas_action.triggered.connect(self.canvas.toggle_measurements)
        toolbar.addAction(reset_view_action)
        toolbar.addAction(toggle_meas_action)
    
    def create_right_panel(self) -> QWidget:
        # (Dieser Code bleibt unverändert)
        panel = QWidget()
        panel.setMaximumWidth(450)
        layout = QVBoxLayout(panel)
        
        measurements_group = QGroupBox("Measurements")
        measurements_layout = QVBoxLayout(measurements_group)
        
        self.measurements_list = QListWidget()
        self.measurements_list.itemClicked.connect(self.on_measurement_selected)
        measurements_layout.addWidget(self.measurements_list)
        
        meas_buttons_layout = QHBoxLayout()
        delete_btn = QPushButton("Delete Last")
        delete_btn.clicked.connect(self.delete_last_measurement)
        meas_buttons_layout.addWidget(delete_btn)
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_measurements)
        meas_buttons_layout.addWidget(clear_btn)
        measurements_layout.addLayout(meas_buttons_layout)
        layout.addWidget(measurements_group)
        
        ref_group = QGroupBox("Reference Objects")
        ref_layout = QVBoxLayout(ref_group)
        ref_scroll = QScrollArea()
        ref_scroll.setWidgetResizable(True)
        ref_scroll.setMaximumHeight(200)
        ref_content = QWidget()
        ref_content_layout = QVBoxLayout(ref_content)
        for name, data in REFERENCE_OBJECTS.items():
            if name != "Custom":
                text = f"• {name}: "
                if "diameter" in data:
                    text += f"⌀{data['diameter']}{data['unit']}"
                else:
                    text += f"{data.get('length', 'N/A')}×{data.get('width', 'N/A')}{data['unit']}"
                ref_content_layout.addWidget(QLabel(text))
        ref_scroll.setWidget(ref_content)
        ref_layout.addWidget(ref_scroll)
        layout.addWidget(ref_group)
        
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        export_json_btn = QPushButton("Export as JSON")
        export_json_btn.clicked.connect(self.export_json)
        export_layout.addWidget(export_json_btn)
        export_csv_btn = QPushButton("Export as CSV")
        export_csv_btn.clicked.connect(self.export_csv)
        export_layout.addWidget(export_csv_btn)
        layout.addWidget(export_group)
        
        info_group = QGroupBox("Info")
        info_layout = QFormLayout(info_group)
        self.zoom_label = QLabel("1.00x")
        self.image_size_label = QLabel("No image")
        self.mouse_pos_label = QLabel("—")
        info_layout.addRow("Zoom:", self.zoom_label)
        info_layout.addRow("Image Size:", self.image_size_label)
        info_layout.addRow("Mouse:", self.mouse_pos_label)
        layout.addWidget(info_group)
        
        layout.addStretch()
        return panel
    
    # Der Event-Filter wird nicht mehr benötigt
    
    def set_tool(self, tool: str):
        self.canvas.set_mode(tool)
        for action in self.tool_actions: action.setChecked(False)
        if tool == "measure": self.tool_actions[0].setChecked(True)
        elif tool == "pan": self.tool_actions[1].setChecked(True)
    
    def load_image(self):
        if not self.prompt_save_if_dirty(): return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)")
        if file_path:
            if self.canvas.load_image(file_path):
                self.current_image_path = file_path
                self.status_bar.showMessage(f"Loaded: {os.path.basename(file_path)}")
                size = self.canvas.get_image_size()
                if size: self.image_size_label.setText(f"{size[0]}×{size[1]} px")
                
                self.load_measurements()
                self.update_measurements_list()
                self.is_dirty = False
                self.undo_stack.clear()
                self.redo_stack.clear()
                self.update_undo_redo_status()
            else:
                QMessageBox.critical(self, "Error", "Failed to load image.")
    
    def save_annotated_image(self):
        if self.canvas.cv_image is None:
            QMessageBox.warning(self, "Warning", "No image to save.")
            return
        
        default_name = f"{os.path.splitext(os.path.basename(self.current_image_path))[0]}_annotated.png"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Annotated Image", default_name, "PNG (*.png);;JPEG (*.jpg)")
        
        if file_path:
            if self.canvas.grab().save(file_path):
                self.status_bar.showMessage(f"Saved annotated image to: {os.path.basename(file_path)}")
            else:
                QMessageBox.critical(self, "Error", "Failed to save image.")
    
    def add_measurement_with_history(self, measurement: Dict):
        """Adds a measurement and records the action for undo."""
        self.canvas.measurements.append(measurement)
        self.undo_stack.append(('add', measurement))
        self.redo_stack.clear()
        
        self.is_dirty = True
        self.update_all_views()
        self.status_bar.showMessage(f"Measurement #{measurement['id']} added.")

    def delete_last_measurement(self):
        deleted_measurement = self.canvas.delete_last_measurement()
        if deleted_measurement:
            self.undo_stack.append(('delete', deleted_measurement))
            self.redo_stack.clear()
            self.is_dirty = True
            self.update_all_views()
            self.status_bar.showMessage("Last measurement deleted.")
        else:
            QMessageBox.information(self, "Info", "No measurements to delete.")

    def clear_measurements(self):
        if not self.canvas.measurements:
            QMessageBox.information(self, "Info", "No measurements to clear.")
            return
        
        reply = QMessageBox.question(self, "Clear All", "Are you sure you want to delete all measurements?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            old_measurements = self.canvas.clear_measurements()
            if old_measurements:
                self.undo_stack.append(('clear', old_measurements))
                self.redo_stack.clear()
                self.is_dirty = True
                self.update_all_views()
                self.status_bar.showMessage("All measurements cleared.")

    def undo(self):
        # (Dieser Code bleibt unverändert)
        if not self.undo_stack: return
        
        action, data = self.undo_stack.pop()
        
        if action == 'add':
            self.canvas.measurements.remove(data)
            if self.canvas.points: self.canvas.points.pop(); self.canvas.points.pop()
            self.redo_stack.append(('add', data))
        elif action == 'delete':
            self.canvas.measurements.append(data)
            self.canvas.points.append( (data['start']['x'], data['start']['y']) )
            self.canvas.points.append( (data['end']['x'], data['end']['y']) )
            self.redo_stack.append(('delete', data))
        elif action == 'clear':
            self.canvas.measurements.extend(data)
            # Wiederherstellen der Punkte ist hier vereinfacht
            for m in data:
                self.canvas.points.append((m['start']['x'], m['start']['y']))
                self.canvas.points.append((m['end']['x'], m['end']['y']))
            self.redo_stack.append(('clear', data))

        self.is_dirty = True
        self.update_all_views()
        
    def redo(self):
        # (Dieser Code bleibt unverändert)
        if not self.redo_stack: return
        
        action, data = self.redo_stack.pop()

        if action == 'add':
            self.canvas.measurements.append(data)
            self.canvas.points.append( (data['start']['x'], data['start']['y']) )
            self.canvas.points.append( (data['end']['x'], data['end']['y']) )
            self.undo_stack.append(('add', data))
        elif action == 'delete':
            try:
                self.canvas.measurements.remove(data)
                # Das Entfernen der Punkte ist tricky, wenn die Reihenfolge nicht garantiert ist
                # Diese simple Implementierung geht davon aus, dass es die letzten waren.
                if self.canvas.points: self.canvas.points.pop(); self.canvas.points.pop()
                self.undo_stack.append(('delete', data))
            except ValueError:
                print("Warning: Could not redo 'delete' action. Measurement not found.")

        elif action == 'clear':
            old_measurements = self.canvas.clear_measurements()
            self.undo_stack.append(('clear', old_measurements))

        self.is_dirty = True
        self.update_all_views()

    def update_all_views(self):
        """Helper to refresh UI after undo/redo."""
        self.update_measurements_list()
        self.canvas.update_display()
        self.update_undo_redo_status()

    def update_undo_redo_status(self):
        """Enables/disables undo/redo actions based on stack state."""
        self.undo_action.setEnabled(bool(self.undo_stack))
        self.redo_action.setEnabled(bool(self.redo_stack))
    
    def update_measurements_list(self):
        # (Dieser Code bleibt unverändert)
        self.measurements_list.clear()
        colors = [
            QColor(0, 255, 0), QColor(255, 0, 0), QColor(0, 0, 255),
            QColor(255, 255, 0), QColor(255, 0, 255), QColor(0, 255, 255)
        ]
        sorted_measurements = sorted(self.canvas.measurements, key=lambda m: m['id'])
        for m in sorted_measurements:
            item_text = f"#{m['id']}: {m['pixel_length']:.1f} px"
            if m.get("real_world_length"):
                unit = m["reference_object"].get("unit", "mm")
                item_text += f" → {m['real_world_length']:.2f} {unit}"
            item = QListWidgetItem(item_text)
            color = colors[(m['id'] - 1) % len(colors)]
            item.setForeground(color)
            self.measurements_list.addItem(item)
    
    def on_measurement_selected(self, item: QListWidgetItem):
        pass
    
    def on_mouse_moved(self, screen_x: int, screen_y: int, img_x: int, img_y: int):
        self.mouse_pos_label.setText(f"({img_x}, {img_y})")
        self.zoom_label.setText(f"{self.canvas.zoom_factor:.2f}x")
    
    def get_measurements_save_path(self) -> str:
        if self.current_image_path:
            dir_name = os.path.dirname(self.current_image_path)
            base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
            return os.path.join(dir_name, f"{base_name}_measurements.json")
        return ""
    
    def save_measurements(self) -> bool:
        filename = self.get_measurements_save_path()
        if not filename:
            QMessageBox.warning(self, "Cannot Save", "Load an image first to create a save path for measurements.")
            return False
        
        data = { "measurements": self.canvas.measurements }
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.is_dirty = False
            self.status_bar.showMessage(f"Measurements saved to {os.path.basename(filename)}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save measurements: {e}")
            return False

    def load_measurements(self):
        filename = self.get_measurements_save_path()
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self.canvas.clear_measurements()
                measurements = data.get("measurements", [])
                for m in measurements:
                    self.canvas.points.append((m['start']['x'], m['start']['y']))
                    self.canvas.points.append((m['end']['x'], m['end']['y']))
                    self.canvas.measurements.append(m)
                
                self.canvas.update_display()
                self.status_bar.showMessage(f"Loaded {len(measurements)} measurements from file.")
                self.is_dirty = False
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Failed to load measurements: {e}")
    
    def export_json(self):
        if not self.canvas.measurements:
            QMessageBox.information(self, "Info", "No measurements to export.")
            return
        
        default_name = self.get_measurements_save_path()
        file_path, _ = QFileDialog.getSaveFileName(self, "Export as JSON", default_name, "JSON (*.json)")
        
        if file_path:
            data = { "exported": datetime.now().isoformat(), "measurements": self.canvas.measurements }
            try:
                with open(file_path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
                self.status_bar.showMessage(f"Exported to: {os.path.basename(file_path)}")
            except Exception as e: QMessageBox.critical(self, "Error", f"Failed to export: {e}")
    
    def export_csv(self):
        if not self.canvas.measurements:
            QMessageBox.information(self, "Info", "No measurements to export.")
            return
        
        default_name = self.get_measurements_save_path().replace(".json", ".csv")
        file_path, _ = QFileDialog.getSaveFileName(self, "Export as CSV", default_name, "CSV (*.csv)")
        
        if file_path:
            try:
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['ID', 'Pixel_Length', 'Real_Length', 'Unit', 'Reference_Object', 'Scale_Factor', 'Start_X', 'Start_Y', 'End_X', 'End_Y', 'Timestamp']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for m in self.canvas.measurements:
                        ref_obj = m.get('reference_object') or {}
                        row = {
                            'ID': m['id'], 'Pixel_Length': f"{m['pixel_length']:.2f}",
                            'Real_Length': f"{m.get('real_world_length', ''):.2f}" if m.get('real_world_length') else '',
                            'Unit': ref_obj.get('unit', ''), 'Reference_Object': ref_obj.get('name', 'None'),
                            'Scale_Factor': f"{m.get('scale_factor', ''):.6f}" if m.get('scale_factor') else '',
                            'Start_X': f"{m['start']['x']:.2f}", 'Start_Y': f"{m['start']['y']:.2f}",
                            'End_X': f"{m['end']['x']:.2f}", 'End_Y': f"{m['end']['y']:.2f}",
                            'Timestamp': m['timestamp']
                        }
                        writer.writerow(row)
                self.status_bar.showMessage(f"Exported to: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def prompt_save_if_dirty(self) -> bool:
        if not self.is_dirty: return True
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Unsaved Changes")
        msg_box.setText("You have unsaved measurements. Do you want to save them before proceeding?")
        msg_box.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        msg_box.setDefaultButton(QMessageBox.Save)
        reply = msg_box.exec()
        if reply == QMessageBox.Save: return self.save_measurements()
        elif reply == QMessageBox.Cancel: return False
        return True

    def closeEvent(self, event: QCloseEvent):
        if self.prompt_save_if_dirty(): event.accept()
        else: event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Dark theme palette (bleibt unverändert)
    from PySide6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    window = PixelRulerMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
