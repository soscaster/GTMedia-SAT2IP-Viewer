import ctypes
import os
import sys
import vlc
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import requests
import json
import pyperclip
from pypresence import Presence
import time

discord_id = "1269853518005665845"
RPC = Presence(discord_id)
RPC.connect()

myappid = u'emina-media.gtmedia.sat2ip' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("GTmedia SAT2IP Services")
        self.setWindowIcon(QIcon(resource_path("favicon.ico")))
        self.setGeometry(0, 0, 1300, 500)
        
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)
        
        self.ip_label = QLabel("Enter IP Address:", self)
        self.layout.addWidget(self.ip_label)
        
        self.ip_frame = QHBoxLayout()
        self.layout.addLayout(self.ip_frame)
        
        self.ip_entry1 = QLineEdit(self)
        self.ip_entry1.setMaxLength(3)
        self.ip_entry1.setText('192')
        self.ip_frame.addWidget(self.ip_entry1)
        
        self.ip_frame.addWidget(QLabel(".", self))
        
        self.ip_entry2 = QLineEdit(self)
        self.ip_entry2.setMaxLength(3)
        self.ip_entry2.setText('168')
        self.ip_frame.addWidget(self.ip_entry2)
        
        self.ip_frame.addWidget(QLabel(".", self))
        
        self.ip_entry3 = QLineEdit(self)
        self.ip_entry3.setMaxLength(3)
        self.ip_frame.addWidget(self.ip_entry3)
        
        self.ip_frame.addWidget(QLabel(".", self))
        
        self.ip_entry4 = QLineEdit(self)
        self.ip_entry4.setMaxLength(3)
        self.ip_frame.addWidget(self.ip_entry4)
        
        self.get_button = QPushButton("Get Services", self)
        self.get_button.clicked.connect(self.get_services)
        self.layout.addWidget(self.get_button)
        
        self.main_frame = QHBoxLayout()
        self.layout.addLayout(self.main_frame)
        
        self.services_frame = QVBoxLayout()
        self.main_frame.addLayout(self.services_frame)
        
        self.services_list = QListWidget(self)
        self.services_list.setMaximumWidth(200)
        self.services_list.setFont(QFont("Arial", 12))
        self.services_list.itemClicked.connect(self.on_service_selected)
        self.services_list.itemDoubleClicked.connect(self.on_service_double_clicked)
        self.services_frame.addWidget(self.services_list)

        self.description_frame = QVBoxLayout()
        self.main_frame.addLayout(self.description_frame)

        self.audio_tracks_combobox = QComboBox(self)
        self.audio_tracks_combobox.setEnabled(False)
        self.audio_tracks_combobox.addItem("Select Audio Track")
        self.audio_tracks_combobox.currentIndexChanged.connect(self.change_audio_track)
        self.description_frame.addWidget(self.audio_tracks_combobox)

        self.copy_button = QPushButton("Copy URL", self)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(lambda: self.copy_to_clipboard(self.get_corrected_url(self.services_list.currentItem().data(Qt.UserRole)['url'], self.current_audio_pid)))
        self.description_frame.addWidget(self.copy_button)

        self.fullscreen_button = QPushButton("Fullscreen", self)
        self.fullscreen_button.setEnabled(False)
        self.fullscreen_button.clicked.connect(self.on_fullscreen_button_clicked)
        self.description_frame.addWidget(self.fullscreen_button)
        
        self.info_labels = {}
        for info in ["Service Name", "Satellite Name", "Frequency", "PID", "Signal Intensity", "Signal Quality", "Receive Rate", "Send Rate"]:
            label = QLabel(info + ":", self)
            self.description_frame.addWidget(label)
            value_label = QLabel("", self)
            value_label.setStyleSheet("background-color: white;")
            value_label.setFont(QFont("Arial", 12))
            self.description_frame.addWidget(value_label)
            self.info_labels[info] = value_label
        
        self.player_frame = QFrame(self)
        self.player_frame.setMinimumSize(800, 500)
        self.player_frame.setStyleSheet("background-color: black;")
        self.main_frame.addWidget(self.player_frame)
        
        self.vlc_instance = vlc.Instance("--verbose 0")
        self.vlc_player = self.vlc_instance.media_player_new()
        if sys.platform.startswith('linux'):
            self.vlc_player.set_xwindow(self.player_frame.winId())
        elif sys.platform == "win32":
            self.vlc_player.set_hwnd(self.player_frame.winId())
        
        self.current_audio_pid = None

        self.media_event_manager = self.vlc_player.event_manager()
        self.media_event_manager.event_attach(vlc.EventType.MediaPlayerMediaChanged, self.on_media_changed)
        
        self.show()
        RPC.update(state="Not running any service", details="Idle", large_image="general")

    def validate_ip(self, text):
        return text.isdigit() and 0 <= int(text) <= 255

    def get_ip_address(self):
        ip_parts = [self.ip_entry1.text(), self.ip_entry2.text(), self.ip_entry3.text(), self.ip_entry4.text()]
        if all(self.validate_ip(part) for part in ip_parts):
            return ".".join(ip_parts)
        return None

    def get_services(self):
        ip_address = self.get_ip_address()
        if not ip_address:
            QMessageBox.critical(self, "Error", "Please enter a valid IP address.")
            return

        count = 100
        data = None

        while True:
            full_url = f"http://{ip_address}:81/getallservices?count={count}"
            try:
                print(full_url)
                response = requests.get(full_url)
                response.raise_for_status()
                data = response.json()
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                QMessageBox.critical(self, "Error", f"Failed to fetch services: {e}")
                return

            if "pagetotal" not in data or "services" not in data:
                QMessageBox.critical(self, "Error", "Invalid response format.")
                return

            if data["pagetotal"] <= 1:
                break
            count += 100

        self.display_services(data["services"])

    def display_services(self, services):
        self.services_list.clear()
        for service in services:
            item = QListWidgetItem(service["servicename"])
            item.setData(Qt.UserRole, service)
            if service["servicename"].startswith('$'):
                item.setForeground(Qt.red)
            self.services_list.addItem(item)

    def on_service_selected(self, item):
        service = item.data(Qt.UserRole)
        ip_address = self.get_ip_address()
        if not ip_address:
            QMessageBox.critical(self, "Error", "Please enter a valid IP address.")
            return

        url = f"http://{ip_address}:81/proginfo?id={service['id']}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch service info: {e}")
            return

        required_keys = {"servicename", "satname", "FQ", "PID", "intensity", "quality", "rev_rate", "send_rate"}
        if not all(key in data for key in required_keys):
            QMessageBox.critical(self, "Error", "Invalid response format.")
            return

        service_info = {
            "Service Name": data['servicename'],
            "Satellite Name": data['satname'],
            "Frequency": str(data['FQ']),
            "PID": str(data['PID']),
            "Signal Intensity": str(data['intensity']),
            "Signal Quality": str(data['quality']),
            "Receive Rate": str(data['rev_rate']),
            "Send Rate": str(data['send_rate'])
        }

        for key, value in service_info.items():
            self.info_labels[key].setText(value)

        # Extract the correct audio PID
        self.current_audio_pid = data['PID'].split('/')[1]

        self.audio_tracks_combobox.setEnabled(True)
        self.copy_button.setEnabled(True)
        self.fullscreen_button.setEnabled(True)

    def on_service_double_clicked(self, item):
        service = item.data(Qt.UserRole)
        corrected_url = self.get_corrected_url(service['url'], self.current_audio_pid)
        self.play_stream(corrected_url)

        # Fetch additional details from the proginfo endpoint
        ip_address = self.get_ip_address()
        if not ip_address:
            QMessageBox.critical(self, "Error", "Please enter a valid IP address.")
            return

        url = f"http://{ip_address}:81/proginfo?id={service['id']}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch service info: {e}")
            return

        required_keys = {"FQ"}
        if not all(key in data for key in required_keys):
            QMessageBox.critical(self, "Error", "Invalid response format from proginfo.")
            return

        fq = data.get('FQ', 'Unknown Frequency')
        service_name = data.get('servicename', 'Unknown Service')

        if service['servicename'].startswith('$'):
            RPC.update(state=f"Scrambled - {fq}", details=f'{service_name}', large_text="Running service:", large_image="scramble", start=int(time.time()), buttons=[{"label": fq, "url": f"https://landing.quangminh.name.vn"}])
        else:
            RPC.update(state=f"FTA - {fq}", details=f'{service_name}', large_text="Running service:", large_image="fta", start=int(time.time()), buttons=[{"label": fq, "url": f"https://landing.quangminh.name.vn"}])

    def set_deinterlace_mode(self, mode):
        self.vlc_player.video_set_deinterlace(mode.encode('utf-8'))

    def play_stream(self, url):
        media = self.vlc_instance.media_new(url)
        self.vlc_player.set_media(media)
        self.set_deinterlace_mode('linear')
        self.vlc_player.play()

    def get_corrected_url(self, url, correct_audio_pid):
        parts = url.split('_')
        parts[-4] = correct_audio_pid
        return '_'.join(parts)

    def populate_audio_tracks(self):
        self.audio_tracks_combobox.clear()
        track_count = self.vlc_player.audio_get_track_count()
        print("Track count:", track_count)
        if track_count > 0:
            tracks = self.vlc_player.audio_get_track_description()
            for track in tracks:
                track_id, track_description = track
                # Decode the description if it's in bytes
                if isinstance(track_description, bytes):
                    track_description = track_description.decode('utf-8')
                self.audio_tracks_combobox.addItem(track_description, track_id)
        else:
            print("No audio tracks found. Refreshing...")
            self.audio_tracks_combobox.addItem("Refreshing...")
            # Wait 2 seconds before refreshing
            QTimer.singleShot(2000, self.populate_audio_tracks)

    def change_audio_track(self, index):
        if index == 0:
            return
        track_id = self.audio_tracks_combobox.itemData(index)
        if track_id is not None:
            print(f"Changing to track ID: {track_id}")
            self.vlc_player.audio_set_track(track_id)
        else:
            print("Invalid track ID")

    def on_media_changed(self, event):
        QTimer.singleShot(1, self.populate_audio_tracks)

    def on_fullscreen_button_clicked(self):
        item = self.services_list.currentItem()
        if not item:
            return
        service = item.data(Qt.UserRole)
        corrected_url = self.get_corrected_url(service['url'], self.current_audio_pid)
        audio_track = self.audio_tracks_combobox.currentIndex()
        self.vlc_player.stop()
        self.fullscreen_player = FullscreenVideoWindow(corrected_url, audio_track)

    def copy_to_clipboard(self, url):
        pyperclip.copy(url)
        QMessageBox.information(self, "Copied", f"URL copied to clipboard:\n{url}")

    def closeEvent(self, event):
        if QMessageBox.question(self, "Quit", "Do you want to quit?") == QMessageBox.Yes:
            QMessageBox.information(self, "Goodbye", "Thank you for using this app!\nWritten by: soscaster")
            event.accept()
        else:
            event.ignore()

