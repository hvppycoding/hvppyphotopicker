# gui.py (PhotoPicker 리네이밍 및 cross-platform 단축키 적용)
import sys
import os
import shutil
import glob
import platform
from PyQt5 import QtWidgets, QtGui, QtCore
from PIL import Image
from .grouper import PhotoGrouper
import cv2

class PhotoPickerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("hvppyphotopicker")
        self.setGeometry(100, 100, 1000, 700)

        self.input_folder = ""
        self.export_folder = ""
        self.groups = []
        self.current_group_index = 0
        self.selected_images = set()

        self.preview_label = None
        self.preview_pixmap = None
        self.preview_scale = 1.0
        self.preview_drag_pos = None
        self.preview_scroll_area = None

        self.selected_image_index = 0
        self.thumb_widgets = []

        self.progress = None

        self.init_ui()

    def pick_least_blurry(self, image_paths):
        def blur_score(path):
            try:
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                return cv2.Laplacian(img, cv2.CV_64F).var()
            except:
                return 0.0
        return max(image_paths, key=blur_score)

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        top_bar = QtWidgets.QHBoxLayout()
        self.btn_input = QtWidgets.QPushButton("Select Input Folder")
        self.btn_output = QtWidgets.QPushButton("Select Export Folder")
        self.btn_merge = QtWidgets.QPushButton("Merge Groups")
        self.btn_split = QtWidgets.QPushButton("Split Group")
        self.btn_export = QtWidgets.QPushButton("Export Selected")
        top_bar.addWidget(self.btn_input)
        top_bar.addWidget(self.btn_output)
        top_bar.addWidget(self.btn_merge)
        top_bar.addWidget(self.btn_split)
        top_bar.addWidget(self.btn_export)

        self.splitter = QtWidgets.QSplitter()
        layout.addWidget(self.splitter)

        self.group_list = QtWidgets.QListWidget()
        self.group_list.currentRowChanged.connect(self.on_group_selected)
        self.splitter.addWidget(self.group_list)

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)

        right_layout.addLayout(top_bar)

        # Move thumbnail scroll area and related widgets before thumb_splitter
        self.thumb_scroll_area = QtWidgets.QScrollArea()
        self.thumb_scroll_area.setWidgetResizable(True)
        self.thumb_container = QtWidgets.QWidget()
        self.thumb_layout = QtWidgets.QHBoxLayout(self.thumb_container)
        self.thumb_layout.setSpacing(10)
        self.thumb_scroll_area.setWidget(self.thumb_container)

        self.preview_label = QtWidgets.QLabel()
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.preview_label.setBackgroundRole(QtGui.QPalette.Base)
        self.preview_label.setScaledContents(False)
        self.preview_scroll_area = QtWidgets.QScrollArea()
        self.preview_scroll_area.setWidget(self.preview_label)
        self.preview_scroll_area.setWidgetResizable(True)
        # right_layout.addWidget(self.preview_scroll_area)

        self.thumb_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.thumb_splitter.addWidget(self.preview_scroll_area)
        self.thumb_splitter.addWidget(self.thumb_scroll_area)
        self.thumb_splitter.setSizes([500, 150])
        right_layout.addWidget(self.thumb_splitter)

        self.preview_label.installEventFilter(self)

        # right_layout.addWidget(self.thumb_scroll_area)
        # self.thumb_scroll_area.setMinimumHeight(140)
        # self.thumb_scroll_area.setMaximumHeight(300)
        # self.thumb_scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([150, 850])

        self.btn_input.clicked.connect(self.select_input_folder)
        self.btn_output.clicked.connect(self.select_export_folder)
        self.btn_export.clicked.connect(self.export_selected)
        self.btn_merge.clicked.connect(self.merge_groups)
        self.btn_split.clicked.connect(self.split_group)

        if platform.system() == "Darwin":
            mod = "Meta"
        else:
            mod = "Ctrl"

        QtWidgets.QShortcut(QtGui.QKeySequence(f"{mod}+F"), self, self.next_group)
        QtWidgets.QShortcut(QtGui.QKeySequence(f"{mod}+B"), self, self.prev_group)
        QtWidgets.QShortcut(QtGui.QKeySequence(f"{mod}+M"), self, self.merge_groups)
        QtWidgets.QShortcut(QtGui.QKeySequence(f"{mod}+P"), self, self.split_group)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

    def select_input_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.input_folder = folder
            self.progress_dialog = None

            exts = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")
            image_paths = []
            for ext in exts:
                image_paths.extend(glob.glob(os.path.join(folder, "**", ext), recursive=True))

            self.show_progress_dialog(len(image_paths))
            self.progress_dialog.setLabelText(f"Analyzing {len(image_paths)} images...")

            grouper = PhotoGrouper(image_paths, threshold_seconds=3.0)
            self.groups = grouper.groups
            self.current_group_index = 0
            self.selected_images.clear()
            processed = 0
            total = len(image_paths)
            for i, group in enumerate(self.groups):
                if self.was_cancelled():
                    self.progress_dialog.cancel()
                    return
                if group:
                    filename = os.path.basename(group[0])
                    self.progress_dialog.setLabelText(f"Analyzing {filename} ({processed + 1}/{total})")
                    best = self.pick_least_blurry(group)
                    self.selected_images.add(best)
                processed += len(group)
                self.progress_dialog.setValue(processed)
                QtWidgets.QApplication.processEvents()

            self.group_list.clear()
            for i in range(len(self.groups)):
                self.group_list.addItem(f"Group {i + 1}")

            self.load_group()
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None

    def select_export_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if folder:
            self.export_folder = folder

    def load_group(self):
        for i in reversed(range(self.thumb_layout.count())):
            widget = self.thumb_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.thumb_widgets = []

        if not self.groups:
            return

        group = self.groups[self.current_group_index]
        self.selected_image_index = 0

        for i, path in enumerate(group):
            container = QtWidgets.QWidget()
            container.setFixedWidth(120)
            container.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
            layout = QtWidgets.QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)

            label = QtWidgets.QLabel()
            pixmap = QtGui.QPixmap(path).scaledToHeight(100, QtCore.Qt.SmoothTransformation)
            label.setPixmap(pixmap)
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.mousePressEvent = lambda e, p=path, idx=i: self.select_image(idx, p)

            name_label = QtWidgets.QLabel(os.path.basename(path))
            name_label.setAlignment(QtCore.Qt.AlignCenter)
            name_label.setStyleSheet("font-size: 10px; color: gray;")

            # Updated checkbox block
            checkbox = QtWidgets.QCheckBox()
            checkbox.setChecked(path in self.selected_images)
            checkbox.stateChanged.connect(lambda state, p=path: self.toggle_selection(p, state))
            checkbox.setStyleSheet("margin: 2px;")

            layout.addWidget(label)
            layout.addWidget(name_label)
            # Overlay checkbox in top-left
            checkbox_overlay = QtWidgets.QWidget(container)
            checkbox_overlay.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
            checkbox_overlay.setGeometry(0, 0, 20, 20)
            checkbox_layout = QtWidgets.QVBoxLayout(checkbox_overlay)
            checkbox_layout.setContentsMargins(2, 2, 0, 0)
            checkbox_layout.addWidget(checkbox)
            checkbox_overlay.raise_()
            layout.addStretch()
            self.thumb_layout.addWidget(container)
            self.thumb_widgets.append(container)

        self.setWindowTitle(f"hvppyphotopicker - Group {self.current_group_index + 1}/{len(self.groups)}")
        self.group_list.setCurrentRow(self.current_group_index)
        self.show_preview(group[self.selected_image_index])
        self.highlight_selected_thumbnail()

    def select_image(self, idx, path):
        self.selected_image_index = idx
        self.highlight_selected_thumbnail()
        self.show_preview(path)

    def highlight_selected_thumbnail(self):
        for i, widget in enumerate(self.thumb_widgets):
            inner = widget.layout().itemAt(0).widget()
            if i == self.selected_image_index:
                inner.setStyleSheet("border: 2px solid rgba(30, 144, 255, 180); background-color: rgba(30, 144, 255, 40);")
            else:
                inner.setStyleSheet("")

    def keyPressEvent(self, event):
        # Override scroll behavior for up/down keys
        if event.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
            self.group_list.clearFocus()
            return
        if not self.groups:
            return
        group = self.groups[self.current_group_index]
        if event.key() == QtCore.Qt.Key_Right:
            self.selected_image_index = min(self.selected_image_index + 1, len(group) - 1)
            widget = self.thumb_widgets[self.selected_image_index]
            self.thumb_scroll_area.ensureWidgetVisible(widget)
            self.highlight_selected_thumbnail()
            self.show_preview(group[self.selected_image_index])
        elif event.key() == QtCore.Qt.Key_Left:
            self.selected_image_index = max(self.selected_image_index - 1, 0)
            widget = self.thumb_widgets[self.selected_image_index]
            self.thumb_scroll_area.ensureWidgetVisible(widget)
            self.highlight_selected_thumbnail()
            self.show_preview(group[self.selected_image_index])
        elif event.key() == QtCore.Qt.Key_Space:
            path = group[self.selected_image_index]
            if path in self.selected_images:
                self.selected_images.remove(path)
            else:
                self.selected_images.add(path)

            # Update the checkbox only
            container = self.thumb_widgets[self.selected_image_index]
            checkbox = container.findChild(QtWidgets.QCheckBox)
            if checkbox:
                checkbox.setChecked(path in self.selected_images)

    def toggle_selection(self, path, state):
        if state == QtCore.Qt.Checked:
            self.selected_images.add(path)
        else:
            self.selected_images.discard(path)

    def next_group(self):
        if self.groups and self.current_group_index < len(self.groups) - 1:
            self.current_group_index += 1
            self.load_group()

    def prev_group(self):
        if self.current_group_index > 0:
            self.current_group_index -= 1
            self.load_group()

    def merge_groups(self):
        if self.current_group_index > 0:
            prev_group = self.groups[self.current_group_index - 1]
            current_group = self.groups[self.current_group_index]
            merged = prev_group + current_group
            self.groups[self.current_group_index - 1] = merged
            del self.groups[self.current_group_index]
            self.current_group_index -= 1
            self.load_group()

    def split_group(self):
        if not self.groups:
            return
        group = self.groups[self.current_group_index]
        to_move = [path for path in group if path in self.selected_images]
        if not to_move or len(to_move) == len(group):
            return
        remain = [p for p in group if p not in to_move]
        self.groups[self.current_group_index] = remain
        self.groups.insert(self.current_group_index + 1, to_move)
        self.load_group()

    def export_selected(self):
        if not self.export_folder:
            QtWidgets.QMessageBox.warning(self, "Export Folder", "Please select export folder first")
            return

        for path in self.selected_images:
            fname = os.path.basename(path)
            target = os.path.join(self.export_folder, fname)
            shutil.copy2(path, target)

        QtWidgets.QMessageBox.information(self, "Done", f"Exported {len(self.selected_images)} files")

    def on_group_selected(self, index):
        if 0 <= index < len(self.groups):
            self.current_group_index = index
            self.load_group()

    def show_preview(self, path):
        self.preview_pixmap = QtGui.QPixmap(path)
        if self.preview_scroll_area and self.preview_scroll_area.viewport():
            area_size = self.preview_scroll_area.viewport().size()
            self.preview_scale = min(
                area_size.width() / self.preview_pixmap.width(),
                area_size.height() / self.preview_pixmap.height()
            )
        else:
            self.preview_scale = 1.0
        self.update_preview()

    def update_preview(self):
        if self.preview_pixmap:
            scaled = self.preview_pixmap.scaled(self.preview_scale * self.preview_pixmap.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)

    def eventFilter(self, source, event):
        if source is self.preview_label and event.type() == QtCore.QEvent.Wheel:
            angle = event.angleDelta().y()
            if angle > 0:
                self.preview_scale *= 1.1
            else:
                self.preview_scale /= 1.1
            self.update_preview()
            return True
        elif event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                self.preview_drag_pos = event.pos()
                return True
        elif event.type() == QtCore.QEvent.MouseMove and event.buttons() & QtCore.Qt.LeftButton:
            if self.preview_drag_pos:
                delta = event.pos() - self.preview_drag_pos
                h_bar = self.preview_scroll_area.horizontalScrollBar()
                v_bar = self.preview_scroll_area.verticalScrollBar()
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
                self.preview_drag_pos = event.pos()
                return True
        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            self.preview_drag_pos = None
            return True
        return super().eventFilter(source, event)
    def show_progress_dialog(self, maximum):
        self.progress_dialog = QtWidgets.QProgressDialog("Loading images...", "Cancel", 0, maximum, self)
        self.progress_dialog.setWindowTitle("Loading")
        self.progress_dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.show()

    def was_cancelled(self):
        return self.progress_dialog.wasCanceled() if self.progress_dialog else False