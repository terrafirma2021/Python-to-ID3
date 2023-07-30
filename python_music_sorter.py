import os
import subprocess
import sys
import curses
import shutil
import re
import threading
import concurrent.futures
from pathlib import Path
import eyed3

def install_missing_dependencies():
    try:
        import eyed3
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "eyed3"])

class MusicOrganizer:
    def __init__(self):
        self.music_dir = None
        self.backup_dir = None
        self.files = []
        self.selected = [False]*7
        self.total_files_processed = 0

    def set_music_dir(self, path):
        self.music_dir = path
        self.files = list(Path(self.music_dir).rglob("*.[mM][pP]3"))

    def set_backup_dir(self, path):
        self.backup_dir = path

    def backup_files(self):
        if self.backup_dir:
            for file in self.files:
                shutil.copy(file, self.backup_dir)

    def process_file(self, file, process_func):
        audiofile = eyed3.load(file)
        if audiofile.tag is None:
            audiofile.initTag()
        new_title, new_artist = process_func(os.path.basename(file).split('.')[0])
        audiofile.tag.title = new_title
        if new_artist:
            audiofile.tag.artist = new_artist
        audiofile.tag.save()
        self.total_files_processed += 1
        self.rename_file(file, new_title)

    def rename_file(self, file, new_title):
        dir_path = os.path.dirname(file)
        new_file_path = os.path.join(dir_path, f"{new_title}.mp3")
        os.rename(file, new_file_path)

    def extract_artist(self, title):
        if '-' in title:
            artist, title = title.split('-', 1)
            return title.strip(), artist.strip()
        return title, None

    def fix_casing(self, title):
        return title.title(), None

    def remove_numbers(self, title):
        return re.sub(r'\d+', '', title), None

    def remove_urls(self, title):
        return re.sub(r'http\S+|www.\S+', '', title), None

    def replace_underscores(self, title):
        return title.replace('_', ' '), None

    def remove_encoded_chars(self, title):
        return title.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore'), None

    def remove_symbols(self, title):
        return re.sub('[^\w\s]', '', title), None

    def process_files(self, process_func):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.process_file, self.files, [process_func]*len(self.files))

organizer = MusicOrganizer()
install_missing_dependencies()

def display_menu(stdscr, current_row, menu_options):
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    for idx, row in enumerate(menu_options):
        x = w // 2 - len(row) // 2
        y = h // 2 - len(menu_options) // 2 + idx

        if 2 <= idx <= 8:
            if organizer.selected[idx-2]:
                row = "[X] " + row[4:]
            else:
                row = "[ ] " + row[4:]

        if idx == current_row:
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(y, x, row)
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(y, x, row)

    stdscr.refresh()

def main(stdscr):
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

    menu_options = ["Set music folder",
                    "Set backup folder",
                    "[ ] Extract Artist from title",
                    "[ ] Fix Casing",
                    "[ ] Remove numbers from titles",
                    "[ ] Remove URLs from titles",
                    "[ ] Replace underscores with spaces",
                    "[ ] Remove encoded characters",
                    "[ ] Remove symbols",
                    "Run",
                    "Exit"]

    current_row = 0

    while True:
        display_menu(stdscr, current_row, menu_options)

        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu_options) - 1:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:  
            if 0 <= current_row <= 1:
                stdscr.clear()
                stdscr.addstr(0, 0, f"Enter the path for the {menu_options[current_row]}:")
                curses.echo()
                path = stdscr.getstr().decode('utf-8')
                curses.noecho()
                if current_row == 0:
                    organizer.set_music_dir(path)
                    menu_options[0] = "Set music folder: " + path
                else:
                    organizer.set_backup_dir(path)
                    menu_options[1] = "Set backup folder: " + path
            elif 2 <= current_row <= 8:
                organizer.selected[current_row-2] = not organizer.selected[current_row-2]
            elif current_row == 9:
                process_funcs = [organizer.extract_artist,
                                 organizer.fix_casing,
                                 organizer.remove_numbers,
                                 organizer.remove_urls,
                                 organizer.replace_underscores,
                                 organizer.remove_encoded_chars,
                                 organizer.remove_symbols]
                for idx, selected in enumerate(organizer.selected):
                    if selected:
                        organizer.process_files(process_funcs[idx])
                stdscr.clear()
                stdscr.addstr(0, 0, f"Processing complete. {organizer.total_files_processed} files processed.")
                stdscr.refresh()
                stdscr.getch()
            elif current_row == 10:
                exit()

curses.wrapper(main)