class FullscreenVideoWindow(QMainWindow):
    def __init__(self, url, audio_track):
        super(FullscreenVideoWindow, self).__init__()
        self.setWindowTitle("Fullscreen Video Player")
        # self.setGeometry(0, 0, 800, 600)
        self.setWindowState(Qt.WindowFullScreen)
        self.setWindowIcon(QIcon(resource_path("favicon.ico")))

        self.vlc_instance = vlc.Instance("--verbose 0")
        self.vlc_player = self.vlc_instance.media_player_new()
        if sys.platform.startswith('linux'):
            self.vlc_player.set_xwindow(self.winId())
        elif sys.platform == "win32":
            self.vlc_player.set_hwnd(self.winId())
        
        self.play_stream(url, audio_track)
        self.show()

    def set_deinterlace_mode(self, mode):
        self.vlc_player.video_set_deinterlace(mode.encode('utf-8'))

    def populate_audio_tracks(self, audio_track):
        track_count = self.vlc_player.audio_get_track_count()
        print("Track count:", track_count)
        if track_count > 0:
            self.vlc_player.audio_set_track(audio_track)
        else:
            print("No audio tracks found. Refreshing...")
            # Wait 2 seconds before refreshing
            QTimer.singleShot(2000, self.populate_audio_tracks(audio_track))

    def play_stream(self, url, audio_track):
        media = self.vlc_instance.media_new(url)
        self.vlc_player.set_media(media)
        self.set_deinterlace_mode('linear')
        print(f"Playing URL: {url}")
        self.vlc_player.play()
        print("Populating audio tracks with:", audio_track)
        # self.populate_audio_tracks(audio_track)
        
    def closeEvent(self, event):
        self.vlc_player.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
