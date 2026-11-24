import configparser
import datetime as dt
import queue
import threading
import livescores
import json
from date_controls import DateField, week_dates, shift_dates
import ctypes
import random
import sys
import time
from pathlib import Path
import tkinter as tk
from tkinter import colorchooser, filedialog, font as tkfont, messagebox, ttk
from PIL import Image, ImageOps, ImageTk

BASE = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
CONFIG = BASE / 'settings.ini'
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
DEFAULTS = {
    'LiveScores': {'Enabled': 'true', 'Source': '', 'Division': '', 'Start': '', 'End': '',
                   'Height': '80', 'FontSize': '32', 'Speed': '90', 'RefreshSeconds': '30', 'ShowCheckTime': 'false',
                   'TextColor': '#FFFFFF', 'BackgroundColor': '#6C3175'},
    'Slideshow': {'ImageFolder': 'Images', 'DisplaySeconds': '10', 'RandomOrder': 'false',
                  'Fit': 'contain', 'Monitor': ''},
    'Ticker': {'Enabled': 'true', 'Text': 'Welkom bij Apolloon  Bedankt aan al onze sponsors!',
               'Height': '60', 'FontSize': '32', 'Speed': '90', 'GapPixels': '30',
               'TextColor': '#FFFFFF', 'BackgroundColor': '#101820'},
}


def read_config():
    conf = configparser.ConfigParser(interpolation=None)
    conf.read_dict(DEFAULTS)
    conf.read(CONFIG, encoding='utf-8-sig')
    return conf


def path_from_setting(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else BASE / path


def enable_dpi_awareness():
    if sys.platform == 'win32':
        try:
            # Per-monitor DPI voorkomt schaalverschillen tussen Windows en Tk.
            api = ctypes.windll.user32.SetProcessDpiAwarenessContext
            api.argtypes = (ctypes.c_void_p,)
            api.restype = ctypes.c_bool
            if api(ctypes.c_void_p(-4)):
                return
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass


def available_monitors(root):
    """Return (device ID, x, y, width, height, primary) for attached displays."""
    if sys.platform != 'win32':
        return [('default', 0, 0, root.winfo_screenwidth(), root.winfo_screenheight(), True)]

    from ctypes import wintypes

    class RECT(ctypes.Structure):
        _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG),
                    ('right', wintypes.LONG), ('bottom', wintypes.LONG)]

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', RECT),
                    ('rcWork', RECT), ('dwFlags', wintypes.DWORD),
                    ('szDevice', wintypes.WCHAR * 32)]

    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR,
                                     wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)

    def collect(handle, hdc, rect, data):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(info)
        if ctypes.windll.user32.GetMonitorInfoW(handle, ctypes.byref(info)):
            r = info.rcMonitor
            found.append((info.szDevice, r.left, r.top, r.right - r.left,
                          r.bottom - r.top, bool(info.dwFlags & 1)))
        return True

    callback = callback_type(collect)
    if not ctypes.windll.user32.EnumDisplayMonitors(None, None, callback, 0) or not found:
        return [('default', 0, 0, root.winfo_screenwidth(), root.winfo_screenheight(), True)]
    return sorted(found, key=lambda monitor: (not monitor[5], monitor[0]))


def monitor_geometry(monitor):
    _, x, y, width, height, _ = monitor
    return f'{width}x{height}{x:+d}{y:+d}'


def place_window(window, x, y, width, height):
    if sys.platform == 'win32':
        # Tk interpreteert negatieve co�rdinaten relatief aan de rechterrand;
        # SetWindowPos gebruikt de absolute Windows-monitorco�rdinaten.
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        ancestor = user32.GetAncestor
        ancestor.argtypes = (wintypes.HWND, wintypes.UINT)
        ancestor.restype = wintypes.HWND
        hwnd = ancestor(window.winfo_id(), 2)  # GA_ROOT: buitenste Tk-venster
        if not hwnd:
            raise OSError('Het Windows-venster kon niet worden gevonden.')
        api = user32.SetWindowPos
        api.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                        ctypes.c_int, ctypes.c_int, wintypes.UINT)
        api.restype = wintypes.BOOL
        if not api(hwnd, None, x, y, width, height, 0x0004):
            raise OSError('Kon het venster niet op het gekozen scherm plaatsen.')
    else:
        window.geometry(f'{width}x{height}{x:+d}{y:+d}')


