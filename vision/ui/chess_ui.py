import customtkinter as ctk
import tkinter as tk
import time


# ============================================================
# CONFIG
# ============================================================

START_TIME = 10 * 60          # 10 minutes
ROBOT_MOVE_TIME = 4000        # 4 seconds - temporary simulation


# ============================================================
# APP
# ============================================================

class ChessRobotUI(ctk.CTk):

    def __init__(self):
        super().__init__()

        # ----------------------------------------------------
        # Window
        # ----------------------------------------------------

        self.title("Chess Playing Robotic Arm")
        self.geometry("1100x700")
        self.minsize(950, 650)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ----------------------------------------------------
        # User / game data
        # ----------------------------------------------------

        self.username = ""
        self.difficulty = ""
        self.player_color = ""

        # ----------------------------------------------------
        # Clocks
        # ----------------------------------------------------

        self.user_time = START_TIME
        self.robot_time = START_TIME

        self.user_running = False
        self.robot_running = False

        self.last_time = time.time()

        # ----------------------------------------------------
        # UI state
        # ----------------------------------------------------

        self.current_screen = None

        self.clock_job = None
        self.robot_job = None

        self.app_closing = False

        # ----------------------------------------------------
        # Window close button
        # ----------------------------------------------------

        self.protocol(
            "WM_DELETE_WINDOW",
            self.close_application
        )

        # ----------------------------------------------------
        # Start
        # ----------------------------------------------------

        self.show_login_screen()

        self.clock_job = self.after(
            100,
            self.update_clock
        )

    # ========================================================
    # GENERAL
    # ========================================================

    def clear_screen(self):

        if self.current_screen is not None:

            try:
                self.current_screen.destroy()
            except tk.TclError:
                pass

        self.current_screen = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.current_screen.pack(
            fill="both",
            expand=True
        )

    def title_label(self, parent, text, size=30):

        return ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(
                size=size,
                weight="bold"
            )
        )

    # ========================================================
    # LOGIN
    # ========================================================

    def show_login_screen(self):

        self.clear_screen()

        frame = ctk.CTkFrame(
            self.current_screen,
            width=420,
            height=500,
            corner_radius=20
        )

        frame.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        # self.title_label(
        #     frame,
        #     "♟ ChessCog",
        #     38
        # ).pack(
        #     pady=(45, 5)
        # )

        ctk.CTkLabel(
            frame,
            text="Chess Playing Robotic Arm",
            font=ctk.CTkFont(size=16)
        ).pack(
            pady=(0, 35)
        )

        self.username_entry = ctk.CTkEntry(
            frame,
            width=280,
            height=45,
            placeholder_text="Username"
        )

        self.username_entry.pack(
            pady=10
        )

        self.password_entry = ctk.CTkEntry(
            frame,
            width=280,
            height=45,
            placeholder_text="Password",
            show="*"
        )

        self.password_entry.pack(
            pady=10
        )

        ctk.CTkButton(
            frame,
            text="LOGIN",
            width=280,
            height=45,
            command=self.login
        ).pack(
            pady=(25, 10)
        )

        ctk.CTkButton(
            frame,
            text="REGISTER",
            width=280,
            height=45,
            fg_color="transparent",
            border_width=1,
            command=self.register
        ).pack(
            pady=10
        )

    # ========================================================
    # LOGIN
    # ========================================================

    def login(self):

        username = self.username_entry.get().strip()

        if not username:
            username = "Player"

        self.username = username

        # TODO:
        # Connect to user_table/database later.

        self.show_game_setup()

    # ========================================================
    # REGISTER
    # ========================================================

    def register(self):

        username = self.username_entry.get().strip()

        if not username:
            username = "Player"

        self.username = username

        # TODO:
        # Connect to user_table/database later.
        #
        # Example:
        #
        # register_user(
        #     username,
        #     self.password_entry.get()
        # )

        self.show_game_setup()

    # ========================================================
    # GAME SETUP
    # ========================================================

    def show_game_setup(self):

        self.clear_screen()

        container = ctk.CTkFrame(
            self.current_screen,
            corner_radius=20
        )

        container.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        self.title_label(
            container,
            "Game Setup",
            34
        ).pack(
            pady=(35, 5)
        )

        ctk.CTkLabel(
            container,
            text=f"Welcome, {self.username}",
            font=ctk.CTkFont(size=16)
        ).pack(
            pady=(0, 25)
        )

        # ----------------------------------------------------
        # Difficulty
        # ----------------------------------------------------

        ctk.CTkLabel(
            container,
            text="Difficulty",
            font=ctk.CTkFont(
                size=18,
                weight="bold"
            )
        ).pack(
            pady=10
        )

        self.difficulty_var = tk.StringVar(
            value="Medium"
        )

        difficulty_frame = ctk.CTkFrame(
            container,
            fg_color="transparent"
        )

        difficulty_frame.pack()

        for difficulty in [
            "Easy",
            "Medium",
            "Hard",
            "Expert"
        ]:

            ctk.CTkRadioButton(
                difficulty_frame,
                text=difficulty,
                variable=self.difficulty_var,
                value=difficulty
            ).pack(
                side="left",
                padx=10
            )

        # ----------------------------------------------------
        # Color
        # ----------------------------------------------------

        ctk.CTkLabel(
            container,
            text="Choose Your Color",
            font=ctk.CTkFont(
                size=18,
                weight="bold"
            )
        ).pack(
            pady=(30, 10)
        )

        self.color_var = tk.StringVar(
            value="White"
        )

        color_frame = ctk.CTkFrame(
            container,
            fg_color="transparent"
        )

        color_frame.pack()

        ctk.CTkRadioButton(
            color_frame,
            text="White",
            variable=self.color_var,
            value="White"
        ).pack(
            side="left",
            padx=30
        )

        ctk.CTkRadioButton(
            color_frame,
            text="Black",
            variable=self.color_var,
            value="Black"
        ).pack(
            side="left",
            padx=30
        )

        # ----------------------------------------------------
        # Start Game
        # ----------------------------------------------------

        ctk.CTkButton(
            container,
            text="START GAME",
            width=300,
            height=50,
            font=ctk.CTkFont(
                size=18,
                weight="bold"
            ),
            command=self.start_game
        ).pack(
            pady=40
        )

    # ========================================================
    # START GAME
    # ========================================================

    def start_game(self):

        self.difficulty = self.difficulty_var.get()
        self.player_color = self.color_var.get()

        # ----------------------------------------------------
        # Reset clocks
        # ----------------------------------------------------

        self.user_time = START_TIME
        self.robot_time = START_TIME

        self.user_running = False
        self.robot_running = False

        # Cancel any previous robot simulation
        self.cancel_robot_job()

        # ----------------------------------------------------
        # Show game screen
        # ----------------------------------------------------

        self.show_game_screen()

        # ----------------------------------------------------
        # WHITE
        #
        # User starts.
        # ----------------------------------------------------

        if self.player_color == "White":

            self.user_running = True
            self.robot_running = False

            self.status_label.configure(
                text="Your turn"
            )

            self.recognition_label.configure(
                text="Vision: Ready\nArm: Ready"
            )

            self.move_done_button.configure(
                state="normal"
            )

            print("GAME STARTED")
            print("PLAYER COLOR: WHITE")
            print("USER CLOCK STARTED")

        # ----------------------------------------------------
        # BLACK
        #
        # Robot starts.
        # ----------------------------------------------------

        else:

            self.user_running = False
            self.robot_running = True

            self.status_label.configure(
                text="Robot opening move..."
            )

            self.move_done_button.configure(
                state="disabled"
            )

            self.recognition_label.configure(
                text="Vision: Ready\nArm: Executing..."
            )

            print("GAME STARTED")
            print("PLAYER COLOR: BLACK")
            print("ROBOT CLOCK STARTED")

            # Temporary robot opening move simulation
            self.robot_job = self.after(
                ROBOT_MOVE_TIME,
                self.robot_move_finished
            )

    # ========================================================
    # GAME SCREEN
    # ========================================================

    def show_game_screen(self):

        self.clear_screen()

        # ----------------------------------------------------
        # TOP BAR
        # ----------------------------------------------------

        top = ctk.CTkFrame(
            self.current_screen,
            height=70,
            corner_radius=0
        )

        top.pack(
            fill="x",
            padx=10,
            pady=(10, 5)
        )

        # ctk.CTkLabel(
        #     top,
        #     text="♟ ChessCog",
        #     font=ctk.CTkFont(
        #         size=25,
        #         weight="bold"
        #     )
        # ).pack(
        #     side="left",
        #     padx=20
        # )

        ctk.CTkLabel(
            top,
            text=(
                f"{self.username}  |  "
                f"{self.player_color}  |  "
                f"{self.difficulty}"
            ),
            font=ctk.CTkFont(size=15)
        ).pack(
            side="right",
            padx=20
        )

        # ----------------------------------------------------
        # MAIN AREA
        # ----------------------------------------------------

        main = ctk.CTkFrame(
            self.current_screen,
            fg_color="transparent"
        )

        main.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10
        )

        # ----------------------------------------------------
        # CHESSBOARD
        # ----------------------------------------------------

        board_frame = ctk.CTkFrame(
            main,
            corner_radius=15
        )

        board_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10)
        )

        self.draw_chessboard(
            board_frame
        )

        # ----------------------------------------------------
        # RIGHT PANEL
        # ----------------------------------------------------

        panel = ctk.CTkFrame(
            main,
            width=300,
            corner_radius=15
        )

        panel.pack(
            side="right",
            fill="y",
            padx=(10, 0)
        )

        panel.pack_propagate(False)

        # ----------------------------------------------------
        # ROBOT CLOCK
        # ----------------------------------------------------

        ctk.CTkLabel(
            panel,
            text="ROBOT",
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            )
        ).pack(
            pady=(25, 0)
        )

        self.robot_clock_label = ctk.CTkLabel(
            panel,
            text=self.format_time(
                self.robot_time
            ),
            font=ctk.CTkFont(
                size=40,
                weight="bold"
            )
        )

        self.robot_clock_label.pack(
            pady=(0, 20)
        )

        # ----------------------------------------------------
        # USER CLOCK
        # ----------------------------------------------------

        ctk.CTkLabel(
            panel,
            text=self.username.upper(),
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            )
        ).pack(
            pady=(10, 0)
        )

        self.user_clock_label = ctk.CTkLabel(
            panel,
            text=self.format_time(
                self.user_time
            ),
            font=ctk.CTkFont(
                size=40,
                weight="bold"
            )
        )

        self.user_clock_label.pack(
            pady=(0, 25)
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        ctk.CTkLabel(
            panel,
            text="STATUS",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            )
        ).pack()

        self.status_label = ctk.CTkLabel(
            panel,
            text="",
            font=ctk.CTkFont(
                size=18,
                weight="bold"
            )
        )

        self.status_label.pack(
            pady=5
        )

        # ----------------------------------------------------
        # MOVE DONE
        # ----------------------------------------------------

        self.move_done_button = ctk.CTkButton(
            panel,
            text="MOVE DONE",
            width=220,
            height=55,
            font=ctk.CTkFont(
                size=17,
                weight="bold"
            ),
            command=self.user_move_done
        )

        self.move_done_button.pack(
            pady=25
        )

        # ----------------------------------------------------
        # SYSTEM STATUS
        # ----------------------------------------------------

        ctk.CTkLabel(
            panel,
            text="SYSTEM",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            )
        ).pack(
            pady=(10, 5)
        )

        self.recognition_label = ctk.CTkLabel(
            panel,
            text="",
            justify="left",
            font=ctk.CTkFont(size=14)
        )

        self.recognition_label.pack()

        # ----------------------------------------------------
        # END GAME
        # ----------------------------------------------------

        ctk.CTkButton(
            panel,
            text="END GAME",
            fg_color="transparent",
            border_width=1,
            command=self.end_game
        ).pack(
            side="bottom",
            pady=20
        )

    # ========================================================
    # CHESSBOARD
    # ========================================================

    def draw_chessboard(self, parent):

        board = tk.Canvas(
            parent,
            bg="#222222",
            highlightthickness=0
        )

        board.pack(
            expand=True,
            padx=20,
            pady=20
        )

        size = 480
        square = size // 8

        start_x = 20
        start_y = 20

        for row in range(8):

            for col in range(8):

                x1 = start_x + col * square
                y1 = start_y + row * square

                x2 = x1 + square
                y2 = y1 + square

                if (row + col) % 2 == 0:
                    color = "#F0D9B5"
                else:
                    color = "#B58863"

                board.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=color,
                    outline=""
                )

        board.config(
            width=size + 40,
            height=size + 40
        )

    # ========================================================
    # TIME FORMAT
    # ========================================================

    def format_time(self, seconds):

        seconds = max(
            0,
            int(seconds)
        )

        minutes = seconds // 60
        seconds = seconds % 60

        return f"{minutes:02d}:{seconds:02d}"

    # ========================================================
    # CLOCK UPDATE
    # ========================================================

    def update_clock(self):

        if self.app_closing:
            return

        now = time.time()

        elapsed = now - self.last_time

        self.last_time = now

        # ----------------------------------------------------
        # USER CLOCK
        # ----------------------------------------------------

        if self.user_running:

            self.user_time -= elapsed

        # ----------------------------------------------------
        # ROBOT CLOCK
        # ----------------------------------------------------

        if self.robot_running:

            self.robot_time -= elapsed

        # ----------------------------------------------------
        # USER TIMEOUT
        # ----------------------------------------------------

        if self.user_time <= 0:

            self.user_time = 0

            self.user_running = False

            if self.current_screen:
                self.game_over(
                    "Time out!"
                )

        # ----------------------------------------------------
        # ROBOT TIMEOUT
        # ----------------------------------------------------

        if self.robot_time <= 0:

            self.robot_time = 0

            self.robot_running = False

            if self.current_screen:
                self.game_over(
                    "Robot time out!"
                )

        # ----------------------------------------------------
        # Update labels safely
        # ----------------------------------------------------

        try:

            if (
                self.current_screen
                and self.current_screen.winfo_exists()
                and hasattr(
                    self,
                    "user_clock_label"
                )
                and self.user_clock_label.winfo_exists()
            ):

                self.user_clock_label.configure(
                    text=self.format_time(
                        self.user_time
                    )
                )

            if (
                self.current_screen
                and self.current_screen.winfo_exists()
                and hasattr(
                    self,
                    "robot_clock_label"
                )
                and self.robot_clock_label.winfo_exists()
            ):

                self.robot_clock_label.configure(
                    text=self.format_time(
                        self.robot_time
                    )
                )

        except tk.TclError:

            pass

        # ----------------------------------------------------
        # Schedule next update
        # ----------------------------------------------------

        if not self.app_closing:

            self.clock_job = self.after(
                100,
                self.update_clock
            )

    # ========================================================
    # USER MOVE DONE
    # ========================================================

    def user_move_done(self):

        # ----------------------------------------------------
        # Only allow button during user's turn
        # ----------------------------------------------------

        if not self.user_running:
            return

        # ----------------------------------------------------
        # STOP USER CLOCK
        # ----------------------------------------------------

        self.user_running = False

        print("USER MOVE COMPLETE")
        print("USER CLOCK STOPPED")

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self.status_label.configure(
            text="Robot thinking..."
        )

        self.move_done_button.configure(
            state="disabled"
        )

        self.recognition_label.configure(
            text=(
                "Vision: Processing...\n"
                "Arm: Waiting..."
            )
        )

        # ----------------------------------------------------
        # TODO:
        #
        # Actual ChessCog recognition goes here.
        #
        # 1. Capture board
        # 2. Detect pieces
        # 3. Determine user's move
        # 4. Generate robot move
        # 5. Send move to arm
        #
        # ----------------------------------------------------

        # ----------------------------------------------------
        # START ROBOT CLOCK
        # ----------------------------------------------------

        self.robot_running = True

        self.status_label.configure(
            text="Robot executing..."
        )

        self.recognition_label.configure(
            text=(
                "Vision: Complete\n"
                "Arm: Executing..."
            )
        )

        print("ROBOT CLOCK STARTED")

        # ----------------------------------------------------
        # TEMPORARY ROBOT SIMULATION
        # ----------------------------------------------------

        self.cancel_robot_job()

        self.robot_job = self.after(
            ROBOT_MOVE_TIME,
            self.robot_move_finished
        )

    # ========================================================
    # ROBOT MOVE FINISHED
    # ========================================================

    def robot_move_finished(self):

        # ----------------------------------------------------
        # Robot simulation job is finished
        # ----------------------------------------------------

        self.robot_job = None

        # ----------------------------------------------------
        # STOP ROBOT CLOCK
        # ----------------------------------------------------

        self.robot_running = False

        print("ROBOT MOVE COMPLETE")
        print("ROBOT CLOCK STOPPED")

        # ----------------------------------------------------
        # START USER CLOCK
        # ----------------------------------------------------

        self.user_running = True

        print("USER CLOCK STARTED")

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self.status_label.configure(
            text="Your turn"
        )

        self.recognition_label.configure(
            text=(
                "Vision: Ready\n"
                "Arm: Ready"
            )
        )

        self.move_done_button.configure(
            state="normal"
        )

    # ========================================================
    # CANCEL ROBOT JOB
    # ========================================================

    def cancel_robot_job(self):

        if self.robot_job is not None:

            try:

                self.after_cancel(
                    self.robot_job
                )

            except tk.TclError:

                pass

            self.robot_job = None

    # ========================================================
    # GAME OVER
    # ========================================================

    def game_over(self, reason):

        self.user_running = False
        self.robot_running = False

        self.cancel_robot_job()

        try:

            self.status_label.configure(
                text=reason
            )

            self.move_done_button.configure(
                state="disabled"
            )

        except tk.TclError:

            pass

    # ========================================================
    # END GAME
    # ========================================================

    def end_game(self):

        print("ENDING GAME")

        # ----------------------------------------------------
        # Stop clocks
        # ----------------------------------------------------

        self.user_running = False
        self.robot_running = False

        # ----------------------------------------------------
        # Cancel robot simulation
        # ----------------------------------------------------

        self.cancel_robot_job()

        # ----------------------------------------------------
        # Show login screen
        # ----------------------------------------------------

        self.show_login_screen()

        # ----------------------------------------------------
        # Reset timer reference
        # ----------------------------------------------------

        self.last_time = time.time()

    # ========================================================
    # CLOSE APPLICATION
    # ========================================================

    def close_application(self):

        print("CLOSING APPLICATION")

        # ----------------------------------------------------
        # Tell timer loop to stop
        # ----------------------------------------------------

        self.app_closing = True

        # ----------------------------------------------------
        # Stop clocks
        # ----------------------------------------------------

        self.user_running = False
        self.robot_running = False

        # ----------------------------------------------------
        # Cancel clock callback
        # ----------------------------------------------------

        if self.clock_job is not None:

            try:

                self.after_cancel(
                    self.clock_job
                )

            except tk.TclError:

                pass

            self.clock_job = None

        # ----------------------------------------------------
        # Cancel robot callback
        # ----------------------------------------------------

        self.cancel_robot_job()

        # ----------------------------------------------------
        # Destroy window
        # ----------------------------------------------------

        try:

            self.destroy()

        except tk.TclError:

            pass


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app = ChessRobotUI()

    app.mainloop()