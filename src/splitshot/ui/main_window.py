from __future__ import annotations

from PySide6.QtCore import QUrl, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
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
from splitshot.presentation.stage import build_stage_presentation, format_seconds_short
from splitshot.ui.controller import ProjectController
from splitshot.ui.widgets.dashboard import (
    LegendItem,
    SectionCard,
    SplitCardData,
    SplitCardGrid,
    StatCard,
    UploadDropZone,
)
from splitshot.ui.widgets.overlay_preview import OverlayPreview
from splitshot.ui.widgets.waveform_editor import WaveformEditor, WaveformState
from splitshot.utils.time import format_time_ms


SECTION_IDS = [
    "manage",
    "upload",
    "merge",
    "overlay",
    "scoring",
    "layout",
    "swap",
    "export",
]

SECTION_LABELS = {
    "manage": "Manage",
    "upload": "Upload",
    "merge": "Merge",
    "overlay": "Overlay",
    "scoring": "Scoring",
    "layout": "Layout",
    "swap": "Swap",
    "export": "Export",
}


class PreviewContainer(QWidget):
    def __init__(self, controller: ProjectController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewSurface")
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

        primary_rect = canvas.primary_rect
        self.primary_video.setGeometry(
            int(offset_x + (primary_rect.x * scale)),
            int(offset_y + (primary_rect.y * scale)),
            int(primary_rect.width * scale),
            int(primary_rect.height * scale),
        )

        if canvas.secondary_rect is not None:
            secondary_rect = canvas.secondary_rect
            self.secondary_video.setGeometry(
                int(offset_x + (secondary_rect.x * scale)),
                int(offset_y + (secondary_rect.y * scale)),
                int(secondary_rect.width * scale),
                int(secondary_rect.height * scale),
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
        self._current_section = "upload"
        self._current_primary_path = ""
        self._current_secondary_path = ""

        self.setWindowTitle("SplitShot")
        self.resize(1660, 1040)
        self.setAcceptDrops(True)

        self.primary_audio = QAudioOutput(self)
        self.primary_audio.setVolume(0.9)
        self.primary_player = QMediaPlayer(self)
        self.primary_player.setAudioOutput(self.primary_audio)

        self.secondary_player = QMediaPlayer(self)
        self.secondary_player.setAudioOutput(None)

        self.preview = PreviewContainer(controller)
        self.preview.setMinimumHeight(420)
        self.preview.primary_video.setAspectRatioMode(Qt.KeepAspectRatio)
        self.preview.secondary_video.setAspectRatioMode(Qt.KeepAspectRatio)
        self.primary_player.setVideoOutput(self.preview.primary_video)
        self.secondary_player.setVideoOutput(self.preview.secondary_video)
        self.preview.overlay.crop_center_selected.connect(self._set_crop_center_from_preview)

        self.waveform = WaveformEditor()
        self.waveform.setMinimumHeight(240)
        self.waveform.shot_added.connect(self.controller.add_shot)
        self.waveform.shot_moved.connect(self.controller.move_shot)
        self.waveform.shot_deleted.connect(self.controller.delete_shot)
        self.waveform.beep_moved.connect(self.controller.set_beep_time)
        self.waveform.seek_requested.connect(self.primary_player.setPosition)
        self.waveform.shot_selected.connect(self.controller.select_shot)

        self.secondary_waveform = WaveformEditor()
        self.secondary_waveform.setMinimumHeight(160)
        self.secondary_waveform.seek_requested.connect(self.primary_player.setPosition)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.sliderMoved.connect(self._set_position)

        self.play_button = QPushButton("Play")
        self.play_button.setProperty("primary", True)
        self.play_button.clicked.connect(self._toggle_playback)

        self.current_time_label = QLabel("0:00.000")
        self.current_time_label.setObjectName("timelineTime")
        self.duration_label = QLabel("0:00.000")
        self.duration_label.setObjectName("timelineTime")

        self.status_pill = QLabel(controller.status_message)
        self.status_pill.setObjectName("statusPill")

        self.project_title_label = QLabel("Untitled Project")
        self.project_title_label.setObjectName("projectTitle")
        self.project_detail_label = QLabel("Local-first stage review")
        self.project_detail_label.setObjectName("projectDetail")

        self.draw_card = StatCard("Draw Time", "--.--", "Upload a stage video to begin.")
        self.stage_card = StatCard("Raw Time", "--.--", "Beep to final shot, matching score Raw.")
        self.shot_count_card = StatCard("Total Shots", "0", "Automatic detections appear here.")
        self.average_split_card = StatCard("Avg Split", "--.--", "Average split after the draw.")

        self.empty_upload = UploadDropZone(
            "Upload a stage video",
            "SplitShot will probe the file, detect the timer beep, find shots, and open the waveform editor automatically.",
            "Choose primary video",
        )
        self.empty_upload.upload_requested.connect(self._load_primary_video)
        self.empty_upload.file_dropped.connect(self._ingest_primary_video)

        self.split_cards = SplitCardGrid()
        self.split_cards.setMinimumHeight(340)
        self.split_cards.shot_selected.connect(self.controller.select_shot)

        self.preview_card = SectionCard("Stage Review", "A large, playback-ready canvas for the current angle.")
        self.waveform_card = SectionCard(
            "Interactive Waveform Editor",
            "Click to add shot | Drag to move | Right-click to delete | Shift+Click the beep to move",
        )
        self.secondary_waveform_card = SectionCard(
            "Secondary Sync Waveform",
            "Review the secondary angle alignment after automatic beep-based sync.",
        )
        self.splits_card = SectionCard(
            "Split Times",
            "Click a split card to select a shot for scoring or manual review.",
        )

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(10)
        self.threshold_slider.setMaximum(90)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)

        self.overlay_position = QComboBox()
        for option in OverlayPosition:
            self.overlay_position.addItem(option.value, option)
        self.overlay_position.currentIndexChanged.connect(self._on_overlay_position_changed)

        self.badge_size = QComboBox()
        for option in BadgeSize:
            self.badge_size.addItem(option.value, option)
        self.badge_size.currentIndexChanged.connect(self._on_badge_size_changed)

        self.merge_enabled = QCheckBox("Enable dual-angle merge")
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

        self.place_score = QCheckBox("Place selected score on preview")
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

        self.primary_upload_button = QPushButton("Upload primary video")
        self.primary_upload_button.setProperty("primary", True)
        self.primary_upload_button.clicked.connect(self._load_primary_video)

        self.secondary_upload_button = QPushButton("Add second angle")
        self.secondary_upload_button.clicked.connect(self._load_secondary_video)

        self.rerun_primary_button = QPushButton("Re-run primary analysis")
        self.rerun_primary_button.clicked.connect(self.controller.analyze_primary)

        self.rerun_secondary_button = QPushButton("Re-run secondary analysis")
        self.rerun_secondary_button.clicked.connect(self.controller.analyze_secondary)

        self.swap_videos_button = QPushButton("Swap primary and secondary")
        self.swap_videos_button.clicked.connect(self.controller.swap_videos)

        self.export_button = QPushButton("Export MP4")
        self.export_button.setProperty("primary", True)
        self.export_button.clicked.connect(self._export_video)

        self.new_project_button = QPushButton("New project")
        self.new_project_button.clicked.connect(self._new_project)
        self.open_project_button = QPushButton("Open project")
        self.open_project_button.clicked.connect(self._open_project)
        self.save_project_button = QPushButton("Save project")
        self.save_project_button.clicked.connect(self._save_project)
        self.save_project_as_button = QPushButton("Save project as")
        self.save_project_as_button.clicked.connect(self._save_project_as)
        self.delete_project_button = QPushButton("Delete project")
        self.delete_project_button.setProperty("danger", True)
        self.delete_project_button.clicked.connect(self._delete_project)

        self.recent_projects_combo = QComboBox()
        self.recent_projects_combo.addItem("No recent projects", "")
        self.recent_projects_combo.currentIndexChanged.connect(self._open_recent_project)

        self.manage_path_label = QLabel("Not saved yet")
        self.manage_path_label.setObjectName("panelInfo")
        self.manage_dirty_label = QLabel("No unsaved changes")
        self.manage_dirty_label.setObjectName("panelInfo")
        self.manage_sync_label = QLabel("Upload a second angle to enable merge review.")
        self.manage_sync_label.setObjectName("panelInfo")
        self.upload_summary_label = QLabel("")
        self.upload_summary_label.setObjectName("panelInfo")
        self.merge_summary_label = QLabel("")
        self.merge_summary_label.setObjectName("panelInfo")
        self.scoring_target_label = QLabel("Select a shot from the waveform or split cards.")
        self.scoring_target_label.setObjectName("panelInfo")
        self.layout_summary_label = QLabel("Original framing.")
        self.layout_summary_label.setObjectName("panelInfo")
        self.export_summary_label = QLabel("H.264 MP4 export with overlays and scoring.")
        self.export_summary_label.setObjectName("panelInfo")

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(18)
        root_layout.addWidget(self._build_navigation())
        root_layout.addWidget(self._build_center_area(), stretch=1)
        root_layout.addWidget(self._build_inspector())

        self._build_menu()
        self._connect_signals()
        self.refresh_ui()

    def _build_navigation(self) -> QWidget:
        nav = QFrame()
        nav.setObjectName("navigationRail")
        nav.setFixedWidth(144)

        brand = QLabel("SplitShot")
        brand.setObjectName("brandLabel")

        sublabel = QLabel("Local shot review")
        sublabel.setObjectName("brandSubLabel")

        self.section_group = QButtonGroup(self)
        self.section_group.setExclusive(True)
        self.section_buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(nav)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(12)
        layout.addWidget(brand)
        layout.addWidget(sublabel)
        layout.addSpacing(10)

        for section_id in SECTION_IDS:
            button = QPushButton(SECTION_LABELS[section_id])
            button.setCheckable(True)
            button.setProperty("navButton", True)
            button.clicked.connect(lambda checked, key=section_id: self._select_section(key))
            self.section_group.addButton(button)
            self.section_buttons[section_id] = button
            layout.addWidget(button)

        layout.addStretch(1)
        self.section_buttons[self._current_section].setChecked(True)
        return nav

    def _build_center_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        header = QFrame()
        header.setObjectName("topHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(18)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        title_layout.addWidget(self.project_title_label)
        title_layout.addWidget(self.project_detail_label)

        header_layout.addLayout(title_layout, stretch=1)
        header_layout.addWidget(self.status_pill, alignment=Qt.AlignRight | Qt.AlignVCenter)

        self.center_stack = QStackedWidget()
        self.center_stack.addWidget(self._build_empty_state_page())
        self.center_stack.addWidget(self._build_review_page())

        layout.addWidget(header)
        layout.addWidget(self.center_stack, stretch=1)
        return container

    def _build_empty_state_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        intro = SectionCard(
            "Automatic stage analysis",
            "Upload once and SplitShot immediately detects the timer beep, shot events, and split timing for review.",
        )
        intro.content_layout.addWidget(self.empty_upload)
        layout.addWidget(intro)

        tips = SectionCard(
            "What happens next",
            "The loaded review screen opens automatically with playback, waveform editing, split cards, merge tools, overlays, scoring, and export controls.",
        )
        layout.addWidget(tips)
        layout.addStretch(1)
        return page

    def _build_review_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(18)

        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(0, 0, 0, 0)
        stats_row.setSpacing(16)
        for card in [self.draw_card, self.stage_card, self.shot_count_card, self.average_split_card]:
            stats_row.addWidget(card, stretch=1)
        layout.addLayout(stats_row)

        preview_frame = QFrame()
        preview_frame.setObjectName("panelCard")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)
        preview_layout.addWidget(self.preview)

        preview_controls = QHBoxLayout()
        preview_controls.setContentsMargins(16, 14, 16, 16)
        preview_controls.setSpacing(12)
        preview_controls.addWidget(self.play_button)
        preview_controls.addWidget(self.current_time_label)
        preview_controls.addWidget(self.position_slider, stretch=1)
        preview_controls.addWidget(self.duration_label)
        preview_controls.addWidget(self.secondary_upload_button)
        preview_layout.addLayout(preview_controls)
        self.preview_card.content_layout.addWidget(preview_frame)
        layout.addWidget(self.preview_card)

        self.waveform_card.content_layout.addWidget(self.waveform)
        legend_row = QHBoxLayout()
        legend_row.setContentsMargins(0, 0, 0, 0)
        legend_row.setSpacing(20)
        legend_row.addWidget(LegendItem("Timer Beep", "#F97316"))
        legend_row.addWidget(LegendItem("Shot", "#22C55E"))
        legend_row.addWidget(LegendItem("Playhead", "#EF4444"))
        legend_row.addStretch(1)
        legend_host = QWidget()
        legend_host.setLayout(legend_row)
        self.waveform_card.content_layout.addWidget(legend_host)
        layout.addWidget(self.waveform_card)

        self.secondary_waveform_card.content_layout.addWidget(self.secondary_waveform)
        layout.addWidget(self.secondary_waveform_card)

        self.splits_card.content_layout.addWidget(self.split_cards)
        layout.addWidget(self.splits_card)
        layout.addStretch(1)

        scroll.setWidget(content)
        return scroll

    def _build_inspector(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("inspectorShell")
        wrapper.setFixedWidth(360)

        self.inspector_stack = QStackedWidget()
        for builder in [
            self._build_manage_panel,
            self._build_upload_panel,
            self._build_merge_panel,
            self._build_overlay_panel,
            self._build_scoring_panel,
            self._build_layout_panel,
            self._build_swap_panel,
            self._build_export_panel,
        ]:
            self.inspector_stack.addWidget(builder())

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.inspector_stack)
        return wrapper

    def _build_manage_panel(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        project_card = SectionCard("Project Management", "Local project bundles for save, reopen, and delete.")
        project_card.content_layout.addWidget(self.new_project_button)
        project_card.content_layout.addWidget(self.open_project_button)
        project_card.content_layout.addWidget(self.save_project_button)
        project_card.content_layout.addWidget(self.save_project_as_button)
        project_card.content_layout.addWidget(self.delete_project_button)
        layout.addWidget(project_card)

        details_card = SectionCard("Current Project", "Status for the active local project file.")
        details_form = QFormLayout()
        details_form.setContentsMargins(0, 0, 0, 0)
        details_form.addRow("Project file", self.manage_path_label)
        details_form.addRow("Changes", self.manage_dirty_label)
        details_form.addRow("Merge sync", self.manage_sync_label)
        details_card.content_layout.addLayout(details_form)
        layout.addWidget(details_card)

        recent_card = SectionCard("Recent Projects", "Jump back into a recent local save.")
        recent_card.content_layout.addWidget(self.recent_projects_combo)
        layout.addWidget(recent_card)
        layout.addStretch(1)
        return self._wrap_panel(page)

    def _build_upload_panel(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        ingest_card = SectionCard(
            "Upload And Analyze",
            "Primary upload starts automatic analysis. Secondary upload auto-syncs against the primary beep.",
        )
        ingest_card.content_layout.addWidget(self.primary_upload_button)
        ingest_card.content_layout.addWidget(self.secondary_upload_button)
        ingest_card.content_layout.addWidget(self.rerun_primary_button)
        ingest_card.content_layout.addWidget(self.rerun_secondary_button)
        ingest_card.content_layout.addWidget(self.upload_summary_label)
        layout.addWidget(ingest_card)

        analysis_card = SectionCard("Detection Threshold", "Lower values are more sensitive. Higher values are stricter.")
        analysis_form = QFormLayout()
        analysis_form.setContentsMargins(0, 0, 0, 0)
        analysis_form.addRow("Threshold", self.threshold_slider)
        analysis_form.addRow(self.restore_defaults_button)
        analysis_card.content_layout.addLayout(analysis_form)
        layout.addWidget(analysis_card)
        layout.addStretch(1)
        return self._wrap_panel(page)

    def _build_merge_panel(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        merge_card = SectionCard("Dual-Angle Merge", "Automatic sync uses detected beeps and stays editable in milliseconds.")
        merge_form = QFormLayout()
        merge_form.setContentsMargins(0, 0, 0, 0)
        merge_form.addRow(self.merge_enabled)
        merge_form.addRow("Layout", self.merge_layout)
        merge_form.addRow("PiP size", self.pip_size)
        merge_card.content_layout.addLayout(merge_form)

        offset_host = QWidget()
        offset_layout = QHBoxLayout(offset_host)
        offset_layout.setContentsMargins(0, 0, 0, 0)
        offset_layout.setSpacing(8)
        for label, delta in [("-10 ms", -10), ("-1 ms", -1), ("+1 ms", 1), ("+10 ms", 10)]:
            button = QPushButton(label)
            button.clicked.connect(lambda _, value=delta: self.controller.adjust_sync_offset(value))
            offset_layout.addWidget(button)
        merge_card.content_layout.addWidget(offset_host)
        merge_card.content_layout.addWidget(self.merge_summary_label)
        layout.addWidget(merge_card)
        layout.addStretch(1)
        return self._wrap_panel(page)

    def _build_overlay_panel(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        overlay_card = SectionCard("Shot Stream Overlay", "Badge styling and placement apply to preview and export.")
        overlay_form = QFormLayout()
        overlay_form.setContentsMargins(0, 0, 0, 0)
        overlay_form.addRow("Position", self.overlay_position)
        overlay_form.addRow("Badge size", self.badge_size)
        overlay_form.addRow("Style target", self.style_target)
        overlay_form.addRow(self.background_button)
        overlay_form.addRow(self.text_button)
        overlay_form.addRow("Opacity", self.opacity_slider)
        overlay_card.content_layout.addLayout(overlay_form)
        layout.addWidget(overlay_card)
        layout.addStretch(1)
        return self._wrap_panel(page)

    def _build_scoring_panel(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        scoring_card = SectionCard("Scoring", "Assign score letters, penalties, and animated placement from the loaded review.")
        scoring_form = QFormLayout()
        scoring_form.setContentsMargins(0, 0, 0, 0)
        scoring_form.addRow(self.scoring_enabled)
        scoring_form.addRow("Selected score", self.score_letter)
        scoring_form.addRow(self.score_color_button)
        scoring_form.addRow("Penalty points", self.penalties_input)
        scoring_form.addRow(self.place_score)
        scoring_card.content_layout.addWidget(self.scoring_target_label)
        scoring_card.content_layout.addLayout(scoring_form)
        layout.addWidget(scoring_card)
        layout.addStretch(1)
        return self._wrap_panel(page)

    def _build_layout_panel(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout_card = SectionCard("Export Layout", "Choose export framing and drag the crop center directly on the preview.")
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("Aspect ratio", self.aspect_ratio)
        form.addRow("Crop X", self.crop_x)
        form.addRow("Crop Y", self.crop_y)
        form.addRow(self.drag_crop)
        layout_card.content_layout.addWidget(self.layout_summary_label)
        layout_card.content_layout.addLayout(form)
        layout.addWidget(layout_card)
        layout.addStretch(1)
        return self._wrap_panel(page)

    def _build_swap_panel(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        swap_card = SectionCard("Swap Angles", "Flip which video leads the preview and the waveform timing reference.")
        swap_card.content_layout.addWidget(self.swap_videos_button)
        layout.addWidget(swap_card)
        layout.addStretch(1)
        return self._wrap_panel(page)

    def _build_export_panel(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        export_card = SectionCard("Export MP4", "Local H.264 export keeps overlays, scoring, and selected layout settings.")
        export_form = QFormLayout()
        export_form.setContentsMargins(0, 0, 0, 0)
        export_form.addRow("Quality", self.export_quality)
        export_card.content_layout.addWidget(self.export_summary_label)
        export_card.content_layout.addLayout(export_form)
        export_card.content_layout.addWidget(self.export_button)
        layout.addWidget(export_card)
        layout.addStretch(1)
        return self._wrap_panel(page)

    def _wrap_panel(self, widget: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(widget)
        return scroll

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

        ingest_menu = menu.addMenu("Analyze")
        primary_action = QAction("Upload Primary And Analyze", self)
        primary_action.triggered.connect(self._load_primary_video)
        ingest_menu.addAction(primary_action)
        secondary_action = QAction("Upload Secondary And Sync", self)
        secondary_action.triggered.connect(self._load_secondary_video)
        ingest_menu.addAction(secondary_action)
        rerun_primary_action = QAction("Re-run Primary Analysis", self)
        rerun_primary_action.triggered.connect(self.controller.analyze_primary)
        ingest_menu.addAction(rerun_primary_action)
        rerun_secondary_action = QAction("Re-run Secondary Analysis", self)
        rerun_secondary_action.triggered.connect(self.controller.analyze_secondary)
        ingest_menu.addAction(rerun_secondary_action)

    def _connect_signals(self) -> None:
        self.controller.project_changed.connect(self.refresh_ui)
        self.controller.settings_changed.connect(self.refresh_ui)
        self.controller.status_changed.connect(self._update_status)
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
        self.project_title_label.setText(project.name)
        project_path_text = "Unsaved local project" if self.controller.project_path is None else str(self.controller.project_path)
        self.project_detail_label.setText(project_path_text)
        self.status_pill.setText(self.controller.status_message)

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

        self.penalties_input.blockSignals(True)
        self.penalties_input.setValue(project.scoring.penalties)
        self.penalties_input.blockSignals(False)

        selected_shot = next(
            (shot for shot in project.analysis.shots if shot.id == project.ui_state.selected_shot_id),
            None,
        )
        self.score_letter.blockSignals(True)
        self.score_letter.setCurrentIndex(
            self.score_letter.findData(
                ScoreLetter.A if selected_shot is None or selected_shot.score is None else selected_shot.score.letter
            )
        )
        self.score_letter.blockSignals(False)

        self._sync_badge_style_controls()
        self._update_media_sources()
        self._update_review_visibility()
        self._update_stats()
        self._update_waveform()
        self._update_secondary_waveform()
        self._update_split_cards()
        self._update_status_labels()
        self._update_navigation()
        self._update_enablement()
        self.preview.overlay.set_state(project, self.primary_player.position())
        self.preview.update()

    def _update_media_sources(self) -> None:
        project = self.controller.project
        if project.primary_video.path:
            if project.primary_video.path != self._current_primary_path:
                self.primary_player.setSource(QUrl.fromLocalFile(project.primary_video.path))
                self._current_primary_path = project.primary_video.path
        elif self._current_primary_path:
            self.primary_player.setSource(QUrl())
            self._current_primary_path = ""

        if project.secondary_video and project.secondary_video.path:
            if project.secondary_video.path != self._current_secondary_path:
                self.secondary_player.setSource(QUrl.fromLocalFile(project.secondary_video.path))
                self._current_secondary_path = project.secondary_video.path
        elif self._current_secondary_path:
            self.secondary_player.setSource(QUrl())
            self._current_secondary_path = ""

        self.preview.update()

    def _update_review_visibility(self) -> None:
        has_primary = bool(self.controller.project.primary_video.path)
        self.center_stack.setCurrentIndex(1 if has_primary else 0)

    def _update_stats(self) -> None:
        project = self.controller.project
        presentation = build_stage_presentation(project)
        metrics = presentation.metrics

        self.draw_card.set_content(
            "Draw Time",
            format_seconds_short(metrics.draw_ms),
            "Seconds to the first shot." if metrics.draw_ms is not None else "Waiting for a detected beep and first shot.",
        )
        self.stage_card.set_content(
            "Raw Time",
            format_seconds_short(metrics.raw_time_ms),
            "Beep to final shot, matching score Raw." if metrics.raw_time_ms is not None else "Raw time appears after analysis.",
        )
        self.shot_count_card.set_content(
            "Total Shots",
            str(metrics.total_shots),
            "Auto detected." if metrics.total_shots else "No shots detected yet.",
        )
        self.average_split_card.set_content(
            "Avg Split",
            format_seconds_short(metrics.average_split_ms),
            "Average split after the draw." if metrics.average_split_ms is not None else "Average split needs multiple shots.",
        )

        merge_meta = "Single angle review"
        if project.secondary_video is not None:
            merge_meta = f"Dual angle sync {project.analysis.sync_offset_ms:+d} ms"
        self.preview_card.set_meta_text(merge_meta)
        self.waveform_card.set_meta_text(f"{metrics.total_shots} shots")
        self.secondary_waveform_card.setVisible(project.secondary_video is not None)

    def _update_waveform(self) -> None:
        project = self.controller.project
        duration = max(1, project.primary_video.duration_ms or self.primary_player.duration() or 1)
        self.waveform.set_state(
            WaveformState(
                duration_ms=duration,
                waveform=project.analysis.waveform_primary,
                secondary_waveform=project.analysis.waveform_secondary if project.secondary_video else None,
                shots=project.analysis.shots,
                beep_time_ms=project.analysis.beep_time_ms_primary,
                secondary_beep_time_ms=project.analysis.beep_time_ms_secondary if project.secondary_video else None,
                playhead_ms=self.primary_player.position(),
                zoom=project.ui_state.timeline_zoom,
                offset_ms=project.ui_state.timeline_offset_ms,
                selected_shot_id=project.ui_state.selected_shot_id,
                frame_nudge_ms=max(1, int(round(1000 / max(1.0, project.primary_video.fps or 30.0)))),
            )
        )

    def _update_secondary_waveform(self) -> None:
        project = self.controller.project
        if project.secondary_video is None:
            self.secondary_waveform.set_state(WaveformState())
            return

        playhead_ms = max(0, self.primary_player.position() + project.analysis.sync_offset_ms)
        duration = max(1, project.secondary_video.duration_ms or project.primary_video.duration_ms or 1)
        self.secondary_waveform.set_state(
            WaveformState(
                duration_ms=duration,
                waveform=project.analysis.waveform_secondary,
                shots=[],
                beep_time_ms=project.analysis.beep_time_ms_secondary,
                playhead_ms=playhead_ms,
            )
        )

    def _update_split_cards(self) -> None:
        project = self.controller.project
        cards: list[SplitCardData] = []
        presentation = build_stage_presentation(project)
        for segment in presentation.timing_segments:
            cards.append(
                SplitCardData(
                    shot_id=segment.shot_id,
                    title=segment.card_title,
                    value=segment.card_value,
                    subtitle=segment.card_subtitle,
                    meta=segment.card_meta,
                )
            )

        self.split_cards.set_cards(cards, project.ui_state.selected_shot_id)

    def _update_status_labels(self) -> None:
        project = self.controller.project
        has_primary = bool(project.primary_video.path)
        has_secondary = project.secondary_video is not None and bool(project.secondary_video.path)

        self.manage_path_label.setText(
            "Not saved yet" if self.controller.project_path is None else str(self.controller.project_path)
        )
        self.manage_dirty_label.setText(
            "Unsaved changes" if self.controller.has_unsaved_changes() else "Saved to disk or unchanged"
        )
        self.manage_sync_label.setText(
            "Waiting for a second angle."
            if not has_secondary
            else f"Automatic offset {project.analysis.sync_offset_ms:+d} ms."
        )

        self.upload_summary_label.setText(self.controller.status_message)
        self.merge_summary_label.setText(
            "Upload a second angle to unlock automatic sync."
            if not has_secondary
            else f"Primary beep {project.analysis.beep_time_ms_primary} ms | Secondary beep {project.analysis.beep_time_ms_secondary} ms | Offset {project.analysis.sync_offset_ms:+d} ms"
        )

        selected_shot = next(
            (shot for shot in project.analysis.shots if shot.id == project.ui_state.selected_shot_id),
            None,
        )
        if selected_shot is None:
            self.scoring_target_label.setText("Select a shot from the waveform or split cards.")
        else:
            self.scoring_target_label.setText(
                f"Selected shot at {format_time_ms(selected_shot.time_ms)}."
            )

        aspect = project.export.aspect_ratio.value
        self.layout_summary_label.setText(
            f"Aspect {aspect} | Crop {int(project.export.crop_center_x * 100)}% x, {int(project.export.crop_center_y * 100)}% y"
        )
        self.export_summary_label.setText(
            f"{project.export.quality.value.title()} quality H.264 MP4 with overlay position {project.overlay.position.value}."
        )

        self.current_time_label.setText(format_time_ms(self.primary_player.position()))
        duration = project.primary_video.duration_ms or self.primary_player.duration()
        self.duration_label.setText(format_time_ms(duration))

        self._populate_recent_projects()

    def _populate_recent_projects(self) -> None:
        current_value = self.recent_projects_combo.currentData()
        self.recent_projects_combo.blockSignals(True)
        self.recent_projects_combo.clear()
        self.recent_projects_combo.addItem("Recent projects", "")
        for path in self.controller.settings.recent_projects:
            self.recent_projects_combo.addItem(path, path)
        index = self.recent_projects_combo.findData(current_value)
        if index >= 0:
            self.recent_projects_combo.setCurrentIndex(index)
        else:
            self.recent_projects_combo.setCurrentIndex(0)
        self.recent_projects_combo.blockSignals(False)

    def _update_navigation(self) -> None:
        index = SECTION_IDS.index(self._current_section)
        self.inspector_stack.setCurrentIndex(index)
        for section_id, button in self.section_buttons.items():
            button.blockSignals(True)
            button.setChecked(section_id == self._current_section)
            button.blockSignals(False)

    def _update_enablement(self) -> None:
        project = self.controller.project
        has_primary = bool(project.primary_video.path)
        has_secondary = project.secondary_video is not None and bool(project.secondary_video.path)
        has_selected_shot = project.ui_state.selected_shot_id is not None

        self.play_button.setEnabled(has_primary)
        self.position_slider.setEnabled(has_primary)
        self.secondary_upload_button.setEnabled(has_primary)
        self.rerun_primary_button.setEnabled(has_primary)
        self.rerun_secondary_button.setEnabled(has_secondary)
        self.merge_enabled.setEnabled(has_secondary)
        self.merge_layout.setEnabled(has_secondary)
        self.pip_size.setEnabled(has_secondary)
        self.swap_videos_button.setEnabled(has_secondary)
        self.export_button.setEnabled(has_primary)
        self.delete_project_button.setEnabled(self.controller.project_path is not None)
        self.score_letter.setEnabled(has_selected_shot)
        self.score_color_button.setEnabled(has_selected_shot)
        self.place_score.setEnabled(has_selected_shot)

        enabled_sections = {
            "manage": True,
            "upload": True,
            "merge": has_primary,
            "overlay": has_primary,
            "scoring": has_primary,
            "layout": has_primary,
            "swap": has_secondary,
            "export": has_primary,
        }
        for section_id, button in self.section_buttons.items():
            button.setEnabled(enabled_sections[section_id])

        if not enabled_sections.get(self._current_section, False):
            self._select_section("upload")

    def _select_section(self, section_id: str) -> None:
        if not self.section_buttons[section_id].isEnabled():
            return
        self._current_section = section_id
        self._update_navigation()

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
        self.current_time_label.setText(format_time_ms(position))
        self.preview.overlay.set_state(self.controller.project, position)
        self._update_waveform()
        self._update_secondary_waveform()

    def _on_duration_changed(self, duration: int) -> None:
        self.position_slider.setMaximum(max(0, duration))
        self.duration_label.setText(format_time_ms(duration))
        self._update_waveform()

    def _on_playback_state_changed(self, state) -> None:
        self.play_button.setText("Pause" if state == QMediaPlayer.PlayingState else "Play")

    def _sync_secondary(self, force: bool = False) -> None:
        project = self.controller.project
        if not project.merge.enabled or project.secondary_video is None:
            self.secondary_player.pause()
            return

        target_position = max(0, self.primary_player.position() + project.analysis.sync_offset_ms)
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
            self._ingest_primary_video(path)

    def _load_secondary_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Secondary Video")
        if path:
            self._ingest_secondary_video(path)

    def _ingest_primary_video(self, path: str) -> None:
        self._run_busy_task("Importing and analyzing primary video...", lambda: self.controller.ingest_primary_video(path))
        self._select_section("upload")

    def _ingest_secondary_video(self, path: str) -> None:
        self._run_busy_task(
            "Importing, analyzing, and syncing secondary video...",
            lambda: self.controller.ingest_secondary_video(path),
        )
        self._select_section("merge")

    def _run_busy_task(self, message: str, task) -> None:
        progress = QProgressDialog(message, None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()
        QApplication.processEvents()
        try:
            task()
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "Operation failed", str(error))
        finally:
            progress.close()

    def _new_project(self) -> None:
        if not self._confirm_unsaved():
            return
        self.primary_player.stop()
        self.secondary_player.stop()
        self.controller.new_project()
        self._select_section("upload")

    def _open_project(self) -> None:
        if not self._confirm_unsaved():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", filter="SplitShot Projects (*.ssproj)")
        if path:
            self.controller.open_project(path)
            self._select_section("manage")

    def _open_recent_project(self) -> None:
        path = self.recent_projects_combo.currentData()
        if not path:
            return
        if not self._confirm_unsaved():
            self.recent_projects_combo.blockSignals(True)
            self.recent_projects_combo.setCurrentIndex(0)
            self.recent_projects_combo.blockSignals(False)
            return
        self.controller.open_project(path)
        self._select_section("manage")

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
            self._select_section("upload")

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

    def _update_status(self, message: str) -> None:
        self.status_pill.setText(message)
        self.upload_summary_label.setText(message)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if not self.controller.project.primary_video.path:
                self._ingest_primary_video(path)
            elif self.controller.project.secondary_video is None:
                self._ingest_secondary_video(path)
            else:
                QMessageBox.information(
                    self,
                    "Videos already loaded",
                    "This project already has a primary and secondary angle. Start a new project to load different files.",
                )
            event.acceptProposedAction()
            return
        event.ignore()
