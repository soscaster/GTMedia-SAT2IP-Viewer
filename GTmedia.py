import tkinter as tk
from tkinter import messagebox
import requests
import json
import pyperclip
import os
import sys
import vlc
import time

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GTmedia SAT2IP Services")
        self.geometry("1300x600")
        self.minsize(width=1300, height=600)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.iconbitmap(resource_path("favicon.ico"))
        self.wm_iconbitmap(resource_path("favicon.ico"))

        self.ip_label = tk.Label(self, text="Enter IP Address:", font=("TkDefaultFont", 12, "normal"))
        self.ip_label.pack(pady=5)
        
        self.ip_frame = tk.Frame(self)
        self.ip_frame.pack(pady=5)

        vcmd = (self.register(self.validate_ip), '%P')

        self.ip_entry1 = tk.Entry(self.ip_frame, width=3, validate='key', vcmd=vcmd)
        self.ip_entry2 = tk.Entry(self.ip_frame, width=3, validate='key', vcmd=vcmd)
        self.ip_entry3 = tk.Entry(self.ip_frame, width=3, validate='key', vcmd=vcmd)
        self.ip_entry4 = tk.Entry(self.ip_frame, width=3, validate='key', vcmd=vcmd)

        self.ip_entry1.insert(0, '192')
        self.ip_entry2.insert(0, '168')

        self.ip_entry1.pack(side="left")
        tk.Label(self.ip_frame, text=".").pack(side="left")
        self.ip_entry2.pack(side="left")
        tk.Label(self.ip_frame, text=".").pack(side="left")
        self.ip_entry3.pack(side="left")
        tk.Label(self.ip_frame, text=".").pack(side="left")
        self.ip_entry4.pack(side="left")

        self.ip_entry1.bind('<KeyRelease>', lambda e: self.next_entry(e, self.ip_entry1, self.ip_entry2))
        self.ip_entry2.bind('<KeyRelease>', lambda e: self.next_entry(e, self.ip_entry2, self.ip_entry3))
        self.ip_entry3.bind('<KeyRelease>', lambda e: self.next_entry(e, self.ip_entry3, self.ip_entry4))
        self.ip_entry4.bind('<KeyRelease>', lambda e: self.next_entry(e, self.ip_entry4, None))

        self.get_button = tk.Button(self, text="Get Services", command=self.get_services)
        self.get_button.pack(pady=5)

        self.main_frame = tk.Frame(self)
        self.main_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.services_frame = tk.Frame(self.main_frame)
        self.services_frame.pack(side="left", fill=tk.BOTH, expand=False)

        self.canvas = tk.Canvas(self.services_frame, width=200)
        self.scrollbar_y = tk.Scrollbar(self.services_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar_y.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # Linux specific
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # Linux specific

        self.player_frame = tk.Frame(self.main_frame, width=800, height=600, bg="black")
        self.player_frame.pack(side="right", padx=10, pady=10)
        
        self.description_frame = tk.Frame(self.main_frame)
        self.description_frame.pack(side="right", fill=tk.BOTH, expand=True)
        self.fullscreen_button = tk.Button(self.description_frame, text="Toggle Fullscreen", command=self.toggle_fullscreen)
        self.fullscreen_button.pack(pady=5)
        
        self.info_labels = {}
        for info in ["Service Name", "Satellite Name", "Frequency", "PID", "Signal Intensity", "Signal Quality", "Receive Rate", "Send Rate"]:
            tk.Label(self.description_frame, text=info + ":", anchor="w", font=("TkDefaultFont", 12, "normal")).pack(fill=tk.X, padx=10, pady=2)
            self.info_labels[info] = tk.Label(self.description_frame, text="", anchor="w", bg="white", font=("TkDefaultFont", 12, "normal"))
            self.info_labels[info].pack(fill=tk.X, padx=10, pady=2)

        self.selected_label = None

        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()

        # Delay setting the window ID to ensure the frame is fully initialized
        self.after(100, self.initialize_vlc_player)

    def initialize_vlc_player(self):
        window_id = self.player_frame.winfo_id()
        self.vlc_player.set_hwnd(window_id)
        print(f"Window ID: {window_id}")

    def validate_ip(self, P):
        if P.isdigit() and len(P) <= 3:
            return True
        elif P == "":
            return True
        else:
            return False

    def next_entry(self, event, current_entry, next_entry):
        if len(current_entry.get()) == 3:
            if next_entry:
                next_entry.focus_set()

    def get_ip_address(self):
        ip1 = self.ip_entry1.get().strip()
        ip2 = self.ip_entry2.get().strip()
        ip3 = self.ip_entry3.get().strip()
        ip4 = self.ip_entry4.get().strip()
        if all(ip.isdigit() and 0 <= int(ip) <= 255 for ip in [ip1, ip2, ip3, ip4]):
            return f"{ip1}.{ip2}.{ip3}.{ip4}"
        else:
            return None

    def get_services(self):
        ip_address = self.get_ip_address()
        if not ip_address:
            messagebox.showerror("Error", "Please enter a valid IP address.")
            return

        url = f"http://{ip_address}:81/getallservices"
        count = 100

        while True:
            full_url = f"{url}?count={count}"
            try:
                response = requests.get(full_url)
                response.raise_for_status()
                data = response.json()
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                messagebox.showerror("Error", f"Failed to fetch services: {e}")
                return

            if "pagetotal" not in data or "services" not in data:
                messagebox.showerror("Error", "Invalid response format.")
                return

            if data["pagetotal"] <= 1:
                break
            count += 100

        self.display_services(data["services"])

    def display_services(self, services):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        for service in services:
            service_name = service["servicename"]
            service_id = service["id"]
            label = tk.Label(self.scrollable_frame, text=service_name, fg="black" if not service_name.startswith('$') else "red", cursor="hand2", font=("TkDefaultFont", 12, "normal"))
            label.pack(anchor="w", padx=10, pady=2)
            label.bind("<Button-1>", lambda e, service_id=service_id, label=label: self.show_service_info(service_id, label))
            label.bind("<Double-Button-1>", lambda e, url=service["url"]: self.play_stream(url))

        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def show_service_info(self, service_id, label):
        if self.selected_label:
            self.selected_label.configure(bg=self.cget("bg"), font=("TkDefaultFont", 12, "normal"))
        label.configure(bg="lightblue", font=("TkDefaultFont", 15, "bold"))
        self.selected_label = label

        ip_address = self.get_ip_address()
        if not ip_address:
            messagebox.showerror("Error", "Please enter a valid IP address.")
            return

        url = f"http://{ip_address}:81/proginfo?id={service_id}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            messagebox.showerror("Error", f"Failed to fetch service info: {e}")
            return

        required_keys = {"servicename", "satname", "FQ", "PID", "intensity", "quality", "rev_rate", "send_rate"}
        if not all(key in data for key in required_keys):
            messagebox.showerror("Error", "Invalid response format.")
            return

        service_info = {
            "Service Name": data['servicename'],
            "Satellite Name": data['satname'],
            "Frequency": data['FQ'],
            "PID": data['PID'],
            "Signal Intensity": data['intensity'],
            "Signal Quality": data['quality'],
            "Receive Rate": data['rev_rate'],
            "Send Rate": data['send_rate']
        }

        for key, value in service_info.items():
            self.info_labels[key].configure(text=value)

    def set_deinterlace_mode(self, mode):
        self.vlc_player.video_set_deinterlace(mode.encode('utf-8'))

    def play_stream(self, url):
        media = self.vlc_instance.media_new(url)
        self.vlc_player.set_media(media)
        self.vlc_player.play()
        self.set_deinterlace_mode('linear')

    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(-1*(event.delta//120), "units")
        elif event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    def copy_to_clipboard(self, url):
        pyperclip.copy(url)
        messagebox.showinfo("Copied", f"URL copied to clipboard:\n{url}")

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            messagebox.showinfo("Goodbye", "Thank you for using this app!\nWritten by: soscaster")
            self.destroy()

    def toggle_fullscreen(self):
        is_fullscreen = self.vlc_player.get_fullscreen()
        self.vlc_player.set_fullscreen(not is_fullscreen)
        print(f"Fullscreen mode set to: {not is_fullscreen}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
