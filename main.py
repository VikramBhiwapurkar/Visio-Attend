import os.path
import datetime
import pickle
import subprocess

import tkinter as tk
import cv2
from PIL import Image, ImageTk
import face_recognition

import util
import csv
import itertools
import dlib


class App:
    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.geometry("1200x520+350+100")

        self.login_button_main_window = util.get_button(self.main_window, 'Mark Attendance', 'green', self.mark_attendence)
        self.login_button_main_window.place(x=750, y=200)

        self.register_new_user_button_main_window = util.get_button(self.main_window, 'Register new user', 'gray',
                                                                    self.register_new_user, fg='black')
        self.register_new_user_button_main_window.place(x=750, y=400)

        self.webcam_label = util.get_img_label(self.main_window)
        self.webcam_label.place(x=10, y=0, width=700, height=500)

        self.add_webcam(self.webcam_label)

        self.db_dir = './db'
        if not os.path.exists(self.db_dir):
            os.mkdir(self.db_dir)

        self.log_path = './log.csv'

        self.registered_users_path = './registered_users.csv'
        self.user_id_counter = self.load_registered_users()

    def load_registered_users(self):
        try:
            with open(self.registered_users_path, 'r') as csvfile:
                reader = csv.reader(csvfile)
                # Count the number of rows in the CSV file to get the last ID used
                num_registered_users = sum(1 for _ in reader)
                # Increment the counter to get the next available ID
                return itertools.count(start=num_registered_users + 1)
        except FileNotFoundError:
            # If the file doesn't exist, start the counter from 1
            return itertools.count(start=1)

    def add_webcam(self, label):
        if 'cap' not in self.__dict__:
            self.cap = cv2.VideoCapture(0)

        self._label = label
        self.process_webcam()

    def process_webcam(self):
        ret, frame = self.cap.read()

        self.most_recent_capture_arr = frame
        img_ = cv2.cvtColor(self.most_recent_capture_arr, cv2.COLOR_BGR2RGB)
        self.most_recent_capture_pil = Image.fromarray(img_)
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        self._label.imgtk = imgtk
        self._label.configure(image=imgtk)

        self._label.after(20, self.process_webcam)


    def mark_attendence(self):
        unknown_img_path = './.tmp.jpg'
        cv2.imwrite(unknown_img_path, self.most_recent_capture_arr)
        output = str(subprocess.check_output(['face_recognition', self.db_dir, unknown_img_path]))
        print(output)
        name = output.split(',')[1].split('\\')[0].strip()

        if name in ['unknown_person', 'no_persons_found']:
            util.msg_box('Ups...', 'Unknown user. Please register new user or try again.')
        else:
            # Search for the user's name in registered_users.csv
            user_id = None
            with open(self.registered_users_path, 'r') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row[1] == name:
                        user_id = row[0]
                        break

            if user_id is not None:
                # Check if the log file exists, create it if it doesn't
                if not os.path.exists(self.log_path):
                    with open(self.log_path, 'w') as log_file:
                        log_file.write('User_ID,Date\n')

                # Check if the user has already logged in on the current date
                date_today = datetime.datetime.now().strftime("%Y-%m-%d")
                with open(self.log_path, 'r') as f:
                    for line in f:
                        if line.strip().startswith(user_id) and date_today in line:
                            util.msg_box('Already Marked as Present', 'You are already marked as present today.')
                            break
                    else:
                        # If the user has not logged in today, write user ID and date into the log file
                        util.msg_box('Marked Present !', 'Good Day, {}.'.format(name))
                        with open(self.log_path, 'a') as f:
                            f.write('{},{}\n'.format(user_id, date_today))
            else:
                util.msg_box('Ups...', 'User not found in registered users. Please register as new user.')

        os.remove(unknown_img_path)

    def register_new_user(self):
        self.register_new_user_window = tk.Toplevel(self.main_window)
        self.register_new_user_window.geometry("1200x520+370+120")

        self.accept_button_register_new_user_window = util.get_button(self.register_new_user_window, 'Accept', 'green', self.accept_register_new_user)
        self.accept_button_register_new_user_window.place(x=750, y=300)

        self.try_again_button_register_new_user_window = util.get_button(self.register_new_user_window, 'Try again', 'red', self.try_again_register_new_user)
        self.try_again_button_register_new_user_window.place(x=750, y=400)

        self.capture_label = util.get_img_label(self.register_new_user_window)
        self.capture_label.place(x=10, y=0, width=700, height=500)

        self.add_img_to_label(self.capture_label)

        self.entry_text_register_new_user = util.get_entry_text(self.register_new_user_window)
        self.entry_text_register_new_user.place(x=750, y=150)

        self.text_label_register_new_user = util.get_text_label(self.register_new_user_window, 'Please, \ninput username:')
        self.text_label_register_new_user.place(x=750, y=70)

    def try_again_register_new_user(self):
        self.register_new_user_window.destroy()

    def add_img_to_label(self, label):
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        label.imgtk = imgtk
        label.configure(image=imgtk)

        self.register_new_user_capture = self.most_recent_capture_arr.copy()

    def start(self):
        self.main_window.mainloop()

    def accept_register_new_user(self):
        name = self.entry_text_register_new_user.get(1.0, "end-1c")

        # Check if the face already exists in the database
        if self.face_already_registered(self.register_new_user_capture):
            util.msg_box('Error!', 'This face is already registered.')
            self.register_new_user_window.destroy()
            return


        user_id = next(self.user_id_counter)
        image_filename = '{}.jpg'.format(name)
        image_path = os.path.join(self.db_dir, image_filename)
        cv2.imwrite(image_path, self.register_new_user_capture)
        util.msg_box('Success!', 'User was registered successfully!')


        with open(self.registered_users_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([user_id, name, image_path])

        self.register_new_user_window.destroy()

    def face_already_registered(self, new_face):
        new_face_encoding = face_recognition.face_encodings(new_face)[0]

        for _, _, image_path in self.get_registered_users():
            registered_face = face_recognition.load_image_file(image_path)
            registered_face_encoding = face_recognition.face_encodings(registered_face)[0]

            # Compare the face encodings
            if face_recognition.compare_faces([registered_face_encoding], new_face_encoding)[0]:
                return True

        return False

    def get_registered_users(self):
        registered_users = []
        with open(self.registered_users_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                registered_users.append((row[0], row[1], row[2]))
        return registered_users

if __name__ == "__main__":
    app = App()
    app.start()