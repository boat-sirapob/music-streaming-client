from PySide6.QtWidgets import (
    QWidget, QMainWindow, QApplication,
    QHBoxLayout, QVBoxLayout, QGridLayout, QSizePolicy,
    QPushButton, QToolButton,
    QLabel)
from PySide6.QtGui import (QIcon, QCursor, QMouseEvent, QPixmap)
from PySide6.QtCore import (
    QObject, Qt, QSize, QUrl,
    QTimer, Signal, QByteArray,
    QJsonDocument, QSettings, QStandardPaths)
from PySide6.QtNetwork import (
    QNetworkCookieJar, QNetworkCookie,
    QNetworkAccessManager,
    QNetworkRequest, QNetworkReply,
    QSslConfiguration, QSsl)
from PySide6.QtMultimedia import (QMediaPlayer, QAudioOutput)
from ui.main_ui import Ui_MainWindow
import sys
from types import FunctionType

from backend.models import Playlist, Song, Category

class MainWindow(QMainWindow, Ui_MainWindow):
    SERVER_URL = "http://localhost/"
    SERVER_PORT = 8000
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        
        # switching pages
        self.home_button.clicked.connect(lambda: self.pages_widget.setCurrentWidget(self.home_page))
        self.browse_button.clicked.connect(lambda: self.pages_widget.setCurrentWidget(self.browse_page))
        self.library_button.clicked.connect(lambda: self.pages_widget.setCurrentWidget(self.library_page))
        self.profile_button.clicked.connect(lambda: self.pages_widget.setCurrentWidget(self.profile_page))
        
        self.sign_in_button.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.login_page))
        self.sign_up_button.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.register_page))
        
        # setup
        self.setup_settings()
        self.setup_networking()
        self.setup_login()
        self.setup_register()
        self.setup_home_page()
        self.setup_browse_page()
        self.setup_library_page()
        self.setup_profile_page()
        self.setup_player()
        self.setup_playlists()

    # -- networking --
    def setup_networking(self):
        self.network_manager = QNetworkAccessManager(self)
        self.ssl_config = QSslConfiguration()
        self.ssl_config.setProtocol(QSsl.SslProtocol.TlsV1_2OrLater)
        
        self.cookie_jar = QNetworkCookieJar()
        self.network_manager.setCookieJar(self.cookie_jar)
                
    def perform_get_request(self, url: str, callback: FunctionType):
        request_url = QUrl(url)
        request_url.setPort(self.SERVER_PORT)

        request = QNetworkRequest(request_url)
        request.setSslConfiguration(self.ssl_config)
        # request.setHeader(...)
        self.network_manager.finished.connect(lambda reply: self.handle_response(reply, callback))
        self.network_manager.get(request)
        
    def perform_post_request(self, url: str, data: dict, callback: FunctionType):
        request_url = QUrl(url)
        request_url.setPort(self.SERVER_PORT)

        request = QNetworkRequest(request_url)
        request.setSslConfiguration(self.ssl_config)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        # maybe? check for errors and call callback
        self.network_manager.finished.connect(lambda reply: self.handle_response(reply, callback))
        
        # self.network_manager.finished.connect(callback)
        request_body = QJsonDocument(data).toJson()
        self.network_manager.post(request, request_body)
        
    def handle_response(self, reply: QNetworkReply, callback: FunctionType):
        err = reply.error()
        if err == QNetworkReply.NetworkError.NoError:
            callback(reply)
        elif err == QNetworkReply.NetworkError.AuthenticationRequiredError:
            # todo: handle incorrect credentials
            ...
        else:
            print(f"Error: {err}")
            print(reply.errorString())
        reply.deleteLater()
        
        self.network_manager.finished.disconnect()

    # -- login --
    LOGIN_ENDPOINT = "client-login"
    def setup_login(self):
        self.login_button.clicked.connect(self.handle_login)
        self.session = None

        # if we have a saved session cookie, use it
        self.settings.beginGroup("Authentication")
        
        loaded_cookies = QNetworkCookie.parseCookies(self.settings.value("session"))
        
        self.settings.endGroup()

        if loaded_cookies:
            self.session = loaded_cookies[0]
            
            print(self.session)
            
            # todo: check if cookie is expired

            self.stackedWidget.setCurrentWidget(self.main_page)

    def handle_login(self):
        data = {
            "email": self.login_email_input.text(),
            "password": self.login_password_input.text(),
            "remember": self.remember_checkbox.isChecked()
        }
        self.perform_post_request(self.SERVER_URL + self.LOGIN_ENDPOINT, data, self.handle_login_response)
        self.login_button.setDisabled(True)
    
    def handle_login_response(self, reply: QNetworkReply):
        # response_data = reply.readAll()
        # response_json = QJsonDocument.fromJson(response_data).object()

        cookies = self.cookie_jar.allCookies()

        session_cookie = None
        for cookie in cookies:
            if cookie.name() == "session":
                session_cookie = cookie
                break

        if session_cookie:
            # authenticated successfully
            
            self.session = session_cookie
            
            # store cookie with persistence
            self.settings.beginGroup("Authentication")
            self.settings.setValue("session", cookie.toRawForm())
            self.settings.endGroup()
            
            self.stackedWidget.setCurrentWidget(self.main_page)
        else:
            # todo: incorrect credentials??
            pass
        
        self.login_email_input.clear()
        self.login_password_input.clear()
        self.remember_checkbox.setChecked(False)
        
        self.login_button.setDisabled(False)
    
    def logout(self):
        self.settings.beginGroup("Authentication")
        self.settings.setValue("session", None)
        self.settings.endGroup()
            
        self.session = None
        self.stackedWidget.setCurrentWidget(self.login_page)
    
    # -- register --
    REGISTER_ENDPOINT = "client-register"
    def setup_register(self):
        self.register_button.clicked.connect(self.handle_register)
    
    def handle_register(self):
        data = {
            "email": self.register_email_input.text(),
            "name": self.display_name_input.text(),
            "password": self.register_password_input.text(),
            "repassword": self.register_confirm_password_input.text()
        }
        self.perform_post_request(self.SERVER_URL + self.REGISTER_ENDPOINT, data, self.handle_register_response)
        # self.login_button.setDisabled(True)
    
    def handle_register_response(self, reply: QNetworkReply):
        response_data = reply.readAll()
        response_json = QJsonDocument.fromJson(response_data).object()

        print(response_json)

        if reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) == 200:
            # todo: maybe have a message that says registered successfully?
            self.stackedWidget.setCurrentWidget(self.login_page)

    # -- home page --
    def setup_home_page(self):
        self.recent_contents.setLayout(QVBoxLayout())
        self.recommend_contents.setLayout(QHBoxLayout())
        self.categories_contents.setLayout(QHBoxLayout())
        
        # -- TEST --
        playlist = Playlist("test", "test", ":resources/assets/images/1989.jpg")
        self.recent_contents.layout().addWidget(
            SmallPlaylistItem(playlist, self)
        )

        self.recommend_contents.layout().setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.recommend_contents.layout().addWidget(
            BigPlaylistItem(playlist, self)
        )
        
        self.categories = [
            Category("Pop Music",  "#87CEEB", ":resources/assets/images/pop_music.jpg"),
            Category("Rock", "#DC143C", ":resources/assets/images/rock.jpg"),
            Category("Hip Hop", "#7FFF00", ":resources/assets/images/hiphop.png"),
            Category("Jazz", "#FFC0CB", ":resources/assets/images/jazz.png"),
            Category("Country Music", "#FFA500", ":resources/assets/images/country.jpg")        
        ]
        
        self.categories_contents.layout().setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        for category in self.categories:
            self.categories_contents.layout().addWidget(
                CategoryItem(category, self)
            )

    # -- browse page --
    def setup_browse_page(self):
        self.search_button.clicked.connect(self.search)
        self.recent_searches = []
        
    def search_query(self, query):
        # todo: perform search query
        print(f"query: {query}")
        
    def search(self):
        query = self.search_bar.text()
        
        result = self.search_query(query)
        
        self.add_recent_search(query)
        
    def add_recent_search(self, query: str):
        if len(self.recent_searches) == 0:
            self.no_recent_searches_label.hide()
        
        item = RecentSearchItem(query, self)
        self.recent_searches.append(item)
        self.recent_searches_widget.layout().insertWidget(0, item)
        if len(self.recent_searches) > 5:
            self.remove_recent_search(self.recent_searches[0])
    
    def remove_recent_search(self, recent_search_item: "RecentSearchItem"):
        recent_search_item.deleteLater()
        self.recent_searches.remove(recent_search_item)
        self.recent_searches_widget.layout().removeWidget(recent_search_item)

        if len(self.recent_searches) == 0:
            self.no_recent_searches_label.show()
            
    # -- library page --
    def setup_library_page(self):
        self.library_playlists = []
        
        # self.add_playlist_button.clicked.connect()
        
        
        # --TEST--
        self.add_playlist_button.clicked.connect(lambda: self.add_playlist(Playlist("test", "test", "assets/images/1989.jpg")))

    def add_playlist(self, playlist: Playlist):
        if len(self.library_playlists) == 0:
            self.no_playlists_label.hide()
        
        # item = LibraryItem(playlist.name, playlist.image_path)
        item = SmallPlaylistItem(playlist, self)
        self.library_playlists.append(item)
        self.library_contents.layout().addWidget(item)

    # -- profile page --
    def setup_profile_page(self):
        self.settings_contents.layout().addWidget(
            ProfileItem(
                text="Languages",
                parent=self,
                on_click=lambda: self.open_settings_page(self.settings_language_page)
            )
        )
        self.settings_contents.layout().addWidget(
            ProfileItem(
                text="Theme",
                parent=self,
                on_click=lambda: self.open_settings_page(self.settings_theme_page)
            )
        )
        self.settings_contents.layout().addWidget(
            ProfileItem(
                text="Notifications",
                parent=self,
                on_click=lambda: None
            )
        ) # TODO: notifications page
        self.settings_contents.layout().addWidget(
            ProfileItem(
                text="About",
                parent=self,
                on_click=lambda: self.open_settings_page(self.settings_about_page)
            )
        )
        self.settings_contents.layout().addWidget(
            ProfileItem(
                text="Log Out",
                parent=self,
                on_click=self.logout
            )
        )

    def open_settings_page(self, page: QWidget):
        self.pages_widget.setCurrentWidget(page)
        
        back_button = QToolButton(page)
        back_button.setGeometry(10, 10, 40, 40)
        back_button.setCursor(QCursor(Qt.PointingHandCursor))
        back_button.setIcon(QIcon(":resources/assets/images/go_back.png"))
        back_button.show()

        back_button.clicked.connect(lambda: self.pages_widget.setCurrentWidget(self.profile_page))

    # -- settings
    def setup_settings(self):
        self.settings = QSettings()
        
        # todo: implement settings
    
    # -- player --
    AUDIO_ENDPOINT = "stream-audio"
    
    UPDATE_INTERVAL = 100
    def setup_player(self):
        # set up media player
        self.audio_output = QAudioOutput()
        
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)
        
        # set audio source
        self.audio_source_url = QUrl(self.SERVER_URL + self.AUDIO_ENDPOINT)
        self.audio_source_url.setPort(self.SERVER_PORT)
        self.media_player.setSource(self.audio_source_url)
        
        # player ui + logic
        self.is_playing = False
        
        self.play_pause_btn.clicked.connect(self.pause_play)
        self.previous_btn.clicked.connect(self.previous_clicked)
        self.next_btn.clicked.connect(self.next_clicked)
        
        self.player_slider.sliderPressed.connect(self.pause_play)
        self.player_slider.sliderMoved.connect(self.set_player_position)
        self.player_slider.sliderReleased.connect(self.pause_play)
        
        self.timer = QTimer(self)
        self.timer.setInterval(self.UPDATE_INTERVAL)
        self.timer.timeout.connect(self.update_player)
        
    def pause_play(self):
        if self.is_playing:
            self.media_player.pause()
            self.timer.stop()
        else:
            self.media_player.play()
            self.timer.start()
            
        self.is_playing = not self.is_playing

    def previous_clicked(self):
        # before this threshold, go to previous track
        # otherwise, seek to beginning
        PREVIOUS_THRESHOLD = 5000
    
        if self.media_player.position() <= PREVIOUS_THRESHOLD:
            # todo: go to previous track
            ...
        else:
            self.media_player.setPosition(0)
    
    def next_clicked(self):
        # todo: go to next track
        ...

    def set_player_position(self, position):
        # fixme: get duration from song
        # duration = self.media_player.duration()
        
        duration = 77035 # TEMP FOR TESTING
        
        player_position = duration * (position / 100)
        print(player_position)
        self.media_player.setPosition(int(player_position))

    def update_player(self):
        duration = 77035 # TEMP FOR TESTING
        
        print(self.media_player.bufferProgress())
        print(self.media_player.mediaStatus())
        
        player_pos = (self.media_player.position() / duration) * 100

        self.player_slider.setSliderPosition(player_pos)

        print(self.media_player.position())

        self.play_pause_btn.setChecked(self.media_player.isPlaying())
        if not self.media_player.isPlaying():
            self.timer.stop()
            self.is_playing = False

    # -- handling playlists --
    def setup_playlists(self):
        self.cur_playlist: Playlist = None
        self.song_items: list[SongItem] = []
        self.playlist_image_label = QLabel()
        self.playlist_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.playlist_image_widget.layout().addWidget(self.playlist_image_label)
        
        # todo: shuffle current playlist
        # self.playlist_shuffle_button.clicked.connect(...)

        # todo: play current playlist
        # self.playlist_play_button.clicked.connect(...)
    
    def open_playlist(self, playlist: Playlist):
        for song_item in self.song_items:
            song_item.deleteLater()
            self.song_items.remove(song_item)
            self.playlist_contents.layout().removeWidget(song_item)

        self.playlist_no_songs_label.show()

        self.cur_playlist = playlist
        
        self.pages_widget.setCurrentIndex(4)

        self.playlist_name_label.setText(playlist.name)
        
        if playlist.image_path:
            pixmap = QPixmap(playlist.image_path).scaled(120, 120)
            self.playlist_image_label.setPixmap(pixmap)
        else:
            # todo: placeholder image for if there is no image
            ...
        
        self.add_playlist_item(Song("test title", "test artist", playlist, 123))
        
    def add_playlist_item(self, song: Song):
        if self.cur_playlist and len(self.cur_playlist.songs) == 0:
            self.playlist_no_songs_label.hide()
        
        item = SongItem(song.title, song.artist, song.playlist.image_path, song.duration)
        self.song_items.append(item)
        self.playlist_contents.layout().addWidget(item)

