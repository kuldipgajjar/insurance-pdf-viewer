"""
Insurance PDF Viewer - Offline Android App
==========================================
Parses LIC / insurance policy PDFs and shows data in a table with WhatsApp share.
Same filtering logic as the original Flask app.py.

Password: 1112
"""

import os
import threading
import webbrowser
from urllib.parse import quote

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle

IS_ANDROID = False
try:
    from android.permissions import request_permissions, Permission
    IS_ANDROID = True
except ImportError:
    pass

CORRECT_PIN = '1112'
COLUMNS = ['S.No', 'PolicyNo', 'Name of Assured', 'D.o.C', 'TotPrem']
COL_WIDTHS = [dp(45), dp(110), dp(175), dp(85), dp(85)]
SHARE_COL_WIDTH = dp(75)

SKIP_KEYWORDS = [
    'Branch Code: 85E', '189- SUTHARVAS', 'Page Total',
    'Grand Total', 'FY - First year Prem.', '( Page No :',
]

C_BG         = (0.07, 0.07, 0.12, 1)
C_CARD       = (0.12, 0.12, 0.20, 1)
C_GREEN      = (0.18, 0.75, 0.42, 1)
C_GREEN_DARK = (0.12, 0.52, 0.30, 1)
C_BLUE       = (0.22, 0.45, 0.82, 1)
C_ACCENT     = (0.07, 0.57, 0.32, 1)
C_ROW_ODD   = (0.09, 0.09, 0.15, 1)
C_ROW_EVEN  = (0.12, 0.12, 0.19, 1)
C_TEXT       = (0.92, 0.92, 0.92, 1)
C_MUTED      = (0.55, 0.55, 0.62, 1)
C_ERROR      = (1.0,  0.32, 0.32, 1)
C_HEADER     = (0.14, 0.48, 0.30, 1)


def _resolve_content_uri(raw_path):
    if not raw_path or not raw_path.startswith('content://'):
        return raw_path
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Uri = autoclass('android.net.Uri')
        context = PythonActivity.mActivity
        content_resolver = context.getContentResolver()
        uri = Uri.parse(raw_path)
        filename = 'selected.pdf'
        try:
            cursor = content_resolver.query(uri, None, None, None, None)
            if cursor and cursor.moveToFirst():
                col_idx = cursor.getColumnIndex('_display_name')
                if col_idx >= 0:
                    filename = cursor.getString(col_idx)
                cursor.close()
        except Exception:
            pass
        dest = os.path.join(App.get_running_app().user_data_dir, filename)
        input_stream = content_resolver.openInputStream(uri)
        with open(dest, 'wb') as out_f:
            buf = bytearray(8192)
            while True:
                n = input_stream.read(buf)
                if n == -1:
                    break
                out_f.write(bytes(buf[:n]))
        input_stream.close()
        return dest
    except Exception as e:
        print(f'[resolve_content_uri] {e}')
        return raw_path


def parse_pdf(pdf_path):
    import pdfplumber
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_tables()
            if extracted:
                tables.extend(extracted)

    header = None
    data_rows = []
    found_header = False

    for table in tables:
        for row in table:
            if row is None:
                continue
            cells = [(cell or '') for cell in row]
            if any(kw in cell for cell in cells for kw in SKIP_KEYWORDS):
                continue
            if 'S.No' in cells:
                found_header = True
                header = [c.strip() for c in cells]
                continue
            if found_header:
                row_data = [c.strip() for c in cells]
                if header and len(row_data) < len(header):
                    row_data.extend([''] * (len(header) - len(row_data)))
                if any(c.startswith('( Page No :') for c in row_data):
                    continue
                data_rows.append(row_data)

    if header is None or not data_rows:
        return []

    col_indices = {}
    for col in COLUMNS:
        try:
            col_indices[col] = header.index(col)
        except ValueError:
            col_indices[col] = None

    result = []
    for row in data_rows:
        record = {}
        for col in COLUMNS:
            idx = col_indices.get(col)
            record[col] = row[idx] if (idx is not None and idx < len(row)) else ''
        result.append(record)
    return result


def make_bg(widget, color):
    with widget.canvas.before:
        widget._c = Color(*color)
        widget._r = Rectangle(pos=widget.pos, size=widget.size)
    def _upd(inst, val):
        inst._r.pos = inst.pos
        inst._r.size = inst.size
    widget.bind(pos=_upd, size=_upd)


