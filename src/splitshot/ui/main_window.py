from __future__ import annotations

from PySide6.QtCore import QUrl, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QColorDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from splitshot.domain.models import (
    AspectRatio,
    BadgeSize,
    ExportQuality,
    MergeLayout,
    OverlayPosition,
    PipSize,
    ScoreLetter,
)
from splitshot.export.pipeline import export_project
from splitshot.merge.layouts import calculate_merge_canvas
from splitshot.timeline.model import compute_split_rows, draw_time_ms, total_time_ms
from splitshot.ui.controller import ProjectController
from splitshot.ui.widgets.overlay_preview import OverlayPreview
from splitshot.ui.widgets.waveform_editor import WaveformEditor, WaveformState
from splitshot.utils.time import format_time_ms


class PreviewContainer(QWidget):
    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.primary_video = QVideoWidget(self)
        self.secondary_video = QVideoWidget(self)
        self.overlay = OverlayPreview(self)
        self.overlay.score_position_selected.connect(self._handle_score_position)
        self.overlay.raise_()

    def resizeEvent(self, event) -> None:  # noqa: N802
        project = self.controller.project
        self.overlay.setGeometry(self.rect())
        if not project.merge.enabled or project.secondary_video is None:
            self.primary_video.setGeometry(self.rect())
            self.secondary_video.hide()
            return

        canvas = calculate_merge_canvas(
            project.primary_video,
            project.secondary_video,
            project.merge.layout,
            project.merge.pip_size,
        )
        scale_x = self.width() / max(1, canvas.width)
        scale_y = self.height() / max(1, canvas.height)
        scale = min(scale_x, scale_y)
        offset_x = int((self.width() - (canvas.width * scale)) / 2)
        offset_y = int((self.height() - (canvas.height * scale)) / 2)

        p = canvas.primary_rect
        self.primary_video.setGeometry(
            int(offset_x + (p.x * scale)),
            int(offset_y + (p.y * scale)),
            int(p.width * scale),
            int(p.height * scale),
        )

        if canvas.secondary_rect is not None:
            s = canvas.secondary_rect
            self.secondary_video.setGeometry(
                int(offset_x + (s.x * scale)),
                int(offset_y + (s.y * scale)),
                int(s.width * scale),
                int(s.height * scale),
            )
            self.secondary_video.show()

    def _handle_score_position(self, x_norm: float, y_norm: float) -> None:
        selected = self.controller.project.ui_state.selected_shot_id
        if selected is None:
            return
        self.controller.set_score_position(selected, x_norm, y_norm)