# -- components --
class SmallThumbnailItem(QPushButton):
    def __init__(self, text: str, image_path: str, parent=None):
        super().__init__(parent)

        # self.setObjectName("recent_playlist")
        self.setMinimumSize(QSize(250, 64))
        self.setText("  " + text)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setAutoFillBackground(False)

        icon = QIcon()
        icon.addFile(image_path, QSize(), QIcon.Normal, QIcon.Off)
        self.setIcon(icon)
        self.setIconSize(QSize(64, 64))

        self.setProperty("class", "SmallThumbnailItem")
        self.setStyleSheet("""
            .SmallThumbnailItem {
                background-color: #1e1e1e;
                font-size: 16px;
                padding: 0px;
                text-align: left;
                color: #dddddd;
                border-radius: 5px;
            }
        
            .SmallThumbnailItem:hover {
                color: #ffffff;
                background-color: #303030;
            }
        """)

class BigThumbnailItem(QPushButton):
    def __init__(self, heading="No Title", subheading="", image_path="", parent=None):
        super().__init__(parent)

        self.setFixedSize(QSize(140, 180))
        self.setCursor(Qt.PointingHandCursor)
        self.setAutoFillBackground(False)

        icon_label = QLabel(self)
        icon_label.setFixedSize(120, 120)
        icon_label.setAlignment(Qt.AlignCenter)
        if image_path:
            pixmap = QPixmap(image_path).scaled(120, 120)
            icon_label.setPixmap(pixmap)

        heading_label = QLabel(self)
        heading_label.setText(heading)
        heading_label.setAlignment(Qt.AlignLeft)
        heading_label.setStyleSheet("color: #ffffff; font-size: 14px; background-color: transparent;")

        subheading_label = QLabel(self)
        subheading_label.setText(subheading)
        subheading_label.setAlignment(Qt.AlignLeft)
        subheading_label.setStyleSheet("color: #cccccc; font-size: 12px; background-color: transparent;")
        
        layout = QVBoxLayout(self)
        layout.addWidget(icon_label)
        layout.addWidget(heading_label)
        if subheading:
            layout.addWidget(subheading_label)
        self.setLayout(layout)
        
        self.setProperty("class", "BigThumbnailItem")
        self.setStyleSheet("""
            .BigThumbnailItem {
                background-color: #1e1e1e;
                font-size: 14px;
                padding: 0px;
                text-align: center;
                border-radius: 5px;
            }
            .BigThumbnailItem:hover {
                color: #ffffff;
                background-color: #303030;
            }
        """)