def make_btn(text, bg, cb, font_size=None, height=None, width=None):
    btn = Button(
        text=text, font_size=font_size or sp(14), bold=True,
        background_color=(0, 0, 0, 0), background_normal='', color=C_TEXT,
    )
    if height:
        btn.size_hint_y = None
        btn.height = height
    if width:
        btn.size_hint_x = None
        btn.width = width
    make_bg(btn, bg)
    btn.bind(on_press=lambda x: cb())
    return btn


class PinScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='pin', **kw)
        make_bg(self, C_BG)
        root = BoxLayout(orientation='vertical', padding=dp(40), spacing=dp(16))
        root.add_widget(Label(text='🔐', font_size=sp(64), size_hint_y=None, height=dp(90)))
        root.add_widget(Label(text='Insurance PDF Viewer', font_size=sp(22), bold=True,
                              color=C_GREEN, size_hint_y=None, height=dp(45)))
        root.add_widget(Label(text='Enter PIN to continue', font_size=sp(13),
                              color=C_MUTED, size_hint_y=None, height=dp(28)))
        card = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12),
                         size_hint_y=None, height=dp(190))
        make_bg(card, C_CARD)
        self.pin_input = TextInput(
            hint_text='● ● ● ●', password=True, multiline=False,
            input_filter='int', font_size=sp(28),
            size_hint_y=None, height=dp(60), padding=[dp(16), dp(14)],
            background_color=(0.06, 0.06, 0.10, 1),
            foreground_color=C_TEXT, cursor_color=C_GREEN, hint_text_color=C_MUTED,
        )
        self.pin_input.bind(on_text_validate=lambda *a: self.check_pin())
        card.add_widget(self.pin_input)
        self.err = Label(text='', color=C_ERROR, font_size=sp(13),
                         size_hint_y=None, height=dp(24))
        card.add_widget(self.err)
        card.add_widget(make_btn('UNLOCK  🔓', C_GREEN_DARK, self.check_pin,
                                 font_size=sp(15), height=dp(48)))
        root.add_widget(card)
        root.add_widget(Label(text='Branch: 85E / 189-SUTHARVAS  •  v1.0',
                              font_size=sp(10), color=C_MUTED,
                              size_hint_y=None, height=dp(24)))
        root.add_widget(Label())
        self.add_widget(root)

    def check_pin(self):
        if self.pin_input.text.strip() == CORRECT_PIN:
            self.manager.current = 'main'
            self.pin_input.text = ''
            self.err.text = ''
        else:
            self.err.text = '❌  Incorrect PIN. Try again.'
            self.pin_input.text = ''


