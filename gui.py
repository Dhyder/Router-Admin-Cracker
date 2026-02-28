#!/usr/bin/env python3
"""
Simple Tkinter GUI for Router Cracker — friendly, slightly witty, and practical.

Features:
- Prompt for router URL, username, and choose a wordlist (or use the included wordlists/universal.txt)
- Optionally enter remembered "old" passwords; the GUI can combine them with universal entries
- Start/stop controls, live log output

Warning: this GUI runs the cracking routine in a background thread. Only test devices you own.
"""
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tempfile
import os
import logging
import random
import time
from cracker import crack_router


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert('end', msg + '\n')
            self.text_widget.see('end')
            self.text_widget.configure(state='disabled')
        self.text_widget.after(0, append)


class CrackerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Router Cracker — Friendly Edition')
        self.geometry('800x520')

        self.router_url = tk.StringVar(value='http://192.168.0.1')
        self.username = tk.StringVar(value='admin')
        self.wordlist = tk.StringVar(value='wordlists/universal.txt')
        self.delay = tk.DoubleVar(value=0.0)
        self.timeout = tk.DoubleVar(value=10.0)
        self.max_combos = tk.IntVar(value=50000)
        self.failed_log = tk.StringVar(value='failed_attempts.txt')

        self._build()
        self._worker = None
        self._gus = None
        self._gus_running = False

    def _build(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill='both', expand=True)

        left = ttk.Frame(frm)
        left.pack(side='left', fill='y')

        ttk.Label(left, text='Router URL').pack(anchor='w')
        ttk.Entry(left, textvariable=self.router_url, width=30).pack()

        ttk.Label(left, text='Username').pack(anchor='w', pady=(6,0))
        ttk.Entry(left, textvariable=self.username, width=30).pack()

        ttk.Label(left, text='Wordlist').pack(anchor='w', pady=(6,0))
        wbox = ttk.Frame(left)
        wbox.pack()
        ttk.Entry(wbox, textvariable=self.wordlist, width=28).pack(side='left')
        ttk.Button(wbox, text='Browse', command=self.browse_wordlist).pack(side='left', padx=4)

        ttk.Label(left, text='Remembered/old passwords (one per line)').pack(anchor='w', pady=(8,0))
        self.old_text = tk.Text(left, height=6, width=30)
        self.old_text.pack()

        ttk.Label(left, text='Delay (s)').pack(anchor='w', pady=(6,0))
        ttk.Entry(left, textvariable=self.delay, width=10).pack()
        ttk.Label(left, text='Max combos').pack(anchor='w', pady=(6,0))
        ttk.Entry(left, textvariable=self.max_combos, width=12).pack()
        ttk.Label(left, text='Timeout (s)').pack(anchor='w', pady=(6,0))
        ttk.Entry(left, textvariable=self.timeout, width=10).pack()

        ttk.Label(left, text='Failed log path').pack(anchor='w', pady=(6,0))
        ttk.Entry(left, textvariable=self.failed_log, width=30).pack()

        btns = ttk.Frame(left)
        btns.pack(pady=8)
        ttk.Button(btns, text='Start', command=self.start).pack(side='left', padx=6)
        ttk.Button(btns, text='Stop', command=self.stop).pack(side='left', padx=6)
        ttk.Button(btns, text='Combine + Save', command=self.combine_and_save).pack(side='left', padx=6)

        right = ttk.Frame(frm)
        right.pack(side='right', fill='both', expand=True)

        # Gus assistant area
        gus_frame = ttk.Frame(right)
        gus_frame.pack(fill='x')
        self.gus_emote = tk.StringVar(value='😎')
        self.gus_name = ttk.Label(gus_frame, text='Gus', font=('TkDefaultFont', 10, 'bold'))
        self.gus_name.pack(side='left')
        self.gus_face = ttk.Label(gus_frame, textvariable=self.gus_emote, font=('TkDefaultFont', 12))
        self.gus_face.pack(side='left', padx=6)

        ttk.Label(right, text='Live log').pack(anchor='w')
        self.log_text = tk.Text(right, state='disabled')
        self.log_text.pack(fill='both', expand=True)

        # configure logging
        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def browse_wordlist(self):
        p = filedialog.askopenfilename(title='Choose wordlist', filetypes=[('Text files', '*.txt'), ('All files', '*.*')])
        if p:
            self.wordlist.set(p)

    def combine_and_save(self):
        # Combine universal and remembered into a temp wordlist
        remembered = [line.strip() for line in self.old_text.get('1.0', 'end').splitlines() if line.strip()]
        if not remembered:
            messagebox.showinfo('Combine', 'No remembered entries to combine.')
            return

        # Load universal list (if exists) otherwise use current wordlist
        base_list = []
        try:
            with open(self.wordlist.get(), 'r', encoding='utf-8') as f:
                base_list = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        except Exception:
            base_list = []

        # smarter combinator: combine with separators, suffixes, and years
        combos = set()
        separators = ['', '_', '-', '.', '']
        suffixes = ['123', '!', '01', '99']
        years = [str(y) for y in range(1999, 2026)]

        max_combos = int(self.max_combos.get() or 50000)
        for r in remembered:
            combos.add(r)
            # small mutations of remembered
            for s in suffixes:
                combos.add(r + s)
            for y in years[-5:]:
                combos.add(r + y)

            for b in base_list:
                combos.add(b)
                # direct concatenations
                combos.add(r + b)
                combos.add(b + r)
                # with separators
                for sep in separators:
                    combos.add(r + sep + b)
                    combos.add(b + sep + r)
                # remembered variants
                for s in suffixes:
                    combos.add(r + s + b)
                    combos.add(b + s + r)

            # cap explosion
            if len(combos) > max_combos:
                logging.warning('Combination exceeded %d entries; truncating', max_combos)
                break

        # save to temp file in project dir
        out = os.path.join(os.getcwd(), 'combined_wordlist.txt')
        with open(out, 'w', encoding='utf-8') as f:
            for c in sorted(combos):
                f.write(c + '\n')

        messagebox.showinfo('Combine', f'Combined {len(combos)} candidates to {out}')
        self.wordlist.set(out)

    # Chat helpers for Gus
    def send_chat(self):
        text = None
        try:
            text = self.chat_entry.get().strip()
        except Exception:
            # If chat_entry isn't present (older GUI), ignore
            return
        if not text:
            return
        # show user message
        logging.info('You: %s', text)
        try:
            self.chat_entry.delete(0, 'end')
        except Exception:
            pass
        # schedule Gus response shortly
        self.after(600, lambda: self._gus_reply(text))

    def _gus_reply(self, text):
        resp = self._respond_to_user(text)
        # ASCII Gus occasionally for flair
        if random.random() < 0.12:
            ascii_gus = (
                "  ____\n"
                " / ___| __ _ _ __ ___   ___\n"
                "| |  _ / _` | '_ ` _ \\ / _ \\\n"
                "| |_| | (_| | | | | | |  __/\n"
                " \\____|\\__,_|_| |_| |_|\\___|\n"
            )
            logging.info('Gus:\n%s', ascii_gus)
        logging.info('Gus: %s', resp)

    def _respond_to_user(self, text: str) -> str:
        t = text.lower()
        # heuristics explanation
        if any(k in t for k in ('heuristic', 'how', 'explain', 'detect')):
            return ("I check status codes (e.g., redirects), look for keywords in the response body (like 'dashboard' or 'index'), "
                    "and, if configured, specific headers. You can pass extra indicators with --success or --success-header.")
        if 'combine' in t or 'remember' in t or 'wordlist' in t:
            return ("Combine uses your remembered fragments + base entries. It makes concatenations, adds small suffixes like 123 or years, "
                    "and inserts simple separators. Try a few remembered fragments and press Combine+Save.")
        if 'joke' in t or 'funny' in t:
            return random.choice([
                "Why did the packet cross the LAN? To get to the other side!",
                "I would tell you a UDP joke, but you might not get it.",
                "Why do routers never gossip? They prefer to keep things on the down-link."
            ])
        if 'progress' in t or 'status' in t:
            return "Progress is estimated from the wordlist size; the GUI shows live logs. I can't interrupt network calls instantly — stopping is cooperative."
        # default playful reply
        return random.choice([
            "Nice question. Try asking me 'how do you detect success?' or 'how does combine work?'.",
            "Hmm... interesting. I suggest combining remembered fragments with the universal list and adding a small delay.",
            "I'm Gus. I like routers, jokes, and concise heuristics. Ask 'heuristic' to learn more."
        ])

    # Gus assistant methods
    def _start_gus(self):
        if self._gus_running:
            return
        self._gus_running = True
        self._gus = threading.Thread(target=self._gus_worker, daemon=True)
        self._gus.start()

    def _stop_gus(self):
        self._gus_running = False

    def _gus_worker(self):
        messages = [
            "I'm Gus — your friendly router whisperer.",
            "Fun fact: routers love predictable passwords. Don't be predictable.",
            "Tip: try adding a year or a number at the end — players do it all the time.",
            "Joke: Why did the packet cross the LAN? To get to the other side!",
            "If you remember a piece of the password, add it to 'Remembered' and press Combine.",
            "Loading... I mean, thinking. I'm thinking. Beep boop."
        ]
        while self._gus_running:
            msg = random.choice(messages)
            logging.info('Gus: %s', msg)
            # playful face change
            self.gus_emote.set(random.choice(['😎','🤖','🕵️','😺','🧠']))
            # sleep a bit while worker is running
            for _ in range(4):
                if not self._gus_running:
                    break
                time.sleep(1)

    def start(self):
        if self._worker and self._worker.is_alive():
            messagebox.showinfo('Already running', 'Crack in progress')
            return

        router_url = self.router_url.get()
        username = self.username.get()
        wordlist = self.wordlist.get()
        delay = float(self.delay.get())
        timeout = float(self.timeout.get())
        failed_log = self.failed_log.get()

        if not router_url or not username or not wordlist:
            messagebox.showerror('Missing', 'Fill router URL, username and wordlist')
            return

        def worker():
            logging.info('Starting cracking against %s with user %s', router_url, username)
            found = crack_router(router_url, username, wordlist, timeout=timeout, delay=delay, failed_log_file=failed_log)
            if found:
                logging.info('🎉 Found: %s', found)
            else:
                logging.info('No password found')

            # stop gus when done
            try:
                self._stop_gus()
            except Exception:
                pass
        self._worker = threading.Thread(target=worker, daemon=True)
        # start gus assistant
        self._start_gus()
        self._worker.start()

    def stop(self):
        # We can't forcefully stop requests easily; inform the user
        if self._worker and self._worker.is_alive():
            messagebox.showinfo('Stop', 'Stopping is cooperative: current request will finish then stop. To abort fully, close the GUI.')
        else:
            messagebox.showinfo('Stop', 'No active run')


def main():
    app = CrackerGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