class LongLabelButton(QWidget):
    def __init__(self, text: str, parent: MainWindow = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(40)

        self.main_window = parent

        self.label = QPushButton(text)
        self.label.setMinimumHeight(35)
        self.label.setCursor(QCursor(Qt.PointingHandCursor))

        self.tool_button = QToolButton(self)
        self.tool_button.setCursor(QCursor(Qt.PointingHandCursor))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.label)
        layout.addWidget(self.tool_button)
        
        self.setLayout(layout)
        
        self.setProperty("class", "LongLabelButton")
        self.setStyleSheet("""
            .LongLabelButton QPushButton {
                text-align: left;
                border: 0;
            }
        """)

class SmallPlaylistItem(SmallThumbnailItem):
    def __init__(self, playlist: Playlist, parent: MainWindow = None):
        super().__init__(playlist.name, playlist.image_path, parent)
        
        self.playlist = playlist
        self.main_window = parent
        
        self.clicked.connect(self.show_playlist)

    def show_playlist(self):
        self.main_window.open_playlist(self.playlist)

class BigPlaylistItem(BigThumbnailItem):
    def __init__(self, playlist: Playlist, parent: MainWindow = None):
        super().__init__(playlist.name, playlist.artist, playlist.image_path, parent)
        
        self.playlist = playlist
        self.main_window = parent
        
        self.clicked.connect(self.show_playlist)

    def show_playlist(self):
        self.main_window.open_playlist(self.playlist)

