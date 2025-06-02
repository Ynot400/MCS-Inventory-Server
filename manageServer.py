import tkinter as tk
from tkinter import simpledialog
from tkinter import ttk
import subprocess
import threading

PASSWORD = "MYpassword1"

class ServerControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Server Control")
        self.root.geometry("400x250")
        self.root.configure(bg="#f5f5f5")

        # Fonts
        button_font = ("Helvetica", 12, "bold")
        label_font = ("Helvetica", 11)

        # Create and configure custom styles
        style = ttk.Style()
        style.theme_use("default")

        style.configure("Start.TButton",
                        font=button_font,
                        foreground="white",
                        background="#28a745",
                        padding=10)
        style.map("Start.TButton",
                  background=[("active", "#218838"), ("disabled", "#a5d6a7")])

        style.configure("Stop.TButton",
                        font=button_font,
                        foreground="white",
                        background="#dc3545",
                        padding=10)
        style.map("Stop.TButton",
                  background=[("active", "#c82333"), ("disabled", "#ef9a9a")])

        # Buttons
        self.start_button = ttk.Button(self.root, text="Start Server", command=self.start_server, style="Start.TButton")
        self.start_button.pack(pady=(30, 10), ipadx=10, ipady=10)

        self.stop_button = ttk.Button(self.root, text="Stop Server", command=self.stop_server, style="Stop.TButton")
        self.stop_button.pack(pady=10, ipadx=10, ipady=10)

        # Labels
        self.status_label = tk.Label(self.root, text="Server Status: Unknown", fg="red", bg="#f5f5f5", font=label_font)
        self.status_label.pack(pady=10)

        self.feedback_label = tk.Label(self.root, text="", fg="blue", bg="#f5f5f5", font=label_font)
        self.feedback_label.pack(pady=10)

    def show_feedback(self, message):
        self.feedback_label.config(text=message)
        self.root.update_idletasks()

    def reset_feedback(self):
        self.root.after(2000, lambda: self.feedback_label.config(text=""))

    def run_in_thread(self, command, success_message, failure_message, is_start):
        def task():
            self.show_feedback(success_message)
            self.start_button.state(["disabled"])
            self.stop_button.state(["disabled"])
            try:
                subprocess.run(command, check=True)
                self.show_feedback(success_message)
                self.status_label.config(
                    text=f"Server Status: {'Running' if is_start else 'Stopped'}",
                    fg="green" if is_start else "red"
                )
            except subprocess.CalledProcessError:
                self.show_feedback(failure_message)
                self.status_label.config(text="Server Status: Error", fg="orange")
            finally:
                self.start_button.state(["!disabled"])
                self.stop_button.state(["!disabled"])
                self.reset_feedback()

        threading.Thread(target=task, daemon=True).start()

    def start_server(self):
        self.run_in_thread(
            ["supervisorctl", "start", "mcsServer"],
            success_message="Starting the server...",
            failure_message="Failed to start the server.",
            is_start=True
        )

    def stop_server(self):
        self.run_in_thread(
            ["supervisorctl", "stop", "mcsServer"],
            success_message="Stopping the server...",
            failure_message="Failed to stop the server.",
            is_start=False
        )

def check_password():
    root = tk.Tk()
    root.withdraw()
    user_password = simpledialog.askstring("Password Required", "Enter the password:", show="*")
    root.destroy()
    return user_password == PASSWORD

if __name__ == "__main__":
    if check_password():
        root = tk.Tk()
        app = ServerControlApp(root)
        root.mainloop()
    else:
        pass
        # print("Incorrect password. Exiting.")
        
