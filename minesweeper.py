import tkinter as tk
import random
from tkinter import messagebox
import time
import os
board = []
revealed = []
buttons = {}
flags = 0
flagged = set()
mine_set = set()
game_over = False
SCORE_FILE = "minesweeper_scores.txt"

def save_score(name, elapsed, rows, cols, mines):
    """Save game result to file."""
    with open(SCORE_FILE, "a") as f:
        f.write(f"{name},{elapsed},{rows},{cols},{mines}\n")
        f.flush()
        os.fsync(f.fileno())

def load_scores():
    if not os.path.exists(SCORE_FILE):
        return []
    with open(SCORE_FILE, "r") as f:
        return [line.strip().split(",") for line in f.readlines() if line.strip()]

def show_scores():
    scores = load_scores()
    if not scores:
        messagebox.showinfo("Scoreboard", "No scores yet. Be the first loser.")
        return

    # Sort by time (ascending)
    scores.sort(key=lambda x: int(x[1]))
    text = "Name\tTime(s)\tRows\tCols\tMines\n" + "-" * 45 + "\n"
    for s in scores[:10]:
        text += f"{s[0]}\t{s[1]}\t{s[2]}\t{s[3]}\t{s[4]}\n"

    messagebox.showinfo("Top 10 Scores", text)

def start_game():
    global ROWS, COLS, MINES, input_window, player_name
    try:
        ROWS = int(entry_rows.get())
        COLS = int(entry_cols.get())
        MINES = int(entry_mines.get())
        player_name = entry_name.get().strip() or "Anonymous"

        if ROWS <= 0 or COLS <= 0 or MINES <= 0:
            raise ValueError
        if MINES >= ROWS * COLS:
            messagebox.showerror("Error!", "Too many Mines!")
            return
    except ValueError:
        messagebox.showerror("Error!", "Enter positive numbers!")
        return

    input_window.destroy()
    launch_game()

def place_mines():
    global board, mine_set
    board = [["0" for _ in range(COLS)] for _ in range(ROWS)]
    mine_set = set()
    mine_positions = random.sample(range(ROWS * COLS), MINES)

    for idx in mine_positions:
        r, c = divmod(idx, COLS)
        board[r][c] = "M"
        mine_set.add((r, c))

    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] != "M":
                count = sum(
                    1
                    for i in range(-1, 2)
                    for j in range(-1, 2)
                    if 0 <= r + i < ROWS and 0 <= c + j < COLS and board[r + i][c + j] == "M"
                )
                board[r][c] = str(count)

def show_cell(r, c):
    global game_over
    if revealed[r][c] or game_over:
        return

    revealed[r][c] = True
    value = board[r][c]
    text = "" if value == "0" else value
    buttons[(r, c)].config(text=text, relief=tk.SUNKEN, bg="#CFECEC", state=tk.DISABLED)

    if value == "M":
        game_over = True
        reveal_mines()
        elapsed = int(time.time() - start_time)
        save_score(player_name+"(Lost)", elapsed, ROWS, COLS, MINES)  # <-- moved here
        messagebox.showinfo("Boom!", f"You hit a mine! Time: {elapsed}s")
        root.destroy()
    elif value == "0":
        flood_fill(r, c)
    elif check_win():
        game_over = True
        elapsed = int(time.time() - start_time)
        save_score(player_name, elapsed, ROWS, COLS, MINES)  # <-- moved here
        messagebox.showinfo("Victory!", f"You cleared all mines in {elapsed} seconds!")
        root.destroy()

def flood_fill(r, c):
    stack = [(r, c)]
    while stack:
        cr, cc = stack.pop()
        for i in range(-1, 2):
            for j in range(-1, 2):
                nr, nc = cr + i, cc + j
                if 0 <= nr < ROWS and 0 <= nc < COLS and not revealed[nr][nc]:
                    revealed[nr][nc] = True
                    value = board[nr][nc]
                    text = "" if value == "0" else value
                    buttons[(nr, nc)].config(text=text, relief=tk.SUNKEN, bg="#E2E4E4", state=tk.DISABLED)
                    if value == "0":
                        stack.append((nr, nc))

def flag_cell(r, c):
    global flagged, flags, game_over
    if revealed[r][c] or game_over:
        return
    btn = buttons[(r, c)]
    if btn["text"] == "":
        btn.config(text="F", fg="red")
        flagged.add((r, c))
        flags += 1
    else:
        btn.config(text="")
        if (r, c) in flagged:
            flagged.remove((r, c))
            flags -= 1

    if len(flagged) == MINES and flagged == mine_set:
        game_over = True
        elapsed = int(time.time() - start_time)
        save_score(player_name, elapsed, ROWS, COLS, MINES)  # <-- moved here too
        messagebox.showinfo("Victory!", f"You flagged all mines correctly in {elapsed} seconds!")
        root.destroy()

def reveal_mines():
    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] == "M":
                buttons[(r, c)].config(text="M", bg="red")

def check_win():
    return all(
        revealed[r][c] or board[r][c] == "M"
        for r in range(ROWS)
        for c in range(COLS)
    )

def create_buttons():
    for r in range(ROWS):
        for c in range(COLS):
            b = tk.Button(root, width=3, height=1, command=lambda r=r, c=c: show_cell(r, c))
            b.bind("<Button-3>", lambda e, r=r, c=c: flag_cell(r, c))
            b.grid(row=r + 1, column=c)
            buttons[(r, c)] = b

def update_timer():
    if not game_over:
        elapsed = int(time.time() - start_time)
        timer_label.config(text=f"Time: {elapsed}s")
        root.after(1000, update_timer)

def start_timer_and_ui():
    global start_time
    start_time = time.time()
    update_timer()

def launch_game():
    global root, revealed, timer_label, game_over, flagged, flags, mine_set
    game_over = False
    flagged = set()
    flags = 0
    mine_set = set()
    root = tk.Tk()
    root.title("Minesweeper")

    place_mines()
    revealed = [[False for _ in range(COLS)] for _ in range(ROWS)]
    create_buttons()

    timer_label = tk.Label(root, text="Time: 0s", font=("Arial", 12, "bold"))
    timer_label.grid(row=0, column=0, columnspan=COLS)

    root.after(0, start_timer_and_ui)

    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"+{x}+{y}")

    root.mainloop()

# --- MENU WINDOW ---
input_window = tk.Tk()
input_window.title("Minesweeper Menu")

tk.Label(input_window, text="Player Name").grid(row=0, column=0)
entry_name = tk.Entry(input_window)
entry_name.grid(row=0, column=1)

tk.Label(input_window, text="Rows").grid(row=1, column=0)
entry_rows = tk.Entry(input_window)
entry_rows.grid(row=1, column=1)

tk.Label(input_window, text="Columns").grid(row=2, column=0)
entry_cols = tk.Entry(input_window)
entry_cols.grid(row=2, column=1)

tk.Label(input_window, text="Mines").grid(row=3, column=0)
entry_mines = tk.Entry(input_window)
entry_mines.grid(row=3, column=1)

tk.Button(input_window, text="Start Game", command=start_game).grid(row=4, column=0, columnspan=2, pady=5)
tk.Button(input_window, text="View Scores", command=show_scores).grid(row=5, column=0, columnspan=2, pady=5)

input_window.mainloop()
