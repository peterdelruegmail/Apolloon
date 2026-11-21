import calendar
import datetime as dt
import tkinter as tk
from tkinter import ttk

MONTHS = ('januari', 'februari', 'maart', 'april', 'mei', 'juni',
          'juli', 'augustus', 'september', 'oktober', 'november', 'december')

def parse_date(value):
    return dt.datetime.strptime(value, '%d/%m/%Y').date()

def week_dates(today=None):
    today = today or dt.date.today()
    start = today - dt.timedelta(days=today.weekday())
    return start, start + dt.timedelta(days=6)

def shift_dates(start, end, days):
    return parse_date(start) + dt.timedelta(days=days), parse_date(end) + dt.timedelta(days=days)

class DateField(ttk.Frame):
    def __init__(self, parent, variable):
        super().__init__(parent)
        self.variable = variable
        self.popup = None
        self.columnconfigure(0, weight=1)
        ttk.Entry(self, textvariable=variable, width=14).grid(row=0, column=0, sticky='ew')
        ttk.Button(self, text='Kalender', command=self.open_calendar).grid(row=0, column=1, padx=(5, 0))

    def open_calendar(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.lift()
            return
        try:
            selected = parse_date(self.variable.get())
        except ValueError:
            selected = dt.date.today()
        self.month = selected.replace(day=1)
        popup = self.popup = tk.Toplevel(self)
        popup.title('Kies een datum')
        popup.transient(self.winfo_toplevel())
        popup.resizable(False, False)
        popup.bind('<Escape>', lambda e: popup.destroy())
        self.body = ttk.Frame(popup, padding=12)
        self.body.pack()
        self.draw_month()
        popup.update_idletasks()
        x = min(self.winfo_rootx(), popup.winfo_screenwidth() - popup.winfo_reqwidth())
        y = min(self.winfo_rooty() + self.winfo_height(), popup.winfo_screenheight() - popup.winfo_reqheight())
        popup.geometry(f'+{max(0,x)}+{max(0,y)}')
        popup.grab_set()

    def move_month(self, delta):
        index = self.month.year * 12 + self.month.month - 1 + delta
        year, month = divmod(index, 12)
        if 1 <= year <= 9999:
            self.month = dt.date(year, month + 1, 1)
            self.draw_month()

    def choose(self, date):
        self.variable.set(date.strftime('%d/%m/%Y'))
        self.popup.destroy()

    def draw_month(self):
        for widget in self.body.winfo_children():
            widget.destroy()
        ttk.Button(self.body, text='<', width=3, command=lambda: self.move_month(-1)).grid(row=0, column=0)
        ttk.Label(self.body, text=f'{MONTHS[self.month.month-1]} {self.month.year}', anchor='center').grid(row=0, column=1, columnspan=5, sticky='ew')
        ttk.Button(self.body, text='>', width=3, command=lambda: self.move_month(1)).grid(row=0, column=6)
        for column, name in enumerate(('ma', 'di', 'wo', 'do', 'vr', 'za', 'zo')):
            ttk.Label(self.body, text=name, anchor='center').grid(row=1, column=column, pady=8, sticky='ew')
        for row, week in enumerate(calendar.monthcalendar(self.month.year, self.month.month), 2):
            for column, day in enumerate(week):
                if day:
                    date = self.month.replace(day=day)
                    ttk.Button(self.body, text=str(day), width=4, command=lambda d=date: self.choose(d)).grid(row=row, column=column, padx=2, pady=2)
        ttk.Button(self.body, text='Vandaag', command=lambda: self.choose(dt.date.today())).grid(row=8, column=0, columnspan=7, sticky='ew', pady=(8,0))
