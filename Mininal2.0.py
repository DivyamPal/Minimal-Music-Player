import dearpygui.dearpygui as dpg
import ntpath
import json
from mutagen.mp3 import MP3
from tkinter import Tk, filedialog
import threading
import pygame
import time
import os
import atexit
import random

# Initialize Pygame and DearPyGui
dpg.create_context()
dpg.create_viewport(title="Minimal Music Player", large_icon="icon.ico", small_icon="icon.ico")
pygame.mixer.init()
_DEFAULT_MUSIC_VOLUME = 0.5
pygame.mixer.music.set_volume(_DEFAULT_MUSIC_VOLUME)
global state
state = None

# Node and Linked List Classes
class Node:
    def __init__(self, song_path):
        self.song_path = song_path
        self.next = None
        self.prev = None

class SongLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self.current = None

    def add_song(self, song_path):
        new_node = Node(song_path)
        if not self.head:
            self.head = self.tail = new_node
        else:
            self.tail.next = new_node
            new_node.prev = self.tail
            self.tail = new_node

    def remove_all_songs(self):
        self.head = self.tail = self.current = None

    def find_song(self, song_path):
        node = self.head
        while node:
            if node.song_path == song_path:
                return node
            node = node.next
        return None

    def set_current_song(self, song_path):
        self.current = self.find_song(song_path)

    def next_song(self):
        if self.current and self.current.next:
            self.current = self.current.next
            return self.current.song_path
        return None

    def previous_song(self):
        if self.current and self.current.prev:
            self.current = self.current.prev
            return self.current.song_path
        return None

    def remove_song(self, song_path):
        node = self.head
        while node:
            if node.song_path == song_path:
                if node.prev:
                    node.prev.next = node.next
                else:
                    self.head = node.next
                if node.next:
                    node.next.prev = node.prev
                else:
                    self.tail = node.prev
                return True
            node = node.next
        return False

# Initialize the linked list
songs = SongLinkedList()

def update_volume(sender, app_data):
    pygame.mixer.music.set_volume(app_data / 100.0)

def remove_song_from_database(sender, app_data, user_data):
    filename = user_data
    if songs.remove_song(filename):
        with open("data/songs.json", "r+") as file:
            data = json.load(file)
            if filename in data["songs"]:
                data["songs"].remove(filename)
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
        dpg.delete_item("list", children_only=True)
        load_database()

def load_database():
    song_data = json.load(open("data/songs.json", "r"))["songs"]
    for filename in song_data:
        songs.add_song(filename)
        with dpg.group(horizontal=True, parent="list"):
            dpg.add_button(
                label=f"{ntpath.basename(filename)}",
                callback=play,
                width=400,
                height=25,
                user_data=filename.replace("\\", "/")
            )
            dpg.add_button(
                label="Remove",
                callback=remove_song_from_database,
                user_data=filename.replace("\\", "/"),
                width=75,
                height=25
            )
        dpg.add_spacer(height=2, parent="list")

def update_database(filename):
    data = json.load(open("data/songs.json", "r+"))
    if filename not in data["songs"]:
        data["songs"].append(filename)
        json.dump(data, open("data/songs.json", "w"), indent=4)

def update_slider():
    global state
    while pygame.mixer.music.get_busy() or state != 'paused':
        dpg.configure_item(item="pos", default_value=pygame.mixer.music.get_pos() / 1000)
        time.sleep(0.7)
    state = None
    dpg.configure_item("cstate", default_value="State: None")
    dpg.configure_item("csong", default_value="Now Playing : ")
    dpg.configure_item("play", label="Play")
    dpg.configure_item(item="pos", max_value=100)
    dpg.configure_item(item="pos", default_value=0)

def play(sender, app_data, user_data):
    global state
    if user_data:
        songs.set_current_song(user_data)
        pygame.mixer.music.load(user_data)
        audio = MP3(user_data)
        dpg.configure_item(item="pos", max_value=audio.info.length)
        pygame.mixer.music.play()
        threading.Thread(target=update_slider, daemon=True).start()
        dpg.configure_item("play", label="Pause")
        state = "playing"
        dpg.configure_item("cstate", default_value="State: Playing")
        dpg.configure_item("csong", default_value=f"Now Playing : {ntpath.basename(user_data)}")