class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='main', **kw)
        self.selected_pdf = None
        make_bg(self, C_BG)
        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        # Top bar
        bar = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        make_bg(bar, C_CARD)
        bar.add_widget(Label(text='📋  Insurance PDF Viewer', font_size=sp(17),
                             bold=True, color=C_GREEN, halign='left', valign='middle'))
        bar.add_widget(make_btn('🔒 Lock', (0.2, 0.2, 0.3, 1), self._lock,
                                width=dp(80), height=dp(36), font_size=sp(12)))
        root.add_widget(bar)

        # Action row
        act = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        act.add_widget(make_btn('📂  Select PDF', C_GREEN_DARK, self.pick_file))
        act.add_widget(make_btn('⚙️  Process', C_BLUE, self.process_pdf))
        root.add_widget(act)

        self.file_lbl = Label(text='No PDF selected.', font_size=sp(11), color=C_MUTED,
                              size_hint_y=None, height=dp(22), halign='left', valign='middle')
        self.file_lbl.bind(size=self.file_lbl.setter('text_size'))
        root.add_widget(self.file_lbl)

        self.status_lbl = Label(text='Tap  📂 Select PDF  to start.',
                                font_size=sp(13), color=(0.75, 0.75, 0.8, 1),
                                size_hint_y=None, height=dp(26), halign='left', valign='middle')
        self.status_lbl.bind(size=self.status_lbl.setter('text_size'))
        root.add_widget(self.status_lbl)

        self.scroll = ScrollView(do_scroll_x=True, do_scroll_y=True)
        self.table = GridLayout(cols=6, size_hint=(None, None), spacing=dp(1))
        self.table.bind(minimum_size=self.table.setter('size'))
        self.scroll.add_widget(self.table)
        root.add_widget(self.scroll)
        self.add_widget(root)
        self._draw_header()

    def _draw_header(self):
        self.table.clear_widgets()
        for h, w in zip(COLUMNS + ['WhatsApp'], COL_WIDTHS + [SHARE_COL_WIDTH]):
            lbl = Label(text=h, font_size=sp(12), bold=True, color=(1, 1, 1, 1),
                        size_hint=(None, None), width=w, height=dp(40),
                        halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            make_bg(lbl, C_HEADER)
            self.table.add_widget(lbl)

    def _lock(self):
        self.manager.current = 'pin'

    def _set_status(self, text, color=None):
        def _u(dt):
            self.status_lbl.text = text
            if color:
                self.status_lbl.color = color
        Clock.schedule_once(_u)

    def pick_file(self):
        if IS_ANDROID:
            request_permissions([Permission.READ_EXTERNAL_STORAGE,
                                  Permission.WRITE_EXTERNAL_STORAGE],
                                 lambda p, g: self._open_picker())
        else:
            self._open_picker()

    def _open_picker(self):
        try:
            from plyer import filechooser
            filechooser.open_file(
                title='Select PDF File',
                filters=[('PDF Files', '*.pdf'), ('All files', '*.*')],
                on_selection=self._on_file_selected,
            )
        except Exception as e:
            self._set_status(f'⚠️ File picker error: {e}', C_ERROR)

    def _on_file_selected(self, selection):
        if not selection:
            return
        self.selected_pdf = selection[0]
        def _u(dt):
            name = os.path.basename(self.selected_pdf) \
                if not self.selected_pdf.startswith('content://') else 'selected file'
            self.file_lbl.text = f'📄  {name}'
            self.status_lbl.text = 'PDF selected. Tap  ⚙️ Process  to extract data.'
            self.status_lbl.color = C_TEXT
        Clock.schedule_once(_u)

    def process_pdf(self):
        if not self.selected_pdf:
            self._set_status('⚠️  Please select a PDF file first.', C_ERROR)
            return
        self._set_status('⏳  Processing PDF — please wait…', C_GREEN)
        threading.Thread(target=self._bg_process, daemon=True).start()

    def _bg_process(self):
        try:
            real_path = _resolve_content_uri(self.selected_pdf)
            if not real_path or not os.path.exists(real_path):
                self._set_status('❌  File not found. Please re-select.', C_ERROR)
                return
            data = parse_pdf(real_path)
            def _done(dt):
                if not data:
                    self.status_lbl.text = '⚠️  No matching data found in this PDF.'
                    self.status_lbl.color = C_ERROR
                    return
                self._draw_header()
                for i, row in enumerate(data):
                    bg = C_ROW_ODD if i % 2 == 0 else C_ROW_EVEN
                    for col, w in zip(COLUMNS, COL_WIDTHS):
                        lbl = Label(text=str(row.get(col, '')), font_size=sp(11),
                                    color=C_TEXT, size_hint=(None, None),
                                    width=w, height=dp(40), halign='center', valign='middle')
                        lbl.bind(size=lbl.setter('text_size'))
                        make_bg(lbl, bg)
                        self.table.add_widget(lbl)
                    btn = Button(text='📤', font_size=sp(18),
                                 size_hint=(None, None), width=SHARE_COL_WIDTH, height=dp(40),
                                 background_color=C_ACCENT, background_normal='', color=C_TEXT)
                    btn.bind(on_press=lambda x, r=row: self._share(r))
                    self.table.add_widget(btn)
                self.status_lbl.text = f'✅  {len(data)} records extracted.'
                self.status_lbl.color = C_GREEN
            Clock.schedule_once(_done)
        except Exception as e:
            self._set_status(f'❌  Error: {e}', C_ERROR)

    def _share(self, row):
        msg = (f"Policy No: {row.get('PolicyNo', '')}\n"
               f"Name of Assured: {row.get('Name of Assured', '')}\n"
               f"D.o.C: {row.get('D.o.C', '')}\n"
               f"TotPrem: {row.get('TotPrem', '')}")
        webbrowser.open('https://wa.me/?text=' + quote(msg))


class InsurancePDFApp(App):
    def build(self):
        Window.clearcolor = C_BG
        self.title = 'Insurance PDF Viewer'
        sm = ScreenManager(transition=FadeTransition(duration=0.25))
        sm.add_widget(PinScreen())
        sm.add_widget(MainScreen())
        return sm


if __name__ == '__main__':
    InsurancePDFApp().run()