class Settings:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Slideshow - instellingen')
        self.root.minsize(760, 720)
        self.slide = None
        self.monitors = available_monitors(self.root)
        conf = read_config()
        self.values = {}
        self.root.geometry('900x800')
        scroll = tk.Canvas(self.root, highlightthickness=0)
        bar = ttk.Scrollbar(self.root, orient='vertical', command=scroll.yview)
        bar.pack(side='right', fill='y')
        scroll.pack(side='left', fill='both', expand=True)
        scroll.configure(yscrollcommand=bar.set)
        panel = ttk.Frame(scroll, padding=18)
        panel_id = scroll.create_window((0, 0), window=panel, anchor='nw')
        panel.bind('<Configure>', lambda e: scroll.configure(scrollregion=scroll.bbox('all')))
        scroll.bind('<Configure>', lambda e: scroll.itemconfigure(panel_id, width=e.width))
        self.root.bind('<MouseWheel>', lambda e: scroll.yview_scroll(-int(e.delta / 120), 'units'))
        ttk.Label(panel, text='Slideshow met ticker', font=('Arial', 17, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 16))
        panel.columnconfigure(1, weight=1)

        def field(row, label, section, key, browse=None):
            ttk.Label(panel, text=label).grid(row=row, column=0, sticky='w', pady=6, padx=(0, 12))
            var = tk.StringVar(value=conf.get(section, key))
            self.values[(section, key)] = var
            ttk.Entry(panel, textvariable=var).grid(row=row, column=1, sticky='ew', pady=6)
            if browse:
                ttk.Button(panel, text='Bladeren.', command=lambda: self.choose_folder(var)).grid(row=row, column=2, padx=(8, 0))

        field(1, 'Afbeeldingsmap', 'Slideshow', 'ImageFolder', browse=True)
        field(2, 'Seconden per foto', 'Slideshow', 'DisplaySeconds')
        self.values[('Slideshow', 'RandomOrder')] = tk.BooleanVar(value=conf.getboolean('Slideshow', 'RandomOrder'))
        ttk.Checkbutton(panel, text='Willekeurige volgorde', variable=self.values[('Slideshow', 'RandomOrder')]).grid(row=3, column=1, sticky='w', pady=6)
        ttk.Label(panel, text='Beeldvulling').grid(row=4, column=0, sticky='w', pady=6)
        self.values[('Slideshow', 'Fit')] = tk.StringVar(value=conf.get('Slideshow', 'Fit'))
        ttk.Combobox(panel, textvariable=self.values[('Slideshow', 'Fit')], values=['contain', 'cover'], state='readonly').grid(row=4, column=1, sticky='ew', pady=6)
        ttk.Label(panel, text='Scherm').grid(row=5, column=0, sticky='w', pady=6)
        self.monitor_labels = {
            f'{monitor[0]} - {monitor[3]}�{monitor[4]}' + (' (hoofdscherm)' if monitor[5] else ''): monitor[0]
            for monitor in self.monitors
        }
        selected = conf.get('Slideshow', 'Monitor')
        label = next((label for label, name in self.monitor_labels.items() if name == selected),
                     next(iter(self.monitor_labels)))
        self.monitor_choice = tk.StringVar(value=label)
        ttk.Combobox(panel, textvariable=self.monitor_choice,
                     values=list(self.monitor_labels), state='readonly').grid(row=5, column=1, sticky='ew', pady=6)
        self.values[('Ticker', 'Enabled')] = tk.BooleanVar(value=conf.getboolean('Ticker', 'Enabled'))
        ttk.Checkbutton(panel, text='Ticker tonen', variable=self.values[('Ticker', 'Enabled')]).grid(row=6, column=1, sticky='w', pady=6)
        ttk.Label(panel, text='Tickertekst').grid(row=7, column=0, sticky='nw', pady=6)
        self.textbox = tk.Text(panel, height=4, wrap='word')
        self.textbox.insert('1.0', conf.get('Ticker', 'Text'))
        self.textbox.grid(row=7, column=1, columnspan=2, sticky='ew', pady=6)
        field(8, 'Balkhoogte (px)', 'Ticker', 'Height')
        field(9, 'Lettergrootte', 'Ticker', 'FontSize')
        field(10, 'Snelheid (px/s)', 'Ticker', 'Speed')
        field(11, 'Ruimte herhaling (px)', 'Ticker', 'GapPixels')
        for row, label, key in ((12, 'Tekstkleur', 'TextColor'), (13, 'Achtergrondkleur', 'BackgroundColor')):
            field(row, label, 'Ticker', key)
            ttk.Button(panel, text='Kiezen.', command=lambda k=key: self.choose_color(k)).grid(row=row, column=2, padx=(8, 0))
        self.values[('LiveScores', 'Enabled')] = tk.BooleanVar(value=conf.getboolean('LiveScores', 'Enabled'))
        ttk.Checkbutton(panel, text="Uitslagenticker bovenaan tonen (zonder logo's)", variable=self.values[('LiveScores', 'Enabled')]).grid(row=14, column=1, sticky='w', pady=6)
        period = ttk.LabelFrame(panel, text='Wedstrijden en periode', padding=14)
        period.grid(row=15, column=0, columnspan=3, sticky='ew', pady=10)
        period.columnconfigure(0, weight=1)
        period.columnconfigure(1, weight=1)
        ttk.Label(period, text='Wedstrijden van').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0,6))
        self.divisions = {livescores.CLUB_LABEL: livescores.CLUB_SOURCE}
        self.division_choice = tk.StringVar(value=conf.get('LiveScores', 'Division') or livescores.CLUB_LABEL)
        self.values[('LiveScores', 'Source')] = tk.StringVar(value=conf.get('LiveScores', 'Source') or livescores.CLUB_SOURCE)
        self.division_box = ttk.Combobox(period, textvariable=self.division_choice,
                                         values=list(self.divisions), state='readonly')
        self.division_box.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0,12))
        self.division_box.bind('<<ComboboxSelected>>', lambda e: self.values[('LiveScores', 'Source')].set(self.divisions[self.division_choice.get()]))
        first, last = week_dates()
        for column, key, label, default in ((0, 'Start', 'Van', first), (1, 'End', 'Tot en met', last)):
            ttk.Label(period, text=label).grid(row=2, column=column, sticky='w', pady=(0,6))
            var = tk.StringVar(value=conf.get('LiveScores', key) or default.strftime('%d/%m/%Y'))
            self.values[('LiveScores', key)] = var
            DateField(period, var).grid(row=3, column=column, sticky='ew', padx=(0,8) if column==0 else (0,0), pady=(0,12))
        ttk.Button(period, text='Vorige week', command=lambda: self.change_week(-7)).grid(row=4, column=0, sticky='ew', padx=(0,4), pady=3)
        ttk.Button(period, text='Deze week', command=lambda: self.change_week(0)).grid(row=4, column=1, sticky='ew', padx=(4,0), pady=3)
        ttk.Button(period, text='Volgende week', command=lambda: self.change_week(7)).grid(row=5, column=0, columnspan=2, sticky='ew', pady=3)
        ttk.Button(period, text='Competities opnieuw laden', command=self.load_divisions).grid(row=6, column=0, columnspan=2, sticky='ew', pady=(8,0))
        field(19, 'Balkhoogte bovenaan (px)', 'LiveScores', 'Height')
        field(20, 'Lettergrootte bovenaan', 'LiveScores', 'FontSize')
        field(21, 'Snelheid bovenaan (px/s)', 'LiveScores', 'Speed')
        field(22, 'Verversen om (seconden)', 'LiveScores', 'RefreshSeconds')
        self.values[('LiveScores', 'ShowCheckTime')] = tk.BooleanVar(value=conf.getboolean('LiveScores', 'ShowCheckTime'))
        ttk.Checkbutton(panel, text='Tijdstip van controle op het scherm tonen', variable=self.values[('LiveScores', 'ShowCheckTime')]).grid(row=23, column=0, columnspan=3, sticky='w', pady=6)
        self.live_status = tk.StringVar(value='Kies alle matchen van Apolloon Spurs of een bepaalde reeks en periode.')
        ttk.Label(panel, textvariable=self.live_status, wraplength=700).grid(row=24, column=0, columnspan=3, sticky='w')
        self.restore_divisions()
        self.division_queue = queue.Queue()
        self.root.after(150, self.load_divisions)
        buttons = ttk.Frame(panel)
        buttons.grid(row=25, column=0, columnspan=3, sticky='e', pady=(18, 0))
        ttk.Button(buttons, text='Opslaan', command=self.save).pack(side='left', padx=5)
        ttk.Button(buttons, text='Opslaan en starten', command=self.start).pack(side='left', padx=5)
        ttk.Label(panel, text='Tijdens afspelen: F2 of Esc instellingen    F11 venster/volledig scherm').grid(row=26, column=0, columnspan=3, sticky='w', pady=(18, 0))

    def change_week(self, days):
        try:
            first, last = week_dates() if days == 0 else shift_dates(
                self.values[('LiveScores', 'Start')].get(), self.values[('LiveScores', 'End')].get(), days)
            self.values[('LiveScores', 'Start')].set(first.strftime('%d/%m/%Y'))
            self.values[('LiveScores', 'End')].set(last.strftime('%d/%m/%Y'))
        except ValueError:
            messagebox.showerror('Ongeldige datum', 'Gebruik DD/MM/JJJJ of kies een datum in de kalender.', parent=self.root)

    def load_divisions(self):
        if getattr(self, 'loading_divisions', False):
            return
        self.loading_divisions = True
        self.live_status.set('Divisies laden.')
        def worker():
            try:
                self.division_queue.put((livescores.competitions(), None))
            except Exception as exc:
                self.division_queue.put((None, str(exc)))
        threading.Thread(target=worker, daemon=True).start()
        self.root.after(100, self.poll_divisions)

    def connection_error(self, context, error):
        try:
            log = BASE / 'verbinding.log'
            previous = log.read_text(encoding='utf-8')[-16000:] if log.exists() else ''
            log.write_text(previous + f'{dt.datetime.now().isoformat(timespec="seconds")} {context}: {error}\n', encoding='utf-8')
        except OSError:
            pass

    def restore_divisions(self):
        try:
            items = json.loads((BASE / 'competitions.json').read_text(encoding='utf-8'))
            self.apply_divisions(items)
        except (OSError, ValueError, TypeError, KeyError):
            source = self.values[('LiveScores', 'Source')].get()
            if source:
                self.apply_divisions([{'name': self.division_choice.get() or 'Opgeslagen competitie', 'source': source}])

    def apply_divisions(self, items):
        if not isinstance(items, list) or not items:
            raise ValueError('Lege competitielijst')
        choices = {livescores.CLUB_LABEL: livescores.CLUB_SOURCE}
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not isinstance(item.get('source'), str):
                raise ValueError('Ongeldige competitielijst')
            if not livescores.valid_source(item['source']):
                raise ValueError('Ongeldige competitielink')
            choices[item['name']] = item['source']
        source = self.values[('LiveScores', 'Source')].get()
        selected = next((name for name, url in choices.items() if url == source), '')
        if source and not selected:
            selected = self.division_choice.get() or 'Opgeslagen competitie'
            choices[selected] = source
        if not selected:
            selected = livescores.CLUB_LABEL
            self.values[('LiveScores', 'Source')].set(choices[selected])
        self.divisions = choices
        self.division_box.configure(values=list(choices))
        self.division_choice.set(selected)

    def poll_divisions(self):
        try:
            items, error = self.division_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self.poll_divisions)
            return
        self.loading_divisions = False
        if error:
            self.connection_error('Competities ophalen', error)
            fallback = 'De opgeslagen competitielijst blijft beschikbaar. ' if self.divisions else ''
            self.live_status.set('Competities niet vernieuwd. ' + fallback + 'Oorzaak: ' + error)
            return
        self.apply_divisions(items)
        try:
            (BASE / 'competitions.json').write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
        except OSError:
            pass
        self.live_status.set('Kies alle matchen van Apolloon Spurs of een bepaalde reeks.')

    def choose_folder(self, var):
        folder = filedialog.askdirectory(initialdir=str(path_from_setting(var.get())))
        if folder:
            var.set(folder)

    def choose_color(self, key):
        var = self.values[('Ticker', key)]
        color = colorchooser.askcolor(color=var.get(), parent=self.root)[1]
        if color:
            var.set(color.upper())

    def save(self):
        try:
            conf = read_config()
            for (section, key), var in self.values.items():
                conf.set(section, key, str(var.get()).lower() if isinstance(var, tk.BooleanVar) else var.get().strip())
            conf.set('LiveScores', 'Division', self.division_choice.get())
            conf.set('Slideshow', 'Monitor', self.monitor_labels[self.monitor_choice.get()])
            text = '      '.join(line.strip() for line in self.textbox.get('1.0', 'end-1c').splitlines() if line.strip())
            conf.set('Ticker', 'Text', text)
            conf.remove_option('Ticker', 'File')
            if float(conf.get('Slideshow', 'DisplaySeconds')) < 1:
                raise ValueError('Seconden per foto moet minstens 1 zijn.')
            for key, minimum in (('Height', 24), ('FontSize', 12), ('Speed', 0), ('GapPixels', 0)):
                value = float(conf.get('Ticker', key)) if key == 'Speed' else int(conf.get('Ticker', key))
                if value < minimum:
                    raise ValueError(f'{key} moet minstens {minimum} zijn.')
            for key in ('TextColor', 'BackgroundColor'):
                self.root.winfo_rgb(conf.get('Ticker', key))
            if conf.getboolean('LiveScores', 'Enabled'):
                source = conf.get('LiveScores', 'Source')
                if not livescores.valid_source(source):
                    raise ValueError('Kies alle matchen van Apolloon Spurs of een reeks uit de lijst.')
            dates = []
            for key in ('Start', 'End'):
                value = conf.get('LiveScores', key).strip()
                dates.append(dt.datetime.strptime(value, '%d/%m/%Y').date() if value else dt.date.today())
            if dates[0] > dates[1]:
                raise ValueError('De begindatum moet voor of op de einddatum liggen.')
            for key, minimum in (('Height', 24), ('FontSize', 12), ('Speed', 0), ('RefreshSeconds', 15)):
                value = int(conf.get('LiveScores', key)) if key in ('Height', 'FontSize') else float(conf.get('LiveScores', key))
                import math
                if not math.isfinite(value) or value < minimum:
                    raise ValueError(f'Bovenste ticker: {key} moet minstens {minimum} zijn.')
            with CONFIG.open('w', encoding='utf-8') as output:
                conf.write(output)
            return True
        except (OSError, ValueError, tk.TclError, configparser.Error) as exc:
            messagebox.showerror('Instellingen niet opgeslagen', str(exc), parent=self.root)
            return False

    def start(self):
        if not self.save():
            return
        self.root.withdraw()
        self.slide = Slideshow(self)

    def return_to_settings(self):
        if self.slide:
            self.slide.window.destroy()
            self.slide = None
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        # Neem aanpassingen uit het INI-bestand over als het buiten het venster werd gewijzigd.
        conf = read_config()
        selected = conf.get('Slideshow', 'Monitor')
        self.monitor_choice.set(next((label for label, name in self.monitor_labels.items() if name == selected),
                                     next(iter(self.monitor_labels))))
        for (section, key), var in self.values.items():
            var.set(conf.getboolean(section, key) if isinstance(var, tk.BooleanVar) else conf.get(section, key))
        self.textbox.delete('1.0', 'end')
        self.textbox.insert('1.0', conf.get('Ticker', 'Text'))


