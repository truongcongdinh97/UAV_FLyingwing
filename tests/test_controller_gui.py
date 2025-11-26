import tkinter as tk
from tkinter import ttk
import pygame
import sys

class ControllerTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RadioMaster / Controller Tester GUI")
        self.root.geometry("800x600")
        
        # Initialize Pygame for Joystick support
        pygame.init()
        pygame.joystick.init()
        
        self.joystick = None
        self.axes_bars = []
        self.button_indicators = []
        self.hat_labels = []
        
        # --- UI Layout ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top Bar: Device Selection
        top_frame = ttk.LabelFrame(main_frame, text="Device Selection", padding="5")
        top_frame.pack(fill=tk.X, pady=5)
        
        self.device_combo = ttk.Combobox(top_frame, state="readonly")
        self.device_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_select)
        
        refresh_btn = ttk.Button(top_frame, text="Refresh Devices", command=self.refresh_devices)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # Content Area (Split into Axes and Buttons)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left: Axes (Sticks/Sliders)
        self.axes_frame = ttk.LabelFrame(content_frame, text="Axes (Sticks & Pots)", padding="10")
        self.axes_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Right: Buttons (Switches) & Hats
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.buttons_frame = ttk.LabelFrame(right_frame, text="Buttons (Switches)", padding="10")
        self.buttons_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.hats_frame = ttk.LabelFrame(right_frame, text="Hats (D-Pad)", padding="10")
        self.hats_frame.pack(fill=tk.X)
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready. Please select a controller.")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initial Refresh
        self.refresh_devices()
        
        # Start Update Loop
        self.root.after(20, self.update_loop)

    def refresh_devices(self):
        """Scan for connected joysticks"""
        pygame.joystick.quit()
        pygame.joystick.init()
        
        count = pygame.joystick.get_count()
        devices = []
        for i in range(count):
            try:
                j = pygame.joystick.Joystick(i)
                j.init()
                devices.append(f"{i}: {j.get_name()}")
                j.quit()
            except:
                devices.append(f"{i}: Unknown Device")
        
        self.device_combo['values'] = devices
        if devices:
            self.device_combo.current(0)
            self.on_device_select(None)
        else:
            self.device_combo.set("No devices found")
            self.cleanup_ui()

    def on_device_select(self, event):
        """Initialize selected joystick"""
        selection = self.device_combo.get()
        if not selection or "No devices" in selection:
            return
            
        try:
            idx = int(selection.split(":")[0])
            self.joystick = pygame.joystick.Joystick(idx)
            self.joystick.init()
            
            self.status_var.set(f"Connected: {self.joystick.get_name()} | ID: {self.joystick.get_id()}")
            self.setup_dynamic_ui()
            
        except Exception as e:
            self.status_var.set(f"Error connecting: {e}")

    def cleanup_ui(self):
        """Clear dynamic widgets"""
        for widget in self.axes_frame.winfo_children():
            widget.destroy()
        for widget in self.buttons_frame.winfo_children():
            widget.destroy()
        for widget in self.hats_frame.winfo_children():
            widget.destroy()
        self.axes_bars = []
        self.button_indicators = []
        self.hat_labels = []

    def setup_dynamic_ui(self):
        """Create widgets based on joystick capabilities"""
        self.cleanup_ui()
        
        if not self.joystick:
            return

        # --- Setup Axes ---
        num_axes = self.joystick.get_numaxes()
        
        # Create a canvas for scrolling if too many axes
        canvas = tk.Canvas(self.axes_frame)
        scrollbar = ttk.Scrollbar(self.axes_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for i in range(num_axes):
            row = ttk.Frame(scrollable_frame)
            row.pack(fill=tk.X, pady=2)
            
            lbl = ttk.Label(row, text=f"Axis {i}", width=8)
            lbl.pack(side=tk.LEFT)
            
            # Progress bar (custom style needed for centering, but standard is 0-100)
            # We will map -1..1 to 0..100
            pb = ttk.Progressbar(row, orient=tk.HORIZONTAL, length=200, mode='determinate')
            pb.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            val_lbl = ttk.Label(row, text="0.00", width=6)
            val_lbl.pack(side=tk.RIGHT)
            
            self.axes_bars.append((pb, val_lbl))

        # --- Setup Buttons ---
        num_buttons = self.joystick.get_numbuttons()
        # Grid layout for buttons
        cols = 8
        for i in range(num_buttons):
            # Create a circular-ish indicator using Canvas
            f = ttk.Frame(self.buttons_frame)
            f.grid(row=i//cols, column=i%cols, padx=2, pady=2)
            
            c = tk.Canvas(f, width=20, height=20, highlightthickness=0)
            c.pack()
            # Draw circle
            circle = c.create_oval(2, 2, 18, 18, fill="gray", outline="black")
            
            lbl = ttk.Label(f, text=f"{i}", font=("Arial", 8))
            lbl.pack()
            
            self.button_indicators.append((c, circle))

        # --- Setup Hats ---
        num_hats = self.joystick.get_numhats()
        for i in range(num_hats):
            lbl = ttk.Label(self.hats_frame, text=f"Hat {i}: (0, 0)")
            lbl.pack(anchor=tk.W)
            self.hat_labels.append(lbl)

    def update_loop(self):
        """Main update loop"""
        if self.joystick:
            pygame.event.pump()
            
            # Update Axes
            for i, (pb, lbl) in enumerate(self.axes_bars):
                val = self.joystick.get_axis(i)
                # Map -1.0...1.0 to 0...100
                mapped_val = (val + 1) * 50
                pb['value'] = mapped_val
                lbl.config(text=f"{val:.2f}")
            
            # Update Buttons
            for i, (canvas, circle_id) in enumerate(self.button_indicators):
                state = self.joystick.get_button(i)
                color = "#00ff00" if state else "gray" # Green if pressed
                canvas.itemconfig(circle_id, fill=color)
            
            # Update Hats
            for i, lbl in enumerate(self.hat_labels):
                val = self.joystick.get_hat(i)
                lbl.config(text=f"Hat {i}: {val}")

        # Schedule next update (20ms = 50fps)
        self.root.after(20, self.update_loop)

def main():
    root = tk.Tk()
    # Set theme if available
    try:
        style = ttk.Style()
        style.theme_use('clam')
    except:
        pass
        
    app = ControllerTesterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