class CategoryItem(QPushButton):
    def __init__(self, category: Category, parent: QWidget = None):
        super().__init__(parent)
        
        self.setFixedSize(QSize(140, 180))
        self.setCursor(Qt.PointingHandCursor)
        self.setAutoFillBackground(False)

        icon_label = QLabel(self)
        icon_label.setFixedSize(120, 120)
        icon_label.setAlignment(Qt.AlignCenter)
        if category.image_path:
            pixmap = QPixmap(category.image_path).scaled(120, 120)
            icon_label.setPixmap(pixmap)

        heading_label = QLabel(self)
        heading_label.setText(category.name)
        heading_label.setAlignment(Qt.AlignLeft)
        heading_label.setStyleSheet(f"color: {category.color}; font-size: 14px; background-color: transparent;")

        # subheading_label = QLabel(self)
        # subheading_label.setAlignment(Qt.AlignLeft)
        # subheading_label.setStyleSheet("color: #cccccc; font-size: 12px; background-color: transparent;")
        
        layout = QVBoxLayout(self)
        layout.addWidget(icon_label)
        layout.addWidget(heading_label)
        self.setLayout(layout)
        
        self.setProperty("class", "CategoryItem")
        self.setStyleSheet("""
            .CategoryItem {
                background-color: #1e1e1e;
                font-size: 14px;
                padding: 0px;
                text-align: center;
                border-radius: 5px;
            }
            .CategoryItem:hover {
                color: #ffffff;
                background-color: #303030;
            }
        """)

