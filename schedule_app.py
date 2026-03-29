# schedule_app.py

import threading
import time
import smtplib
import json
import os
from email.mime.text import MIMEText
from datetime import datetime

import pytz # type: ignore
from kivy.lang import Builder # type: ignore
from kivy.clock import Clock # type: ignore
from kivy.core.audio import SoundLoader  # type: ignore # 🔊 NEW
import kivymd.app # type: ignore
from kivymd.uix.list import OneLineListItem # type: ignore
from kivymd.uix.dialog import MDDialog # type: ignore
from kivymd.uix.menu import MDDropdownMenu # type: ignore
from kivymd.uix.button import MDFlatButton # type: ignore

# ================= EMAIL CONFIG =================
EMAIL_SENDER = "jonatanumpingbiwang@gmail.com"
EMAIL_PASSWORD = "gcto pqve bupk hwpt"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

DATA_FILE = "data.json"

# 🔊 Load sound
alarm_sound = SoundLoader.load("alarm.mp3")

# ================= UI =================
KV = '''
Screen:
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Class Schedule"
            elevation: 4

        MDBoxLayout:
            orientation: "vertical"
            padding: 10
            spacing: 10

            MDTextField:
                id: email_input
                hint_text: "Enter Your Email"

            MDBoxLayout:
                orientation: "horizontal"
                spacing: 10
                size_hint_y: None
                height: "50dp"

                MDRaisedButton:
                    text: "Save Email"
                    on_release: app.save_email()

                MDRaisedButton:
                    text: "View Email"
                    on_release: app.view_email()

            MDTextField:
                id: subject
                hint_text: "Subject"

            MDTextField:
                id: hour_input
                hint_text: "Hour (1-12)"
                readonly: True
                on_focus:
                    if self.focus: app.open_hour_menu(self)

            MDTextField:
                id: minute_input
                hint_text: "Minute (00-59)"
                readonly: True
                on_focus:
                    if self.focus: app.open_minute_menu(self)

            MDTextField:
                id: ampm_input
                hint_text: "AM / PM"
                readonly: True
                on_focus:
                    if self.focus: app.open_ampm_menu(self)

            MDTextField:
                id: day_input
                hint_text: "Select Day"
                readonly: True
                on_focus:
                    if self.focus: app.open_day_menu(self)

            MDRaisedButton:
                text: "Add / Update Schedule"
                pos_hint: {"center_x": 0.5}
                on_release: app.add_schedule()

            ScrollView:
                MDList:
                    id: schedule_list

        MDFloatingActionButton:
            icon: "delete"
            pos_hint: {"center_x": 0.9, "center_y": 0.1}
            on_release: app.delete_last_schedule()
'''

