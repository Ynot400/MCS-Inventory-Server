import tkinter as tk
from tkinter import simpledialog
import subprocess
import threading

# Set your predefined password
PASSWORD = "MYpassword1"

class ServerControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Server Control")

        # Add buttons for starting/stopping the server
        self.start_button = tk.Button(self.root, text="Start Server", command=self.start_server)
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(self.root, text="Stop Server", command=self.stop_server)
        self.stop_button.pack(pady=10)

        self.status_label = tk.Label(self.root, text="Server Status: Unknown", fg="red")
        self.status_label.pack(pady=10)

        self.feedback_label = tk.Label(self.root, text="", fg="blue")
        self.feedback_label.pack(pady=10)

    def show_feedback(self, message):
        """Display feedback message."""
        self.feedback_label.config(text=message)
        self.root.update_idletasks()  # Refresh the UI immediately

    def reset_feedback(self):
        """Clear feedback message after a delay."""
        self.root.after(2000, lambda: self.feedback_label.config(text=""))

    def run_in_thread(self, command, success_message, failure_message):
        """Run a subprocess command in a thread."""
        def task():
            self.show_feedback(success_message)
            self.start_button.config(state="disabled")
            self.stop_button.config(state="disabled")
            try:
                subprocess.run(command, check=True)
                self.show_feedback(success_message)
            except subprocess.CalledProcessError:
                self.show_feedback(failure_message)
            finally:
                self.start_button.config(state="normal")
                self.stop_button.config(state="normal")
                self.reset_feedback()

        threading.Thread(target=task).start()

    def start_server(self):
        """Start the Gunicorn server via Supervisor."""
        self.run_in_thread(
            ["supervisorctl", "start", "mcsServer"],
            success_message="Starting the server...",
            failure_message="Failed to start the server."
        )
        self.status_label.config(text="Server Status: Running", fg="green")

    def stop_server(self):
        """Stop the Gunicorn server via Supervisor."""
        self.run_in_thread(
            ["supervisorctl", "stop", "mcsServer"],
            success_message="Stopping the server...",
            failure_message="Failed to stop the server."
        )
        self.status_label.config(text="Server Status: Stopped", fg="red")

def check_password():
    """Prompt the user to enter the password."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window initially
    user_password = simpledialog.askstring("Password Required", "Enter the password:", show="*")
    if user_password == PASSWORD:
        root.destroy()
        return True
    else:
        root.destroy()
        return False

if __name__ == "__main__":
    if check_password():
        root = tk.Tk()
        app = ServerControlApp(root)
        root.mainloop()
    else:
        print("Incorrect password. Exiting.")