def play_pause():
    global state
    if state == "playing":
        state = "paused"
        pygame.mixer.music.pause()
        dpg.configure_item("play", label="Play")
        dpg.configure_item("cstate", default_value="State: Paused")
    elif state == "paused":
        state = "playing"
        pygame.mixer.music.unpause()
        dpg.configure_item("play", label="Pause")
        dpg.configure_item("cstate", default_value="State: Playing")
    else:
        song_data = json.load(open("data/songs.json", "r"))["songs"]
        if song_data:
            song = random.choice(song_data)
            songs.set_current_song(song)
            play(None, None, song)

def pre():
    previous_song = songs.previous_song()
    if previous_song:
        play(None, None, previous_song)

def next():
    next_song = songs.next_song()
    if next_song:
        play(None, None, next_song)

def stop():
    global state
    pygame.mixer.music.stop()
    state = None

def add_files():
    root = Tk()
    root.withdraw()
    filename = filedialog.askopenfilename(filetypes=[("Music Files", ("*.mp3", "*.wav", "*.ogg"))])
    root.quit()
    if filename and filename.endswith((".mp3", ".wav", ".ogg")):
        update_database(filename)
        songs.add_song(filename)
        dpg.add_button(label=f"{ntpath.basename(filename)}", callback=play, width=-1, height=25,
                       user_data=filename.replace("\\", "/"), parent="list")
        dpg.add_spacer(height=2, parent="list")

def add_folder():
    root = Tk()
    root.withdraw()
    folder = filedialog.askdirectory()
    root.quit()
    for filename in os.listdir(folder):
        full_path = os.path.join(folder, filename)
        if filename.endswith((".mp3", ".wav", ".ogg")):
            update_database(full_path)
            songs.add_song(full_path)
            dpg.add_button(label=f"{ntpath.basename(full_path)}", callback=play, width=-1, height=25,
                           user_data=full_path.replace("\\", "/"), parent="list")
            dpg.add_spacer(height=2, parent="list")

def search(sender, app_data, user_data):
    song_data = json.load(open("data/songs.json", "r"))["songs"]
    dpg.delete_item("list", children_only=True)
    for song in song_data:
        if app_data.lower() in song.lower():
            dpg.add_button(label=f"{ntpath.basename(song)}", callback=play, width=-1, height=25,
                           user_data=song, parent="list")
            dpg.add_spacer(height=2, parent="list")

def removeall():
    songs.remove_all_songs()
    with open("data/songs.json", "w") as f:
        json.dump({"songs": []}, f, indent=4)
    dpg.delete_item("list", children_only=True)

# GUI Theme and Layout
with dpg.theme(tag="base"):
    with dpg.theme_component():
        dpg.add_theme_color(dpg.mvThemeCol_Button, (223,0,255))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (137, 142, 255, 95))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (137, 142, 255))
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3)
        dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 4, 4)
        dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 4, 4)
        dpg.add_theme_style(dpg.mvStyleVar_WindowTitleAlign, 0.50, 0.50)
        dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 14)
        dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (25, 25, 25))
        dpg.add_theme_color(dpg.mvThemeCol_Border, (0,0,0))

with dpg.window(label="Minimal Music Player", tag="Main", width=620, height=600, pos=(100, 100), no_collapse=True):
    dpg.add_button(label="Add Folder", callback=add_folder, width=100, height=25)
    dpg.add_button(label="Add File", callback=add_files, width=100, height=25)
    dpg.add_button(label="Remove All", callback=removeall, width=100, height=25)
    dpg.add_input_text(callback=search, hint="Search", width=375, height=25)
    dpg.add_separator()
    with dpg.child_window(width=595, height=400, tag="list"):
        load_database()
    dpg.add_slider_int(label="Position", width=300, height=10, min_value=0, max_value=100, tag="pos", default_value=0)
    dpg.add_slider_int(label="Volume", width=200, height=10, min_value=0, max_value=100, default_value=30, callback=update_volume)
    dpg.add_separator()
    with dpg.group(horizontal=True):
        dpg.add_button(label="Previous", callback=pre, width=100, height=25)
        dpg.add_button(label="Play", callback=play_pause, width=100, height=25, tag="play")
        dpg.add_button(label="Stop", callback=stop, width=100, height=25)
        dpg.add_button(label="Next", callback=next, width=100, height=25)
    dpg.add_text("Now Playing : ", tag="csong")
    dpg.add_text("State: None", tag="cstate")


load_database()
dpg.bind_theme("base")
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()

atexit.register(lambda: pygame.quit())