class MainWindow(QMainWindow):
    def __init__(self, controller: ProjectController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("SplitShot")
        self.resize(1500, 980)

        self.primary_audio = QAudioOutput(self)
        self.primary_audio.setVolume(0.9)
        self.primary_player = QMediaPlayer(self)
        self.primary_player.setAudioOutput(self.primary_audio)

        self.secondary_player = QMediaPlayer(self)
        self.secondary_player.setAudioOutput(None)

        self.preview = PreviewContainer(controller)
        self._current_primary_path = ""
        self._current_secondary_path = ""
        self.preview.primary_video.setAspectRatioMode(Qt.KeepAspectRatio)
        self.preview.secondary_video.setAspectRatioMode(Qt.KeepAspectRatio)
        self.primary_player.setVideoOutput(self.preview.primary_video)
        self.secondary_player.setVideoOutput(self.preview.secondary_video)
        self.preview.overlay.crop_center_selected.connect(self._set_crop_center_from_preview)

        self.waveform = WaveformEditor()
        self.waveform.shot_added.connect(self.controller.add_shot)
        self.waveform.shot_moved.connect(self.controller.move_shot)
        self.waveform.shot_deleted.connect(self.controller.delete_shot)
        self.waveform.beep_moved.connect(self.controller.set_beep_time)
        self.waveform.seek_requested.connect(self.primary_player.setPosition)
        self.waveform.shot_selected.connect(self.controller.select_shot)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.sliderMoved.connect(self._set_position)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._toggle_playback)

        self.stats_label = QLabel()
        self.split_table = QTableWidget(0, 6)
        self.split_table.setHorizontalHeaderLabels(["Shot", "Absolute", "Split", "Score", "Source", "Confidence"])
        self.split_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.split_table.itemSelectionChanged.connect(self._selection_from_table)

        self.overlay_position = QComboBox()
        for option in OverlayPosition:
            self.overlay_position.addItem(option.value, option)
        self.overlay_position.currentIndexChanged.connect(self._on_overlay_position_changed)

        self.badge_size = QComboBox()
        for option in BadgeSize:
            self.badge_size.addItem(option.value, option)
        self.badge_size.currentIndexChanged.connect(self._on_badge_size_changed)

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(10)
        self.threshold_slider.setMaximum(90)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)

        self.merge_enabled = QCheckBox("Enable merge")
        self.merge_enabled.toggled.connect(self.controller.set_merge_enabled)

        self.merge_layout = QComboBox()
        for option in MergeLayout:
            self.merge_layout.addItem(option.value, option)
        self.merge_layout.currentIndexChanged.connect(self._on_merge_layout_changed)

        self.pip_size = QComboBox()
        for option in PipSize:
            self.pip_size.addItem(option.value, option)
        self.pip_size.currentIndexChanged.connect(self._on_pip_size_changed)

        self.penalties_input = QSpinBox()
        self.penalties_input.setRange(0, 999)
        self.penalties_input.valueChanged.connect(self.controller.set_penalties)

        self.scoring_enabled = QCheckBox("Enable scoring")
        self.scoring_enabled.toggled.connect(self._toggle_scoring)

        self.score_letter = QComboBox()
        for option in ScoreLetter:
            self.score_letter.addItem(option.value, option)
        self.score_letter.currentIndexChanged.connect(self._on_score_changed)

        self.score_color_button = QPushButton("Score color")
        self.score_color_button.clicked.connect(self._choose_score_color)

        self.place_score = QCheckBox("Place score on preview")
        self.place_score.toggled.connect(self.preview.overlay.set_placement_mode)

        self.export_quality = QComboBox()
        for option in ExportQuality:
            self.export_quality.addItem(option.value, option)
        self.export_quality.currentIndexChanged.connect(self._on_export_quality_changed)

        self.aspect_ratio = QComboBox()
        for option in AspectRatio:
            self.aspect_ratio.addItem(option.value, option)
        self.aspect_ratio.currentIndexChanged.connect(self._on_aspect_ratio_changed)

        self.crop_x = QSlider(Qt.Horizontal)
        self.crop_x.setRange(0, 100)
        self.crop_x.valueChanged.connect(self._on_crop_changed)

        self.crop_y = QSlider(Qt.Horizontal)
        self.crop_y.setRange(0, 100)
        self.crop_y.valueChanged.connect(self._on_crop_changed)

        self.drag_crop = QCheckBox("Drag crop on preview")
        self.drag_crop.toggled.connect(self.preview.overlay.set_crop_mode)

        self.style_target = QComboBox()
        self.style_target.addItems(["Timer", "Shot", "Current Shot", "Hit Factor"])
        self.style_target.currentIndexChanged.connect(self._sync_badge_style_controls)

        self.background_button = QPushButton("Background color")
        self.background_button.clicked.connect(lambda: self._choose_badge_color("background_color"))
        self.text_button = QPushButton("Text color")
        self.text_button.clicked.connect(lambda: self._choose_badge_color("text_color"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.valueChanged.connect(self._on_badge_opacity_changed)

        self.restore_defaults_button = QPushButton("Restore defaults")
        self.restore_defaults_button.clicked.connect(self.controller.restore_defaults)

        controls = self._build_controls()
        central = QWidget()
        self.setCentralWidget(central)

        content_splitter = QSplitter(Qt.Vertical)
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.addWidget(self.preview, stretch=1)
        preview_controls = QHBoxLayout()
        preview_controls.addWidget(self.play_button)
        preview_controls.addWidget(self.position_slider, stretch=1)
        preview_controls.addWidget(self.stats_label)
        preview_layout.addLayout(preview_controls)

        content_splitter.addWidget(preview_panel)
        content_splitter.addWidget(self.waveform)
        content_splitter.addWidget(self.split_table)
        content_splitter.setStretchFactor(0, 6)
        content_splitter.setStretchFactor(1, 2)
        content_splitter.setStretchFactor(2, 2)

        root_splitter = QSplitter(Qt.Horizontal)
        root_splitter.addWidget(content_splitter)
        root_splitter.addWidget(controls)
        root_splitter.setStretchFactor(0, 7)
        root_splitter.setStretchFactor(1, 3)

        layout = QVBoxLayout(central)
        layout.addWidget(root_splitter)

        self._build_menu()
        self._connect_signals()
        self.refresh_ui()

    def _build_controls(self) -> QWidget:
        tabs = QTabWidget()

        project_tab = QWidget()
        project_layout = QVBoxLayout(project_tab)
        load_primary = QPushButton("Load primary video")
        load_primary.clicked.connect(self._load_primary_video)
        analyze_primary = QPushButton("Analyze primary")
        analyze_primary.clicked.connect(self.controller.analyze_primary)
        load_secondary = QPushButton("Load secondary video")
        load_secondary.clicked.connect(self._load_secondary_video)
        analyze_secondary = QPushButton("Analyze secondary")
        analyze_secondary.clicked.connect(self.controller.analyze_secondary)
        save_project = QPushButton("Save project")
        save_project.clicked.connect(self._save_project)
        save_as_project = QPushButton("Save project as")
        save_as_project.clicked.connect(self._save_project_as)
        open_project = QPushButton("Open project")
        open_project.clicked.connect(self._open_project)
        delete_project = QPushButton("Delete project")
        delete_project.clicked.connect(self._delete_project)
        swap_videos = QPushButton("Swap videos")
        swap_videos.clicked.connect(self.controller.swap_videos)
        for widget in [
            load_primary,
            analyze_primary,
            load_secondary,
            analyze_secondary,
            save_project,
            save_as_project,
            open_project,
            delete_project,
            swap_videos,
        ]:
            project_layout.addWidget(widget)
        project_layout.addStretch(1)

        analysis_tab = QWidget()
        analysis_layout = QFormLayout(analysis_tab)
        analysis_layout.addRow("Threshold", self.threshold_slider)
        analysis_layout.addRow("Badge size", self.badge_size)
        analysis_layout.addRow(self.restore_defaults_button)

        merge_tab = QWidget()
        merge_layout = QFormLayout(merge_tab)
        merge_layout.addRow(self.merge_enabled)
        merge_layout.addRow("Layout", self.merge_layout)
        merge_layout.addRow("PiP size", self.pip_size)
        offset_controls = QWidget()
        offset_layout = QHBoxLayout(offset_controls)
        for label, delta in [("-10", -10), ("-1", -1), ("+1", 1), ("+10", 10)]:
            button = QPushButton(label)
            button.clicked.connect(lambda _, value=delta: self.controller.adjust_sync_offset(value))
            offset_layout.addWidget(button)
        merge_layout.addRow("Offset ms", offset_controls)

        scoring_tab = QWidget()
        scoring_layout = QFormLayout(scoring_tab)
        scoring_layout.addRow(self.scoring_enabled)
        scoring_layout.addRow("Score", self.score_letter)
        scoring_layout.addRow(self.score_color_button)
        scoring_layout.addRow("Penalty points", self.penalties_input)
        scoring_layout.addRow(self.place_score)

        overlay_tab = QWidget()
        overlay_layout = QFormLayout(overlay_tab)
        overlay_layout.addRow("Position", self.overlay_position)
        overlay_layout.addRow("Style target", self.style_target)
        overlay_layout.addRow(self.background_button)
        overlay_layout.addRow(self.text_button)
        overlay_layout.addRow("Opacity", self.opacity_slider)

        tabs.addTab(project_tab, "Project")
        tabs.addTab(analysis_tab, "Analysis")
        tabs.addTab(merge_tab, "Merge")
        tabs.addTab(overlay_tab, "Overlay")
        tabs.addTab(scoring_tab, "Scoring")
        export_tab = QWidget()
        export_layout = QFormLayout(export_tab)
        export_layout.addRow("Quality", self.export_quality)
        export_layout.addRow("Aspect ratio", self.aspect_ratio)
        export_layout.addRow("Crop X", self.crop_x)
        export_layout.addRow("Crop Y", self.crop_y)
        export_layout.addRow(self.drag_crop)
        export_button = QPushButton("Export MP4")
        export_button.clicked.connect(self._export_video)
        export_layout.addRow(export_button)
        tabs.addTab(export_tab, "Export")
        return tabs

    def _build_menu(self) -> None:
        menu = self.menuBar()
        project_menu = menu.addMenu("Project")
        for label, handler in [
            ("New", self._new_project),
            ("Open", self._open_project),
            ("Save", self._save_project),
            ("Save As", self._save_project_as),
        ]:
            action = QAction(label, self)
            action.triggered.connect(handler)
            project_menu.addAction(action)

        analyze_menu = menu.addMenu("Analyze")
        analyze_primary_action = QAction("Analyze Primary", self)
        analyze_primary_action.triggered.connect(self.controller.analyze_primary)
        analyze_menu.addAction(analyze_primary_action)
        analyze_secondary_action = QAction("Analyze Secondary", self)
        analyze_secondary_action.triggered.connect(self.controller.analyze_secondary)
        analyze_menu.addAction(analyze_secondary_action)

    def _connect_signals(self) -> None:
        self.controller.project_changed.connect(self.refresh_ui)
        self.primary_player.positionChanged.connect(self._on_position_changed)
        self.primary_player.durationChanged.connect(self._on_duration_changed)
        self.primary_player.playbackStateChanged.connect(self._on_playback_state_changed)

        self._secondary_sync_timer = QTimer(self)
        self._secondary_sync_timer.setInterval(80)
        self._secondary_sync_timer.timeout.connect(self._sync_secondary)
        self._secondary_sync_timer.start()

    def refresh_ui(self) -> None:
        project = self.controller.project
        self.setWindowTitle(f"SplitShot - {project.name}")

        self.threshold_slider.blockSignals(True)
        self.threshold_slider.setValue(int(project.analysis.detection_threshold * 100))
        self.threshold_slider.blockSignals(False)

        self.overlay_position.blockSignals(True)
        self.overlay_position.setCurrentIndex(self.overlay_position.findData(project.overlay.position))
        self.overlay_position.blockSignals(False)

        self.badge_size.blockSignals(True)
        self.badge_size.setCurrentIndex(self.badge_size.findData(project.overlay.badge_size))
        self.badge_size.blockSignals(False)

        self.merge_enabled.blockSignals(True)
        self.merge_enabled.setChecked(project.merge.enabled)
        self.merge_enabled.blockSignals(False)

        self.merge_layout.blockSignals(True)
        self.merge_layout.setCurrentIndex(self.merge_layout.findData(project.merge.layout))
        self.merge_layout.blockSignals(False)

        self.pip_size.blockSignals(True)
        self.pip_size.setCurrentIndex(self.pip_size.findData(project.merge.pip_size))
        self.pip_size.blockSignals(False)

        self.scoring_enabled.blockSignals(True)
        self.scoring_enabled.setChecked(project.scoring.enabled)
        self.scoring_enabled.blockSignals(False)

        self.export_quality.blockSignals(True)
        self.export_quality.setCurrentIndex(self.export_quality.findData(project.export.quality))
        self.export_quality.blockSignals(False)

        self.aspect_ratio.blockSignals(True)
        self.aspect_ratio.setCurrentIndex(self.aspect_ratio.findData(project.export.aspect_ratio))
        self.aspect_ratio.blockSignals(False)

        self.crop_x.blockSignals(True)
        self.crop_x.setValue(int(project.export.crop_center_x * 100))
        self.crop_x.blockSignals(False)

        self.crop_y.blockSignals(True)
        self.crop_y.setValue(int(project.export.crop_center_y * 100))
        self.crop_y.blockSignals(False)

        self._sync_badge_style_controls()

        self.penalties_input.blockSignals(True)
        self.penalties_input.setValue(project.scoring.penalties)
        self.penalties_input.blockSignals(False)

        selected_id = project.ui_state.selected_shot_id
        selected_shot = next((shot for shot in project.analysis.shots if shot.id == selected_id), None)
        if selected_shot is not None and selected_shot.score is not None:
            self.score_letter.blockSignals(True)
            self.score_letter.setCurrentIndex(self.score_letter.findData(selected_shot.score.letter))
            self.score_letter.blockSignals(False)

        self._update_media_sources()
        self._update_waveform()
        self._update_split_table()
        self._update_stats()
        self.preview.overlay.set_state(project, self.primary_player.position())
        self.preview.update()

    def _update_media_sources(self) -> None:
        project = self.controller.project
        if project.primary_video.path and project.primary_video.path != self._current_primary_path:
            self.primary_player.setSource(QUrl.fromLocalFile(project.primary_video.path))
            self._current_primary_path = project.primary_video.path
        if (
            project.secondary_video
            and project.secondary_video.path
            and project.secondary_video.path != self._current_secondary_path
        ):
            self.secondary_player.setSource(QUrl.fromLocalFile(project.secondary_video.path))
            self._current_secondary_path = project.secondary_video.path
        self.preview.update()

    def _update_waveform(self) -> None:
        project = self.controller.project
        self.waveform.set_state(
            WaveformState(
                duration_ms=max(1, project.primary_video.duration_ms or self.primary_player.duration() or 1),
                waveform=project.analysis.waveform_primary,
                secondary_waveform=project.analysis.waveform_secondary if project.merge.enabled else None,
                shots=project.analysis.shots,
                beep_time_ms=project.analysis.beep_time_ms_primary,
                secondary_beep_time_ms=project.analysis.beep_time_ms_secondary if project.merge.enabled else None,
                playhead_ms=self.primary_player.position(),
                zoom=project.ui_state.timeline_zoom,
                offset_ms=project.ui_state.timeline_offset_ms,
                selected_shot_id=project.ui_state.selected_shot_id,
                frame_nudge_ms=max(1, int(round(1000 / max(1.0, project.primary_video.fps or 30.0)))),
            )
        )

    def _update_split_table(self) -> None:
        rows = compute_split_rows(self.controller.project)
        self.split_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            items = [
                str(row.shot_number),
                format_time_ms(row.absolute_time_ms),
                "" if row.split_ms is None else format_time_ms(row.split_ms),
                row.score_letter or "",
                row.source,
                "" if row.confidence is None else f"{row.confidence:.2f}",
            ]
            for column, value in enumerate(items):
                self.split_table.setItem(row_index, column, QTableWidgetItem(value))

    def _update_stats(self) -> None:
        project = self.controller.project
        draw_text = format_time_ms(draw_time_ms(project))
        total_text = format_time_ms(total_time_ms(project))
        shot_count = len(project.analysis.shots)
        offset = project.analysis.sync_offset_ms
        self.stats_label.setText(f"Shots {shot_count} | Draw {draw_text} | Total {total_text} | Offset {offset} ms")

    def _toggle_playback(self) -> None:
        if self.primary_player.playbackState() == QMediaPlayer.PlayingState:
            self.primary_player.pause()
            self.secondary_player.pause()
        else:
            self.primary_player.play()
            if self.controller.project.merge.enabled and self.controller.project.secondary_video:
                self._sync_secondary(force=True)
                self.secondary_player.play()

    def _set_position(self, position: int) -> None:
        self.primary_player.setPosition(position)
        self.preview.overlay.set_state(self.controller.project, position)

    def _on_position_changed(self, position: int) -> None:
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(position)
        self.position_slider.blockSignals(False)
        self.preview.overlay.set_state(self.controller.project, position)
        self._update_waveform()

    def _on_duration_changed(self, duration: int) -> None:
        self.position_slider.setMaximum(max(0, duration))
        self._update_waveform()

    def _on_playback_state_changed(self, state) -> None:
        self.play_button.setText("Pause" if state == QMediaPlayer.PlayingState else "Play")

    def _sync_secondary(self, force: bool = False) -> None:
        project = self.controller.project
        if not project.merge.enabled or project.secondary_video is None:
            self.secondary_player.pause()
            return
        target_position = self.primary_player.position() + project.analysis.sync_offset_ms
        target_position = max(0, target_position)
        if force or abs(self.secondary_player.position() - target_position) > 60:
            self.secondary_player.setPosition(target_position)

    def _on_overlay_position_changed(self) -> None:
        position = self.overlay_position.currentData()
        if position is not None:
            self.controller.set_overlay_position(position)

    def _on_badge_size_changed(self) -> None:
        size = self.badge_size.currentData()
        if size is not None:
            self.controller.set_badge_size(size)

    def _on_threshold_changed(self, value: int) -> None:
        self.controller.set_detection_threshold(value / 100.0)

    def _on_merge_layout_changed(self) -> None:
        layout = self.merge_layout.currentData()
        if layout is not None:
            self.controller.set_merge_layout(layout)

    def _on_pip_size_changed(self) -> None:
        size = self.pip_size.currentData()
        if size is not None:
            self.controller.set_pip_size(size)

    def _toggle_scoring(self, enabled: bool) -> None:
        self.controller.set_scoring_enabled(enabled)

    def _on_score_changed(self) -> None:
        selected = self.controller.project.ui_state.selected_shot_id
        if selected is None:
            return
        letter = self.score_letter.currentData()
        if letter is not None:
            self.controller.assign_score(selected, letter)

    def _selection_from_table(self) -> None:
        row = self.split_table.currentRow()
        shots = self.controller.project.analysis.shots
        if 0 <= row < len(shots):
            self.controller.select_shot(shots[row].id)

    def _on_export_quality_changed(self) -> None:
        quality = self.export_quality.currentData()
        if quality is not None:
            self.controller.set_export_quality(quality)

    def _on_aspect_ratio_changed(self) -> None:
        aspect = self.aspect_ratio.currentData()
        if aspect is not None:
            self.controller.project.export.aspect_ratio = aspect
            self.controller.project.touch()
            self.controller.project_changed.emit()

    def _on_crop_changed(self) -> None:
        self.controller.project.export.crop_center_x = self.crop_x.value() / 100.0
        self.controller.project.export.crop_center_y = self.crop_y.value() / 100.0
        self.controller.project.touch()
        self.controller.project_changed.emit()

    def _sync_badge_style_controls(self) -> None:
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(int(self._selected_badge_style().opacity * 100))
        self.opacity_slider.blockSignals(False)

    def _selected_badge_style(self):
        label = self.style_target.currentText()
        if label == "Timer":
            return self.controller.project.overlay.timer_badge
        if label == "Shot":
            return self.controller.project.overlay.shot_badge
        if label == "Current Shot":
            return self.controller.project.overlay.current_shot_badge
        return self.controller.project.overlay.hit_factor_badge

    def _choose_badge_color(self, attribute: str) -> None:
        color = QColorDialog.getColor(parent=self)
        if not color.isValid():
            return
        setattr(self._selected_badge_style(), attribute, color.name())
        self.controller.project.touch()
        self.controller.project_changed.emit()

    def _choose_score_color(self) -> None:
        letter = self.score_letter.currentData()
        if letter is None:
            return
        color = QColorDialog.getColor(parent=self)
        if not color.isValid():
            return
        self.controller.project.overlay.scoring_colors[letter.value] = color.name()
        self.controller.project.touch()
        self.controller.project_changed.emit()

    def _on_badge_opacity_changed(self) -> None:
        self._selected_badge_style().opacity = self.opacity_slider.value() / 100.0
        self.controller.project.touch()
        self.controller.project_changed.emit()

    def _set_crop_center_from_preview(self, x_norm: float, y_norm: float) -> None:
        self.controller.project.export.crop_center_x = x_norm
        self.controller.project.export.crop_center_y = y_norm
        self.controller.project.touch()
        self.controller.project_changed.emit()

    def _load_primary_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Primary Video")
        if path:
            self.controller.load_primary_video(path)

    def _load_secondary_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Secondary Video")
        if path:
            self.controller.load_secondary_video(path)

    def _new_project(self) -> None:
        if not self._confirm_unsaved():
            return
        self.controller.new_project()

    def _open_project(self) -> None:
        if not self._confirm_unsaved():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", filter="SplitShot Projects (*.ssproj)")
        if path:
            self.controller.open_project(path)

    def _save_project(self) -> None:
        if self.controller.project_path is None:
            self._save_project_as()
            return
        self.controller.save_project(str(self.controller.project_path))

    def _save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", filter="SplitShot Projects (*.ssproj)")
        if path:
            self.controller.save_project(path)

    def _delete_project(self) -> None:
        if self.controller.project_path is None:
            return
        result = QMessageBox.question(
            self,
            "Delete project",
            "Delete the saved project bundle from disk?",
        )
        if result == QMessageBox.Yes:
            self.controller.delete_current_project()

    def _export_video(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export MP4", filter="MP4 Files (*.mp4)")
        if not path:
            return
        progress = QProgressDialog("Exporting video...", None, 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        try:
            export_project(
                self.controller.project,
                path,
                progress_callback=lambda value: progress.setValue(int(value * 100)),
            )
            progress.setValue(100)
            QMessageBox.information(self, "Export complete", f"Saved export to:\n{path}")
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "Export failed", str(error))
        finally:
            progress.close()

    def _confirm_unsaved(self) -> bool:
        if not self.controller.has_unsaved_changes():
            return True
        result = QMessageBox.question(
            self,
            "Unsaved changes",
            "This project has unsaved changes. Continue without saving?",
        )
        return result == QMessageBox.Yes