class Slideshow:
    def __init__(self, settings):
        self.settings = settings
        self.window = tk.Toplevel(settings.root)
        self.window.title('Slideshow met ticker')
        self.window.configure(bg='black')
        selected = read_config().get('Slideshow', 'Monitor')
        monitor = next((item for item in available_monitors(settings.root) if item[0] == selected), None)
        if monitor is None:
            monitor = available_monitors(settings.root)[0]
        self.monitor = monitor
        # Een venster zonder rand op de exacte monitorafmetingen is op Windows
        # voorspelbaarder dan Tk's fullscreen bij meerdere schermen.
        self.window.withdraw()
        self.window.overrideredirect(True)
        _, x, y, width, height, _ = self.monitor
        self.window.geometry(f'{width}x{height}+0+0')
        self.window.deiconify()
        place_window(self.window, x, y, width, height)
        self.window.lift()
        self.window.after_idle(self.ensure_position)
        self.window.after(250, self.ensure_position)
        self.fullscreen = True
        self.window.bind('<Escape>', lambda event: self.settings.return_to_settings())
        self.window.bind('<F2>', lambda event: self.settings.return_to_settings())
        self.window.bind('<F11>', self.toggle_fullscreen)
        self.window.protocol('WM_DELETE_WINDOW', self.settings.return_to_settings)
        self.window.bind('<Configure>', self.on_resize)
        self.canvas = tk.Canvas(self.window, bg='black', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.image_item = self.canvas.create_image(0, 0, anchor='center')
        self.status_item = self.canvas.create_text(0, 0, fill='white', font=('Arial', 22), text='Afbeeldingen laden...')
        self.ticker_bg = self.canvas.create_rectangle(0, 0, 0, 0, fill='#101820', outline='')
        self.ticker_items = [self.canvas.create_text(0, 0, text='', fill='white', anchor='w')]
        self.live_bg = self.canvas.create_rectangle(0, 0, 0, 0, outline='')
        self.live_items = []
        self.live_text = 'Kies een divisie in de instellingen'
        self.live_x = 0.0
        self.live_queue = queue.Queue()
        self.live_busy = False
        self.live_last = 0
        self.live_signature = None
        self.live_generation = 0
        self.live_checked = None
        self.photo = None
        self.current = None
        self.files = []
        self.index = 0
        self.last_scan = 0
        self.last_config = None
        self.last_image = 0
        self.text = ''
        self.x = 0.0
        self.text_width = 0
        self.last_tick = time.monotonic()
        self.reload_settings(force=True)
        self.show_next()
        self.tick()

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.window.withdraw()
        self.window.overrideredirect(self.fullscreen)
        _, x, y, width, height, _ = self.monitor
        target_width, target_height = (width, height) if self.fullscreen else (
            max(500, width * 3 // 4), max(350, height * 3 // 4))
        self.window.geometry(f'{target_width}x{target_height}+0+0')
        self.window.deiconify()
        place_window(self.window, x, y, target_width, target_height)
        self.window.lift()
        self.window.after_idle(self.ensure_position)
        self.window.after(250, self.ensure_position)

    def ensure_position(self):
        if self.window.winfo_exists():
            _, x, y, width, height, _ = self.monitor
            if not self.fullscreen:
                width, height = max(500, width * 3 // 4), max(350, height * 3 // 4)
            place_window(self.window, x, y, width, height)

    def on_resize(self, event):
        if event.widget is self.window and self.current:
            self.window.after(150, self.render_current)

    def reload_settings(self, force=False):
        try:
            stamp = CONFIG.stat().st_mtime_ns
            if not force and stamp == self.last_config:
                return
            conf = read_config()
            self.folder = path_from_setting(conf.get('Slideshow', 'ImageFolder'))
            self.seconds = max(1, conf.getfloat('Slideshow', 'DisplaySeconds'))
            self.random = conf.getboolean('Slideshow', 'RandomOrder')
            self.fit = conf.get('Slideshow', 'Fit').lower()
            self.enabled = conf.getboolean('Ticker', 'Enabled')
            self.height = max(24, conf.getint('Ticker', 'Height'))
            self.fontsize = max(12, conf.getint('Ticker', 'FontSize'))
            self.speed = max(0, conf.getfloat('Ticker', 'Speed'))
            self.gap = max(0, conf.getint('Ticker', 'GapPixels'))
            self.text_color = conf.get('Ticker', 'TextColor').strip()
            self.background_color = conf.get('Ticker', 'BackgroundColor').strip()
            self.window.winfo_rgb(self.text_color)
            self.window.winfo_rgb(self.background_color)
            self.live_enabled = conf.getboolean('LiveScores', 'Enabled')
            self.live_height = max(24, conf.getint('LiveScores', 'Height'))
            self.live_fontsize = max(12, conf.getint('LiveScores', 'FontSize'))
            self.live_speed = max(0, conf.getfloat('LiveScores', 'Speed'))
            self.live_refresh = max(15, conf.getfloat('LiveScores', 'RefreshSeconds'))
            self.live_show_check = conf.getboolean('LiveScores', 'ShowCheckTime')
            self.live_source = conf.get('LiveScores', 'Source')
            self.live_start = conf.get('LiveScores', 'Start')
            self.live_end = conf.get('LiveScores', 'End')
            self.live_color = conf.get('LiveScores', 'TextColor')
            self.canvas.itemconfigure(self.live_bg, fill=conf.get('LiveScores', 'BackgroundColor'))
            signature = (self.live_source, self.live_start, self.live_end)
            if signature != self.live_signature:
                self.live_generation += 1
                self.live_signature = signature
                self.live_last = 0
                self.live_checked = None
                self.live_text = 'Uitslagen laden.'
            previous_text = self.text
            self.text = conf.get('Ticker', 'Text').strip()
            if previous_text != self.text:
                self.x = self.canvas.winfo_width()
            self.text_width = tkfont.Font(family='Arial', size=self.fontsize, weight='bold').measure(self.text)
            for item in self.ticker_items:
                self.canvas.itemconfigure(item, text=self.text, font=('Arial', self.fontsize, 'bold'), fill=self.text_color)
            self.canvas.itemconfigure(self.ticker_bg, fill=self.background_color)
            self.last_config = stamp
            self.last_scan = 0
            self.layout()
            if self.current:
                self.render_current()
        except (OSError, ValueError, tk.TclError, configparser.Error) as exc:
            print(f'Instellingen niet geladen: {exc}', file=sys.stderr)

    def refresh_files(self):
        try:
            found = sorted((p for p in self.folder.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS), key=lambda p: p.name.lower())
        except OSError:
            found = []
        if set(found) != set(self.files):
            if self.random:
                random.shuffle(found)
            self.files = found
            self.index = 0

    def layout(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        top = self.live_height if self.live_enabled else 0
        bottom = max(top, h - (self.height if self.enabled else 0))
        self.canvas.coords(self.live_bg, 0, 0, w, top)
        self.canvas.itemconfigure(self.live_bg, state='normal' if self.live_enabled else 'hidden')
        self.position_live()
        self.canvas.coords(self.image_item, w // 2, (top + bottom) // 2)
        self.canvas.coords(self.status_item, w // 2, (top + bottom) // 2)
        self.canvas.coords(self.ticker_bg, 0, bottom, w, h)
        self.canvas.itemconfigure(self.ticker_bg, state='normal' if self.enabled else 'hidden')
        self.position_ticker()

    def position_ticker(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        pitch = self.text_width + self.gap
        count = max(0, int((w - self.x) // pitch)) + 2 if self.enabled and self.text and pitch else 0
        while len(self.ticker_items) < count:
            self.ticker_items.append(self.canvas.create_text(0, 0, text=self.text, fill=self.text_color,
                                     font=('Arial', self.fontsize, 'bold'), anchor='w'))
        for i, item in enumerate(self.ticker_items):
            visible = i < count
            self.canvas.itemconfigure(item, state='normal' if visible else 'hidden')
            if visible:
                self.canvas.coords(item, self.x + i * pitch, h - self.height // 2)

    def position_live(self):
        width = tkfont.Font(family='Arial', size=self.live_fontsize, weight='bold').measure(self.live_text)
        self.live_pitch = width + self.gap
        w = self.canvas.winfo_width()
        count = max(0, int((w - self.live_x) // self.live_pitch)) + 2 if self.live_enabled and self.live_pitch else 0
        while len(self.live_items) < count:
            self.live_items.append(self.canvas.create_text(0, 0, anchor='w'))
        for i, item in enumerate(self.live_items):
            self.canvas.itemconfigure(item, text=self.live_text, fill=self.live_color,
                font=('Arial', self.live_fontsize, 'bold'), state='normal' if i < count else 'hidden')
            self.canvas.coords(item, self.live_x + i * self.live_pitch, self.live_height // 2)

    def refresh_live(self, now):
        try:
            generation, result, error = self.live_queue.get_nowait()
            self.live_busy = False
            if generation == self.live_generation:
                if error:
                    self.settings.connection_error('Scores ophalen', error)
                    stamp = self.live_checked or 'geen'
                    self.live_text = self.live_text.split('   |   ')[0] + '   |   Verbinding mislukt'
                    if self.live_show_check:
                        self.live_text += ' - laatste controle: ' + stamp
                    self.settings.live_status.set('Scores niet bijgewerkt: ' + error)
                else:
                    games, failures = result
                    self.live_checked = dt.datetime.now().strftime('%H:%M:%S')
                    self.live_text = livescores.ticker_text(games)
                    if self.live_show_check:
                        self.live_text += '   |   Controle: ' + self.live_checked
                    self.settings.live_status.set(f'{len(games)} wedstrijden - controle {self.live_checked}' + (f' - {failures} scores niet bijgewerkt' if failures else ''))
                self.position_live()
        except queue.Empty:
            pass
        if not self.live_enabled or self.live_busy or now - self.live_last < self.live_refresh:
            return
        self.live_last = now
        if not self.live_source:
            return
        try:
            start, end = [(dt.datetime.strptime(v, '%d/%m/%Y').date() if v else dt.date.today()).isoformat() for v in (self.live_start, self.live_end)]
        except ValueError:
            self.live_text = 'Ongeldige datum - gebruik DD/MM/JJJJ'
            return
        signature = (self.live_source, start, end)
        if getattr(self, 'live_date_signature', None) != signature:
            self.live_date_signature = signature
            self.live_text = 'Uitslagen laden.'
        source, generation = self.live_source, self.live_generation
        self.live_busy = True
        def worker():
            try:
                self.live_queue.put((generation, livescores.load_scores(source, start, end), None))
            except Exception as exc:
                self.live_queue.put((generation, None, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def render_current(self):
        if not self.current or not self.window.winfo_exists():
            return
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height() - (self.height if self.enabled else 0) - (self.live_height if self.live_enabled else 0))
        try:
            with Image.open(self.current) as src:
                image = ImageOps.exif_transpose(src).convert('RGB')
            if self.fit == 'cover':
                image = ImageOps.fit(image, (w, h), method=Image.Resampling.LANCZOS)
            else:
                image.thumbnail((w, h), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(image)
            self.canvas.itemconfigure(self.image_item, image=self.photo)
            self.canvas.itemconfigure(self.status_item, text='')
        except (OSError, ValueError) as exc:
            self.canvas.itemconfigure(self.image_item, image='')
            self.canvas.itemconfigure(self.status_item, text=f'Afbeelding niet leesbaar: {self.current.name}')
            print(f'{self.current}: {exc}', file=sys.stderr)
        self.layout()

    def show_next(self):
        self.refresh_files()
        if self.files:
            self.current = self.files[self.index % len(self.files)]
            self.index += 1
            self.render_current()
        else:
            self.current = None
            self.canvas.itemconfigure(self.image_item, image='')
            self.canvas.itemconfigure(self.status_item, text=f'Plaats afbeeldingen in: {self.folder}')
            self.layout()
        self.last_image = time.monotonic()

    def tick(self):
        if not self.window.winfo_exists():
            return
        now = time.monotonic()
        elapsed = min(now - self.last_tick, 0.2)
        self.last_tick = now
        self.reload_settings()
        self.refresh_live(now)
        if self.live_enabled:
            self.live_x -= self.live_speed * elapsed
            if getattr(self, "live_pitch", 0) and self.live_x <= -self.live_pitch:
                self.live_x %= self.live_pitch
                self.live_x -= self.live_pitch
            self.position_live()
        if now - self.last_scan >= 2:
            self.last_scan = now
            previous = self.files[:]
            self.refresh_files()
            if bool(self.files) != bool(previous):
                self.show_next()
        if now - self.last_image >= self.seconds:
            self.show_next()
        if self.enabled and self.text:
            self.x -= self.speed * elapsed
            pitch = self.text_width + self.gap
            if pitch and self.x <= -pitch:
                self.x += pitch * (1 + int((-pitch - self.x) // pitch))
            self.position_ticker()
        self.window.after(30, self.tick)


if __name__ == '__main__':
    enable_dpi_awareness()
    Settings().root.mainloop()
