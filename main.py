import sys
import os
import json
import base64
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, 
    QMessageBox, QProgressBar, QCheckBox, QScrollArea, QStackedWidget,
    QSlider, QStyle, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QByteArray, QTime
from PyQt6.QtGui import QFont, QIcon, QPixmap, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

# Optional video support check
try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

# App's secret internal pepper combined with user password
APP_INTERNAL_PEPPER = b"SecureVaultApp_v1_ProtectedSecretRecipe_2026_XYZ"

# Expanded allowed media formats (Images and Videos only)
ALLOWED_IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.heic', '.tiff', '.svg']
ALLOWED_VIDEO_EXTS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.ts', '.m2ts', '.webm', '.m4v']

def create_svg_icon(svg_string: str, width: int = 24, height: int = 24) -> QIcon:
    """Renders an SVG string into a QIcon using QSvgRenderer."""
    renderer = QSvgRenderer(QByteArray(svg_string.encode('utf-8')))
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

# Inline clean SVGs for UI components with high-contrast visible strokes (#2563eb or #ffffff for buttons)
SVG_LOCK = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>'''
SVG_UNLOCK = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path></svg>'''
SVG_FOLDER = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#4b5563" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>'''
SVG_PLAY = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>'''
SVG_PAUSE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>'''
SVG_VOLUME = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>'''
SVG_EYE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>'''
SVG_EXPORT = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>'''

def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a strong 32-byte Fernet key using PBKDF2 with SHA-256."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    
    combined_secret = password.encode('utf-8') + APP_INTERNAL_PEPPER
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(combined_secret))

class EncryptionWorker(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)

    def __init__(self, input_path, output_path, password):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.password = password

    def run(self):
        try:
            from cryptography.fernet import Fernet
            
            self.progress.emit(10)
            filename = os.path.basename(self.input_path)
            _, ext = os.path.splitext(filename)
            
            with open(self.input_path, 'rb') as f:
                file_data = f.read()
            
            self.progress.emit(30)
            salt = os.urandom(16)
            key = derive_key(self.password, salt)
            f_cipher = Fernet(key)
            
            self.progress.emit(60)
            encrypted_data = f_cipher.encrypt(file_data)
            
            self.progress.emit(80)
            vault_package = {
                "version": "2.2",
                "filename": filename,
                "extension": ext.lower(),
                "salt": base64.b64encode(salt).decode('utf-8'),
                "payload": base64.b64encode(encrypted_data).decode('utf-8')
            }
            
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(vault_package, f)
                
            self.progress.emit(100)
            self.finished.emit(True, f"Media file encrypted successfully! Extension '{ext.lower()}' securely stored.")
        except Exception as e:
            self.finished.emit(False, str(e))

class DecryptionWorker(QThread):
    finished = pyqtSignal(bool, str, dict)
    progress = pyqtSignal(int)

    def __init__(self, input_path, password):
        super().__init__()
        self.input_path = input_path
        self.password = password

    def run(self):
        try:
            from cryptography.fernet import Fernet
            
            self.progress.emit(20)
            with open(self.input_path, 'r', encoding='utf-8') as f:
                vault_package = json.load(f)
                
            salt = base64.b64decode(vault_package["salt"].encode('utf-8'))
            encrypted_data = base64.b64decode(vault_package["payload"].encode('utf-8'))
            
            self.progress.emit(50)
            key = derive_key(self.password, salt)
            f_cipher = Fernet(key)
            
            self.progress.emit(75)
            decrypted_data = f_cipher.decrypt(encrypted_data)
            
            vault_package["decrypted_bytes"] = decrypted_data
                    
            self.progress.emit(100)
            self.finished.emit(True, "Vault unlocked successfully!", vault_package)
        except Exception as e:
            self.finished.emit(False, "Decryption failed! Incorrect password or corrupted vault package.", {})

class SecureVaultWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure Media Vault - Professional Edition")
        self.setMinimumSize(950, 720)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fafc;
            }
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                background: #ffffff;
                border-radius: 12px;
            }
            QTabBar::tab {
                background: #f1f5f9;
                color: #475569;
                padding: 14px 32px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 6px;
                font-weight: 600;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background: #2563eb;
                color: #ffffff;
            }
            QLabel {
                color: #1e293b;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 10px;
                color: #0f172a;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
            QPushButton#secondaryBtn {
                background-color: #e2e8f0;
                color: #334155;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #cbd5e1;
            }
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                text-align: center;
                color: #1e293b;
                background-color: #f1f5f9;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 7px;
            }
            QCheckBox {
                color: #334155;
                font-size: 13px;
                spacing: 8px;
            }
        """)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.encrypt_tab = QWidget()
        self.decrypt_tab = QWidget()

        self.tabs.addTab(self.encrypt_tab, "Encrypt Media")
        self.tabs.addTab(self.decrypt_tab, "Decrypt Vault & View")

        self.tabs.setTabIcon(0, create_svg_icon(SVG_LOCK, 18, 18))
        self.tabs.setTabIcon(1, create_svg_icon(SVG_UNLOCK, 18, 18))

        self.setup_encrypt_tab()
        self.setup_decrypt_tab()

    def setup_encrypt_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        title = QLabel("Secure Media Encryption")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Select any photo or video file (.mp4, .ts, .m2ts, .png, .jpg, .webp, etc.). File extension and metadata are securely bound inside the encrypted vault container.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #64748b; font-size: 13px;")
        layout.addWidget(subtitle)

        file_layout = QHBoxLayout()
        self.enc_file_input = QLineEdit()
        self.enc_file_input.setPlaceholderText("Select image or video file...")
        self.enc_file_input.setReadOnly(True)
        
        file_btn = QPushButton("Browse")
        file_btn.setObjectName("secondaryBtn")
        file_btn.setFixedWidth(110)
        file_btn.setIcon(create_svg_icon(SVG_FOLDER, 16, 16))
        file_btn.clicked.connect(self.browse_encrypt_file)
        
        file_layout.addWidget(self.enc_file_input)
        file_layout.addWidget(file_btn)
        layout.addLayout(file_layout)

        self.enc_pass_input = QLineEdit()
        self.enc_pass_input.setPlaceholderText("Enter vault password...")
        self.enc_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.enc_pass_input)

        self.enc_confirm_input = QLineEdit()
        self.enc_confirm_input.setPlaceholderText("Confirm vault password...")
        self.enc_confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.enc_confirm_input)

        self.enc_show_pass = QCheckBox("Show Passwords")
        self.enc_show_pass.stateChanged.connect(self.toggle_encrypt_passwords)
        layout.addWidget(self.enc_show_pass)

        self.enc_progress = QProgressBar()
        self.enc_progress.setValue(0)
        self.enc_progress.setFixedHeight(24)
        layout.addWidget(self.enc_progress)

        self.enc_btn = QPushButton("Encrypt & Save Vault Package")
        self.enc_btn.clicked.connect(self.start_encryption)
        layout.addWidget(self.enc_btn)

        layout.addStretch()
        self.encrypt_tab.setLayout(layout)

    def setup_decrypt_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("Decrypt & Interactive Vault Viewer")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Select an encrypted vault file, enter your password, and verify. Once unlocked, choose whether to view the media directly in-app or export it back in its original format.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #64748b; font-size: 13px;")
        layout.addWidget(subtitle)

        file_layout = QHBoxLayout()
        self.dec_file_input = QLineEdit()
        self.dec_file_input.setPlaceholderText("Select encrypted .vault file...")
        self.dec_file_input.setReadOnly(True)
        
        dec_browse = QPushButton("Browse")
        dec_browse.setObjectName("secondaryBtn")
        dec_browse.setFixedWidth(100)
        dec_browse.setIcon(create_svg_icon(SVG_FOLDER, 16, 16))
        dec_browse.clicked.connect(self.browse_decrypt_file)
        
        file_layout.addWidget(self.dec_file_input)
        file_layout.addWidget(dec_browse)
        layout.addLayout(file_layout)

        pass_layout = QHBoxLayout()
        self.dec_pass_input = QLineEdit()
        self.dec_pass_input.setPlaceholderText("Enter vault password...")
        self.dec_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.dec_show_pass = QCheckBox("Show")
        self.dec_show_pass.stateChanged.connect(lambda state: self.toggle_password_visibility(self.dec_pass_input, state))
        
        verify_btn = QPushButton("Unlock Vault")
        verify_btn.setFixedWidth(150)
        verify_btn.clicked.connect(self.unlock_vault_package)
        
        pass_layout.addWidget(self.dec_pass_input)
        pass_layout.addWidget(self.dec_show_pass)
        pass_layout.addWidget(verify_btn)
        layout.addLayout(pass_layout)

        # Action panel after successful unlock (contains View & Export buttons)
        self.action_panel = QWidget()
        action_layout = QHBoxLayout(self.action_panel)
        action_layout.setContentsMargins(0, 5, 0, 5)
        
        self.meta_info_lbl = QLabel("Status: Vault locked.")
        self.meta_info_lbl.setStyleSheet("font-weight: bold; color: #475569;")
        
        self.view_unlocked_btn = QPushButton("View Media")
        self.view_unlocked_btn.setIcon(create_svg_icon(SVG_EYE, 16, 16))
        self.view_unlocked_btn.setFixedWidth(140)
        self.view_unlocked_btn.setEnabled(False)
        self.view_unlocked_btn.clicked.connect(self.show_media_in_viewer)
        
        self.export_unlocked_btn = QPushButton("Export Original File")
        self.export_unlocked_btn.setObjectName("secondaryBtn")
        self.export_unlocked_btn.setIcon(create_svg_icon(SVG_EXPORT, 16, 16))
        self.export_unlocked_btn.setFixedWidth(180)
        self.export_unlocked_btn.setEnabled(False)
        self.export_unlocked_btn.clicked.connect(self.export_decrypted_file)
        
        action_layout.addWidget(self.meta_info_lbl)
        action_layout.addStretch()
        action_layout.addWidget(self.view_unlocked_btn)
        action_layout.addWidget(self.export_unlocked_btn)
        layout.addWidget(self.action_panel)

        # Viewer stack for Image or Video Player
        self.viewer_stack = QStackedWidget()
        self.viewer_stack.setStyleSheet("background-color: #f1f5f9; border-radius: 8px; border: 1px solid #cbd5e1;")
        
        self.img_label = QLabel("No media loaded. Unlock vault above and click 'View Media'.")
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("color: #64748b; font-size: 14px;")
        
        self.img_scroll = QScrollArea()
        self.img_scroll.setWidgetResizable(True)
        self.img_scroll.setWidget(self.img_label)
        self.viewer_stack.addWidget(self.img_scroll)

        if HAS_MULTIMEDIA:
            vid_container = QWidget()
            vid_layout = QVBoxLayout(vid_container)
            vid_layout.setContentsMargins(10, 10, 10, 10)
            
            self.video_widget = QVideoWidget()
            self.media_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.media_player.setAudioOutput(self.audio_output)
            self.media_player.setVideoOutput(self.video_widget)
            
            vid_layout.addWidget(self.video_widget)
            
            # Custom Video Player Controls Bar with fully visible SVG icons
            ctrl_bar = QHBoxLayout()
            
            self.play_btn = QPushButton()
            self.play_btn.setIcon(create_svg_icon(SVG_PLAY, 18, 18))
            self.play_btn.setFixedWidth(45)
            self.play_btn.setFixedHeight(35)
            self.play_btn.clicked.connect(self.toggle_playback)
            
            self.time_lbl = QLabel("00:00 / 00:00")
            self.time_lbl.setStyleSheet("color: #334155; font-size: 12px; font-weight: bold;")
            
            self.seek_slider = QSlider(Qt.Orientation.Horizontal)
            self.seek_slider.setRange(0, 0)
            self.seek_slider.sliderPressed.connect(self.slider_pressed)
            self.seek_slider.sliderReleased.connect(self.slider_released)
            self.seek_slider.sliderMoved.connect(self.set_media_position)
            
            vol_icon_lbl = QLabel()
            vol_icon_lbl.setPixmap(create_svg_icon(SVG_VOLUME, 18, 18).pixmap(18, 18))
            
            self.volume_slider = QSlider(Qt.Orientation.Horizontal)
            self.volume_slider.setRange(0, 100)
            self.volume_slider.setValue(80)
            self.volume_slider.setFixedWidth(90)
            self.volume_slider.valueChanged.connect(self.set_media_volume)
            self.audio_output.setVolume(0.8)
            
            ctrl_bar.addWidget(self.play_btn)
            ctrl_bar.addWidget(self.time_lbl)
            ctrl_bar.addWidget(self.seek_slider)
            ctrl_bar.addWidget(vol_icon_lbl)
            ctrl_bar.addWidget(self.volume_slider)
            
            vid_layout.addLayout(ctrl_bar)
            
            self.media_player.positionChanged.connect(self.position_changed)
            self.media_player.durationChanged.connect(self.duration_changed)
            
            self.viewer_stack.addWidget(vid_container)
        else:
            fallback_lbl = QLabel("Video playback requires PyQt6-Multimedia module.")
            fallback_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.viewer_stack.addWidget(fallback_lbl)

        layout.addWidget(self.viewer_stack)
        self.decrypt_tab.setLayout(layout)

    def toggle_password_visibility(self, line_edit, state):
        if state == 2:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def toggle_encrypt_passwords(self, state):
        mode = QLineEdit.EchoMode.Normal if state == 2 else QLineEdit.EchoMode.Password
        self.enc_pass_input.setEchoMode(mode)
        self.enc_confirm_input.setEchoMode(mode)

    def browse_encrypt_file(self):
        all_exts = ALLOWED_IMAGE_EXTS + ALLOWED_VIDEO_EXTS
        filter_str = f"Media Files (*{' *'.join(all_exts)});;Images (*{' *'.join(ALLOWED_IMAGE_EXTS)});;Videos (*{' *'.join(ALLOWED_VIDEO_EXTS)})"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image or Video to Encrypt", "", filter_str)
        if file_path:
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in all_exts:
                QMessageBox.warning(self, "Invalid Format", "Only supported image and video formats are permitted.")
                return
            self.enc_file_input.setText(file_path)

    def browse_decrypt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Vault File", "", "Vault Files (*.vault);;All Files (*.*)")
        if file_path:
            self.dec_file_input.setText(file_path)
            self.meta_info_lbl.setText("Status: Vault loaded. Enter password to unlock.")
            self.view_unlocked_btn.setEnabled(False)
            self.export_unlocked_btn.setEnabled(False)

    def start_encryption(self):
        input_path = self.enc_file_input.text()
        password = self.enc_pass_input.text()
        confirm = self.enc_confirm_input.text()

        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Error", "Please select a valid image or video file.")
            return
        if not password:
            QMessageBox.warning(self, "Error", "Please enter a vault password.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Password Mismatch", "Passwords do not match. Please verify.")
            return

        default_out = input_path + ".vault"
        output_path, _ = QFileDialog.getSaveFileName(self, "Save Encrypted Vault File", default_out, "Vault Files (*.vault)")
        if not output_path:
            return

        self.enc_btn.setEnabled(False)
        self.enc_progress.setValue(0)

        self.enc_worker = EncryptionWorker(input_path, output_path, password)
        self.enc_worker.progress.connect(self.enc_progress.setValue)
        self.enc_worker.finished.connect(self.encryption_complete)
        self.enc_worker.start()

    def encryption_complete(self, success, message):
        self.enc_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", message)
            self.enc_file_input.clear()
            self.enc_pass_input.clear()
            self.enc_confirm_input.clear()
            self.enc_progress.setValue(0)
        else:
            QMessageBox.critical(self, "Encryption Error", message)

    def unlock_vault_package(self):
        input_path = self.dec_file_input.text()
        password = self.dec_pass_input.text()

        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Error", "Please select a valid .vault file.")
            return
        if not password:
            QMessageBox.warning(self, "Error", "Please enter the vault password.")
            return

        self.dec_worker = DecryptionWorker(input_path, password)
        self.dec_worker.finished.connect(self.vault_unlocked_complete)
        self.dec_worker.start()

    def vault_unlocked_complete(self, success, message, package_data):
        if not success:
            QMessageBox.critical(self, "Access Denied", message)
            self.meta_info_lbl.setText("Status: Authentication failed.")
            self.view_unlocked_btn.setEnabled(False)
            self.export_unlocked_btn.setEnabled(False)
            return

        self.unlocked_package = package_data
        filename = package_data.get("filename", "unknown")
        ext = package_data.get("extension", "").lower()

        self.meta_info_lbl.setText(f"Status: Unlocked successfully ({filename})")
        self.view_unlocked_btn.setEnabled(True)
        self.export_unlocked_btn.setEnabled(True)
        QMessageBox.information(self, "Vault Unlocked", f"Password verified! File type '{ext}' recognized. Choose 'View Media' or 'Export Original File'.")

    def show_media_in_viewer(self):
        if not hasattr(self, 'unlocked_package'):
            return

        ext = self.unlocked_package.get("extension", "").lower()
        decrypted_bytes = self.unlocked_package.get("decrypted_bytes", b"")

        if ext in ALLOWED_IMAGE_EXTS:
            qimg = QImage.fromData(decrypted_bytes)
            if qimg.isNull():
                QMessageBox.warning(self, "Error", "Failed to render image payload.")
                return
            pixmap = QPixmap.fromImage(qimg)
            self.img_label.setPixmap(pixmap)
            self.viewer_stack.setCurrentIndex(0)
        elif ext in ALLOWED_VIDEO_EXTS:
            if not HAS_MULTIMEDIA:
                QMessageBox.warning(self, "Error", "Multimedia module unavailable for video playback.")
                return
            temp_cache = os.path.join(os.path.expanduser("~"), ".vault_temp_playback" + ext)
            with open(temp_cache, 'wb') as f:
                f.write(decrypted_bytes)
            
            self.media_player.setSource(QUrl.fromLocalFile(temp_cache))
            self.media_player.play()
            self.play_btn.setIcon(create_svg_icon(SVG_PAUSE, 18, 18))
            self.viewer_stack.setCurrentIndex(1)
        else:
            QMessageBox.warning(self, "Unknown Format", f"Unsupported extension in metadata: {ext}")

    def export_decrypted_file(self):
        if not hasattr(self, 'unlocked_package'):
            return
        
        orig_name = self.unlocked_package.get("filename", "restored_media" + self.unlocked_package.get("extension", ".bin"))
        output_path, _ = QFileDialog.getSaveFileName(self, "Export Restored Media", orig_name, "All Files (*.*)")
        if not output_path:
            return

        try:
            with open(output_path, 'wb') as f:
                f.write(self.unlocked_package.get("decrypted_bytes", b""))
            QMessageBox.information(self, "Success", f"File exported successfully as '{os.path.basename(output_path)}' with original format preserved!")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def toggle_playback(self):
        if not HAS_MULTIMEDIA:
            return
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.play_btn.setIcon(create_svg_icon(SVG_PLAY, 18, 18))
        else:
            self.media_player.play()
            self.play_btn.setIcon(create_svg_icon(SVG_PAUSE, 18, 18))

    def slider_pressed(self):
        if HAS_MULTIMEDIA:
            self._is_seeking = True

    def slider_released(self):
        if HAS_MULTIMEDIA:
            self._is_seeking = False
            self.media_player.setPosition(self.seek_slider.value())

    def position_changed(self, position):
        if HAS_MULTIMEDIA and not getattr(self, '_is_seeking', False):
            self.seek_slider.setValue(position)
        self.update_time_label(position, self.media_player.duration())

    def duration_changed(self, duration):
        if HAS_MULTIMEDIA:
            self.seek_slider.setRange(0, duration)

    def set_media_position(self, position):
        if HAS_MULTIMEDIA and getattr(self, '_is_seeking', False):
            self.media_player.setPosition(position)

    def set_media_volume(self, value):
        if HAS_MULTIMEDIA:
            self.audio_output.setVolume(value / 100.0)

    def update_time_label(self, pos, duration):
        pos_time = QTime(0, 0, 0).addMSecs(pos).toString("mm:ss")
        dur_time = QTime(0, 0, 0).addMSecs(duration).toString("mm:ss")
        self.time_lbl.setText(f"{pos_time} / {dur_time}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SecureVaultWindow()
    window.show()
    sys.exit(app.exec())