class ScheduleApp(kivymd.app.MDApp):
    def build(self):
        self.schedules = []
        self.menu = None
        self.saved_email = None
        self.sent_flags = set()
        self.editing_index = None

        self.load_data()

        self.root = Builder.load_string(KV)

        Clock.schedule_once(lambda dt: self.refresh_list())

        threading.Thread(target=self.check_schedule, daemon=True).start()

        return self.root

    # ================= DATA =================
    def save_data(self):
        data = {
            "email": self.saved_email,
            "schedules": self.schedules
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                self.saved_email = data.get("email")
                self.schedules = data.get("schedules", [])

    # ================= EMAIL =================
    def save_email(self):
        email = self.root.ids.email_input.text
        if email:
            self.saved_email = email
            self.save_data()
            self.show_dialog("Email saved!")
        else:
            self.show_dialog("Enter email!")

    def view_email(self):
        self.show_dialog(self.saved_email if self.saved_email else "No email saved")

    def send_email(self, subject, schedule_time):
        try:
            if not self.saved_email:
                return

            msg = MIMEText(f"Reminder: {subject} at {schedule_time}")
            msg["Subject"] = "Class Schedule Reminder"
            msg["From"] = EMAIL_SENDER
            msg["To"] = self.saved_email

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, self.saved_email, msg.as_string())
            server.quit()

            print("Email sent successfully!")

        except Exception as e:
            print("EMAIL ERROR:", e)

    # 🔔 POPUP + 🔊 SOUND
    def trigger_alert(self, subject, time_part):
        # Popup
        Clock.schedule_once(lambda dt: self.show_dialog(f"{subject} is starting now!"))

        # Sound
        if alarm_sound:
            alarm_sound.play()

    # ================= TIME CHECK =================
    def check_schedule(self):
        philippines = pytz.timezone("Asia/Manila")

        while True:
            now = datetime.now(philippines)

            current_hour = now.hour
            current_minute = now.minute
            current_day = now.strftime("%A")

            print(f"Now (PH): {now.strftime('%I:%M %p')} {current_day}")

            for item in list(self.schedules):
                parts = item.split("|")

                if len(parts) >= 3:
                    subject = parts[0].strip()
                    time_part = parts[1].strip()
                    day_part = parts[2].strip()

                    key = f"{subject}-{time_part}-{day_part}-{now.strftime('%Y-%m-%d')}"

                    try:
                        sched_time = datetime.strptime(time_part, "%I:%M %p")

                        if (
                            sched_time.hour == current_hour and
                            sched_time.minute == current_minute and
                            day_part == current_day
                        ):
                            if key not in self.sent_flags:
                                print("MATCH FOUND:", subject)

                                self.send_email(subject, time_part)
                                self.trigger_alert(subject, time_part)  # 🔥 NEW

                                self.sent_flags.add(key)

                    except Exception as e:
                        print("Time Parse Error:", e)

            time.sleep(5)

    # ================= UI LIST =================
    def refresh_list(self):
        if not self.root:
            return

        schedule_list = self.root.ids.schedule_list
        schedule_list.clear_widgets()

        for i, item in enumerate(self.schedules):
            schedule_list.add_widget(
                OneLineListItem(
                    text=item,
                    on_release=lambda x=item, idx=i: self.open_item_dialog(idx)
                )
            )

    # ================= MENU =================
    def open_menu(self, caller, items, setter):
        menu_items = [
            {
                "text": str(i),
                "viewclass": "OneLineListItem",
                "on_release": lambda x=i: setter(x),
            }
            for i in items
        ]
        self.menu = MDDropdownMenu(caller=caller, items=menu_items, width_mult=3)
        self.menu.open()

    def open_hour_menu(self, caller):
        self.open_menu(caller, list(range(1, 13)), self.set_hour)

    def open_minute_menu(self, caller):
        self.open_menu(caller, [f"{i:02d}" for i in range(60)], self.set_minute)

    def open_ampm_menu(self, caller):
        self.open_menu(caller, ["AM", "PM"], self.set_ampm)

    def open_day_menu(self, caller):
        self.open_menu(caller, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], self.set_day)

    def set_hour(self, v):
        self.root.ids.hour_input.text = str(v)
        self.menu.dismiss()

    def set_minute(self, v):
        self.root.ids.minute_input.text = str(v)
        self.menu.dismiss()

    def set_ampm(self, v):
        self.root.ids.ampm_input.text = v
        self.menu.dismiss()

    def set_day(self, v):
        self.root.ids.day_input.text = v
        self.menu.dismiss()

    # ================= ADD / EDIT =================
    def add_schedule(self):
        subject = self.root.ids.subject.text
        hour = self.root.ids.hour_input.text
        minute = self.root.ids.minute_input.text
        ampm = self.root.ids.ampm_input.text
        day = self.root.ids.day_input.text

        if subject and hour and minute and ampm and day:
            time_str = f"{hour}:{minute} {ampm}"
            item = f"{subject} | {time_str} | {day}"

            if self.editing_index is not None:
                self.schedules[self.editing_index] = item
                self.editing_index = None
            else:
                self.schedules.append(item)

            self.save_data()
            self.refresh_list()
            self.clear_inputs()
        else:
            self.show_dialog("Fill all fields!")

    def clear_inputs(self):
        ids = self.root.ids
        ids.subject.text = ""
        ids.hour_input.text = ""
        ids.minute_input.text = ""
        ids.ampm_input.text = ""
        ids.day_input.text = ""

    def delete_last_schedule(self):
        if self.schedules:
            self.schedules.pop()
            self.save_data()
            self.refresh_list()

    # ================= ITEM ACTION =================
    def open_item_dialog(self, index):
        item = self.schedules[index]

        dialog = MDDialog(
            text=item,
            buttons=[
                self.create_button("Edit", lambda x: self.edit_schedule(index, dialog)),
                self.create_button("Delete", lambda x: self.delete_schedule(index, dialog)),
            ],
        )
        dialog.open()

    def create_button(self, text, callback):
        return MDFlatButton(text=text, on_release=callback)

    def edit_schedule(self, index, dialog):
        item = self.schedules[index]
        subject, time_part, day = [x.strip() for x in item.split("|")]

        hour, rest = time_part.split(":")
        minute, ampm = rest.split(" ")

        self.root.ids.subject.text = subject
        self.root.ids.hour_input.text = hour
        self.root.ids.minute_input.text = minute
        self.root.ids.ampm_input.text = ampm
        self.root.ids.day_input.text = day

        self.editing_index = index
        dialog.dismiss()

    def delete_schedule(self, index, dialog):
        self.schedules.pop(index)
        self.save_data()
        self.refresh_list()
        dialog.dismiss()

    def show_dialog(self, message):
        MDDialog(text=message).open()

# ================= RUN =================
if __name__ == "__main__":
    ScheduleApp().run()