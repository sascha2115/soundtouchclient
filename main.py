from bosesoundtouchapi.models.contentitem import ContentItem
import flet as ft
import json
import requests
import asyncio
import xml.etree.ElementTree as ET
import pprint
from bosesoundtouchapi import SoundTouchClient, SoundTouchDevice, SoundTouchDiscovery
from pathlib import Path
from filebrowser import create_filebrowser

# Configuration
SOURCE = "STORED_MUSIC"


class BoseSoundTouchController:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Bose SoundTouch Controller"
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.page.window_width = 400
        self.page.window_height = 700
        self.page.padding = 20

        self.device = None
        self.client = None
        self.ipaddr = ""
        self.config_file = Path.home() / ".bose_soundtouch_config.json"
        self.accountid = ""
        self.last_path = []

        # --------------------------------------------------------------------------------
        # Flet UI components
        # --------------------------------------------------------------------------------

        # Track info
        self.track_label = ft.Text(
            "",
            size=20,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        )
        # Artist and Album info
        self.artist_album_label = ft.Text(
            "Loading...",
            size=14,
            color=ft.Colors.GREY_500,
            text_align=ft.TextAlign.CENTER,
        )
        # Track number info
        self.track_number_label = ft.Text(
            "Track",
            size=12,
            color=ft.Colors.GREY_600,
            text_align=ft.TextAlign.CENTER,
        )

        # Progress bar + time labels
        self.position_label = ft.Text("0:00", size=12, color=ft.Colors.GREY_600)
        self.duration_label = ft.Text("--:--", size=12, color=ft.Colors.GREY_600)
        self.progress_bar = ft.ProgressBar(value=0.0, width=280, bar_height=6)

        progress_section = ft.Row(
            [self.position_label, self.progress_bar, self.duration_label],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

        # Colors for buttons
        button_style = ft.ButtonStyle(
            bgcolor=ft.Colors.GREY_800,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=12),
            icon_color=ft.Colors.WHITE,
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
        )

        # Buttons
        self.prev_btn = ft.IconButton(
            icon=ft.Icons.SKIP_PREVIOUS,
            on_click=self.previous_track,
            disabled=True,
            style=button_style,
            icon_size=40,
        )
        self.play_pause_btn = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.toggle_play_pause,
            disabled=True,
            style=button_style,
            icon_size=60,
        )
        self.next_btn = ft.IconButton(
            icon=ft.Icons.SKIP_NEXT,
            on_click=self.next_track,
            disabled=True,
            style=button_style,
            icon_size=40,
        )
        self.shuffle_btn = ft.TextButton(
            text="Shuffle",
            on_click=self.toggle_shuffle,
            disabled=True,
            style=button_style,
        )
        # NEW: Repeat button
        self.repeat_btn = ft.TextButton(
            text="Repeat",
            on_click=self.toggle_repeat,
            disabled=True,
            style=button_style,
        )

        controls_section = ft.Column(
            [
                ft.Row(
                    [self.prev_btn, self.play_pause_btn, self.next_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
                ft.Row(
                    [self.shuffle_btn, self.repeat_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15,
        )

        # Volume info and slider
        self.volume_label = ft.Text(
            "Volume: 0", size=14, text_align=ft.TextAlign.CENTER
        )
        self.volume_slider = ft.Slider(
            min=0,
            max=100,
            value=50,
            disabled=True,
            on_change=self.change_volume,
            width=200,
        )
        self.vol_down_btn = ft.IconButton(
            icon=ft.Icons.REMOVE,
            on_click=self.volume_down,
            style=button_style,
            disabled=True,
            icon_size=20,
        )
        self.vol_up_btn = ft.IconButton(
            icon=ft.Icons.ADD,
            on_click=self.volume_up,
            style=button_style,
            disabled=True,
            icon_size=20,
        )

        volume_section = ft.Column(
            [
                self.volume_label,
                ft.Row(
                    [self.vol_down_btn, self.volume_slider, self.vol_up_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=0,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        )

        # Preset buttons
        self.preset_buttons = []
        for i in range(1, 7):
            btn = ft.ElevatedButton(
                f"{i}",
                on_click=lambda e, n=i: self.select_preset(n),
                disabled=True,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.GREY_800,
                    color=ft.Colors.WHITE,
                    padding=ft.padding.symmetric(horizontal=27, vertical=17),
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
            )
            btn.content = ft.Text(f"{i}", size=16)
            self.preset_buttons.append(btn)

        presets_row1 = ft.Row(
            self.preset_buttons[0:3],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )
        presets_row2 = ft.Row(
            self.preset_buttons[3:6],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )

        presets_section = ft.Column(
            [presets_row1, presets_row2],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Button for file browser
        self.open_filebrowser_btn = ft.ElevatedButton(
            "Media Browser",
            on_click=lambda e: self.show_filebrowser(),
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.GREY_800,
                color=ft.Colors.WHITE,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )

        # File browser overlay (hidden by default)
        self.filebrowser_overlay = ft.Container(
            bgcolor=ft.Colors.BLACK,
            border=ft.border.all(1, ft.Colors.GREY_700),
            width=self.page.window_width,
            height=int(self.page.window_height * 0.75),
            expand=True,
            top=0,
            left=0,
            right=0,
            bottom=0,
            visible=False,
        )

        # Status label
        self.status_label = ft.Text(
            "Connecting...", text_align=ft.TextAlign.CENTER, color=ft.Colors.GREY_600
        )

        # Main UI layout
        self.main_ui = ft.Column(
            [
                self.track_label,
                self.artist_album_label,
                self.track_number_label,
                progress_section,
                controls_section,
                volume_section,
                presets_section,
                self.open_filebrowser_btn,
                ft.Divider(),
                self.status_label,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15,
            expand=True,
        )

        # Add both main UI and overlay to page
        self.stack_layout = ft.Stack(
            controls=[
                self.main_ui,
                self.filebrowser_overlay,
            ],
            expand=True,  # Make the stack expand to fill the page
        )
        self.page.add(self.stack_layout)

        # --------------------------------------------------------------------------------
        # Main initialization
        # --------------------------------------------------------------------------------

        # Load saved config and try to auto-connect
        saved = self.load_config()
        if saved and saved.get("last_ip"):
            print("Found last saved IP address")
            self.auto_connect_saved(saved)
        else:
            self.discover_devices()
        self.page.update()
        self.page.on_keyboard_event = self.handle_key_event

    # --------------------------------------------------------------------------------
    # Backend methods
    # --------------------------------------------------------------------------------

    # Load config from file
    def load_config(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
        return {}

    # Save config to file
    def save_config(self, ipaddr, name):
        try:
            config = {"last_ip": ipaddr, "last_name": name}
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    # Connect to last known device
    def auto_connect_saved(self, cfg):
        ipaddr = cfg.get("last_ip")
        if ipaddr:
            self.ipaddr = ipaddr
        name = cfg.get("last_name", "Saved Device")
        self.status_label.value = "Connecting to device..."
        self.page.update()
        try:
            self.connect_to_device(ipaddr, name)
        except Exception as e:
            print(f"Auto-connect failed: {e}")
            self.discover_devices()

    # Discover devices
    def discover_devices(self):
        print("Trying to discover devices...")
        self.status_label.value = "Searching for devices..."
        self.page.update()
        try:
            discovery = SoundTouchDiscovery(True, printToConsole=True)
            devices = discovery.DiscoverDevices(timeout=5)
            if devices:
                print("Devices found.")
                sockaddr = list(devices)
                ipaddr = sockaddr.split(":")
                print("IP-Address:", ipaddr)
                self.ipaddr = ipaddr
                self.connect_to_device(ipaddr)
            else:
                print("No devices found.")
                self.status_label.value = "No devices found."
        except Exception as e:
            print(f"Discovery error: {e}")
            self.status_label.value = "Device discovery error."
            self.page.update()

    # Connect device
    def connect_to_device(self, ipaddr, name=None):
        print("Connecting to device...")
        try:
            requests.get(f"http://{ipaddr}:8090/info", timeout=5)
            print("Connected to:", ipaddr)
        except requests.RequestException:
            print("Connection error: IP request failed.")
            raise ValueError("Connection failed")
            return

        try:
            self.device = SoundTouchDevice(ipaddr)
            pprint.pprint(self.device)
            self.client = SoundTouchClient(self.device)
            if not name:
                info = self.client.GetInformation()
                name = info.DeviceName
            self.save_config(ipaddr, name)
            self.status_label.value = f"Connected: {name} ({ipaddr})"
            self.enable_controls(True)
            self.update_status()
        except Exception as e:
            self.status_label.value = f"Connection failed: {e}"
            self.enable_controls(False)
        self.page.update()

    # Enable GUI controls
    def enable_controls(self, enabled):
        for btn in [
            self.prev_btn,
            self.play_pause_btn,
            self.next_btn,
            self.shuffle_btn,
            self.repeat_btn,
        ]:
            btn.disabled = not enabled
        self.volume_slider.disabled = not enabled
        self.vol_down_btn.disabled = not enabled
        self.vol_up_btn.disabled = not enabled
        for b in self.preset_buttons:
            b.disabled = not enabled
        self.open_filebrowser_btn.disabled = not enabled
        self.page.update()

    # --------------------------------------------------------------------------------
    # Methods for GUI controls
    # --------------------------------------------------------------------------------

    # Play/pause
    def toggle_play_pause(self, e):
        if not self.client:
            return
        try:
            np = self.client.GetNowPlayingStatus(True)
            if np.PlayStatus == "PLAY_STATE":
                self.client.MediaPause()
            else:
                self.client.MediaPlay()
            self.update_status()
        except Exception as ex:
            print(f"Error toggling play/pause: {ex}")

    # Previous track
    def previous_track(self, e):
        if not self.client:
            return
        try:
            np = self.client.GetNowPlayingStatus(True)
            if np.IsSkipPreviousEnabled:
                self.client.MediaPreviousTrack()
            self.update_status()
        except Exception as ex:
            print(f"Error: {ex}")

    # Next track
    def next_track(self, e):
        if not self.client:
            return
        try:
            np = self.client.GetNowPlayingStatus(True)
            if np.IsSkipEnabled:
                self.client.MediaNextTrack()
            self.update_status()
        except Exception as ex:
            print(f"Error: {ex}")

    # Volume
    def change_volume(self, e):
        if not self.client:
            return
        try:
            val = int(self.volume_slider.value)
            self.client.SetVolumeLevel(val)
            self.volume_label.value = f"Volume: {val}"
            self.page.update()
        except Exception as ex:
            print(f"Error changing volume: {ex}")

    def volume_up(self, e):
        if self.client:
            try:
                self.client.VolumeUp()
                self.update_status()
            except Exception as ex:
                print(f"Error increasing volume: {ex}")

    def volume_down(self, e):
        if self.client:
            try:
                self.client.VolumeDown()
                self.update_status()
            except Exception as ex:
                print(f"Error decreasing volume: {ex}")

    # Shuffle
    def toggle_shuffle(self, e):
        if not self.client:
            return
        try:
            np = self.client.GetNowPlayingStatus(True)
            if np.IsShuffleEnabled:
                self.client.MediaShuffleOff()
            else:
                self.client.MediaShuffleOn()
            self.update_status()
        except Exception as ex:
            print(f"Error toggling shuffle: {ex}")

    # NEW: Repeat mode toggle
    def toggle_repeat(self, e):
        if not self.client:
            return
        try:
            np = self.client.GetNowPlayingStatus(True)
            current_repeat = getattr(np, "RepeatSetting", "REPEAT_OFF")

            # Cycle through: OFF -> ON -> ONE -> OFF
            if current_repeat == "REPEAT_OFF":
                self.client.MediaRepeatAll()
            elif current_repeat == "REPEAT_ALL":
                self.client.MediaRepeatOne()
            else:
                self.client.MediaRepeatOff()

            self.update_status()
        except Exception as ex:
            print(f"Error toggling repeat: {ex}")

    # Presets
    def select_preset(self, number):
        if not self.client:
            return
        try:
            if number == 1:
                self.client.SelectPreset1()
            elif number == 2:
                self.client.SelectPreset2()
            elif number == 3:
                self.client.SelectPreset3()
            elif number == 4:
                self.client.SelectPreset4()
            elif number == 5:
                self.client.SelectPreset5()
            elif number == 6:
                self.client.SelectPreset6()
            self.status_label.value = f"Preset {number} activated"
            self.page.update()
        except Exception as e:
            print(f"Error selecting preset {number}: {e}")

    # File browser
    def show_filebrowser(self):
        self.filebrowser_overlay.content = create_filebrowser(
            self.client,
            self.accountid,
            self.last_path,
            self.hide_filebrowser,
            self.page,
        )
        self.filebrowser_overlay.visible = True
        self.page.update()

    def hide_filebrowser(self, e, new_path=None):
        if new_path is not None:
            self.last_path = new_path
        self.filebrowser_overlay.visible = False
        self.page.update()

    # Determine track number
    def update_track_number(self):
        try:
            url = "http://" + self.ipaddr + ":8090/now_playing"
            response = requests.get(url)
            xmlroot = ET.fromstring(response.text)
            offset = xmlroot.findtext("offset")
            if offset:
                offset = int(offset) + 1
                self.track_number_label.value = f"Track: {offset}"
            else:
                self.track_number_label.value = ""
        except Exception as e:
            print(f"Error determining track number: {e}")
            self.track_number_label.value = ""

    # Update UI elements
    def update_status(self):
        if not self.client:
            return
        try:
            np = self.client.GetNowPlayingStatus(True)

            # Playing info
            if np.ContentItem:
                self.track_label.value = getattr(np, "Track", "") or getattr(
                    np.ContentItem, "Name", "No track"
                )
                artist = getattr(np, "Artist", "")
                album = getattr(np, "Album", "")
                self.artist_album_label.value = (
                    f"{artist} • {album}" if artist and album else artist or album or ""
                )

                self.update_track_number()
            else:
                self.track_label.value = ""
                self.artist_album_label.value = ""
                self.track_number_label.value = ""

            # Progress info (seconds)
            duration = getattr(np, "Duration", 0)
            position = getattr(np, "Position", 0)
            if duration > 0:
                self.progress_bar.value = min(max(position / duration, 0.0), 1.0)
                self.position_label.value = (
                    f"{int(position // 60)}:{int(position % 60):02d}"
                )
                self.duration_label.value = (
                    f"{int(duration // 60)}:{int(duration % 60):02d}"
                )
            else:
                self.progress_bar.value = 0.0
                self.position_label.value = "0:00"
                self.duration_label.value = "--:--"

            # Volume
            vol = self.client.GetVolume()
            if vol:
                self.volume_label.value = f"Volume: {vol.Actual}"
                self.volume_slider.value = vol.Actual

            # Shuffle state
            self.shuffle_btn.text = (
                "Shuffle: On" if np.IsShuffleEnabled else "Shuffle: Off"
            )

            # NEW: Repeat state
            repeat_mode = getattr(np, "RepeatSetting", "REPEAT_OFF")
            if repeat_mode == "REPEAT_ALL":
                self.repeat_btn.text = "Repeat: All"
            elif repeat_mode == "REPEAT_ONE":
                self.repeat_btn.text = "Repeat: One"
            else:
                self.repeat_btn.text = "Repeat: Off"

            # Play/pause icon
            self.play_pause_btn.icon = (
                ft.Icons.PAUSE if np.PlayStatus == "PLAY_STATE" else ft.Icons.PLAY_ARROW
            )

            self.page.update()
        except Exception as e:
            print(f"Update error: {e}")

    # keyboard
    def handle_key_event(self, e):
        # print("key pressed")
        if e.key == "+":
            self.volume_up(e)
        elif e.key == "-":
            self.volume_down(e)
        elif e.key == " " or e.key.lower() == "space":
            self.toggle_play_pause(e)
        elif e.key == "Escape":
            self.hide_filebrowser(e)

    # Background task for updating
    async def background_status_loop(self):
        while True:
            if self.client:
                try:
                    self.update_status()
                except Exception as e:
                    print(f"Background update error: {e}")
            await asyncio.sleep(1)

    # Find media server
    async def find_media_server(self):
        print("Looking for media server...")
        try:
            if self.client:
                servers = self.client.GetMediaServerList()
                if servers:
                    server = servers[0]
                    serverid = server.ServerId + "/0"
                    print("Media Server ID:", serverid)
                    self.accountid = serverid
                else:
                    print("No media servers found")
            else:
                print("Error: No SoundTouch client.")
        except Exception as e:
            print("GetMediaServerList Error:", e)


def main(page: ft.Page):
    controller = BoseSoundTouchController(page)
    page.run_task(controller.background_status_loop)
    page.run_task(controller.find_media_server)
    page.window.width = 500
    page.window.height = 720
    page.window.top = 45
    page.window.left = 960


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)