# -- browse page --
class RecentSearchItem(LongLabelButton):
    def __init__(self, text: str, parent: MainWindow = None) -> None:
        super().__init__(text, parent)
        
        self.label.clicked.connect(lambda: parent.search_query(text))
        
        self.tool_button.setIcon(QIcon(":/resources/assets/images/cancel.png"))
        self.tool_button.clicked.connect(lambda: parent.remove_recent_search(self))

# -- library page --
class LibraryItem(SmallThumbnailItem):
    def __init__(self, text: str, image_path: str, parent=None):
        super().__init__(text, image_path, parent)
        
# -- profile page --
class ProfileItem(LongLabelButton):
    def __init__(self, text: str, on_click: FunctionType, parent: MainWindow = None) -> None:
        super().__init__(text, parent)
        
        self.tool_button.setIcon(QIcon(":/resources/assets/images/enter.png"))
        
        self.label.clicked.connect(on_click)
        self.tool_button.clicked.connect(on_click)

# -- playlists page --
class SongItem(QWidget):
    def __init__(self, heading: str, subheading: str, image_path: str, duration: float, parent: QWidget = None) -> None:
        super().__init__(parent)
        
        icon_label = QLabel(self)
        icon_label.setFixedSize(60, 60)
        icon_label.setAlignment(Qt.AlignCenter)
        if image_path:
            pixmap = QPixmap(image_path).scaled(60, 60)
            icon_label.setPixmap(pixmap)
        
        labels_widget = QWidget(self)
        labels_widget.setLayout(QVBoxLayout())

        heading_label = QLabel(self)
        heading_label.setText(heading)
        heading_label.setAlignment(Qt.AlignLeft)
        heading_label.setStyleSheet("color: #ffffff; font-size: 14px; background-color: transparent;")

        subheading_label = QLabel(self)
        subheading_label.setText(subheading)
        subheading_label.setAlignment(Qt.AlignLeft)
        subheading_label.setStyleSheet("color: #cccccc; font-size: 12px; background-color: transparent;")
        
        labels_widget.layout().addWidget(heading_label)
        labels_widget.layout().addWidget(subheading_label)
        
        duration_label = QLabel(self)
        duration_label.setText(to_time(duration))
        
        play_button = QToolButton(self)
        play_button.setIcon(QIcon(":/resources/assets/images/play.png"))
        # todo: set current song to clicked song
        # play_button.clicked.connect(...)
        
        layout = QHBoxLayout(self)
        layout.addWidget(icon_label)
        layout.addWidget(labels_widget)
        layout.addWidget(duration_label)
        layout.addWidget(play_button)
        self.setLayout(layout)
        
        self.setProperty("class", "PlaylistItem")
        self.setStyleSheet("""
            .PlaylistItem {
                background-color: #1e1e1e;
                font-size: 14px;
                padding: 0px;
                text-align: center;
                border-radius: 5px;
            }
        """)

# -- utility --
def to_time(duration: float):
    minutes = duration // 60
    seconds = duration % 60
    return f"{minutes:01}:{seconds:02}"

def run():
    app = QApplication(sys.argv)
    app.setOrganizationName("KMITL")
    app.setApplicationName("Music Streaming Client")

    window = MainWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    run()