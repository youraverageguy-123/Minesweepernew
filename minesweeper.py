import tkinter as tk
import random
from tkinter import messagebox
import time
import os

# ---------- Globals ----------
board = []
revealed = []
buttons = {}
flags = 0
flagged = set()
mine_set = set()
game_over = False
rng_seed=None

SCORE_FILE = "minesweeper_scores.txt"
SAVES_DIR = "saves"
SLOT_FILES = [os.path.join(SAVES_DIR, f"slot{i}.txt") for i in range(1, 4)]
current_save_slot = None  # which slot (1..3) this running game is associated with (or None)

# ensure saves dir exists
if not os.path.exists(SAVES_DIR):
    os.makedirs(SAVES_DIR)


# ---------- Score helpers ----------
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


# ---------- Save/Load slots ----------
def write_slot(slot, rows, cols, mines, board_data, revealed_data, flagged_set, elapsed):
    """Write the slot file for slot (1..3)."""
    path = SLOT_FILES[slot - 1]
    with open(path, "w") as f:
        f.write(f"{rows} {cols} {mines}\n")
        f.write(f"{int(elapsed)}\n")
        f.write(f"{rng_seed}\n")

        # board rows
        for row in board_data:
            f.write("".join(row) + "\n")
        # revealed rows
        for row in revealed_data:
            f.write("".join("1" if x else "0" for x in row) + "\n")
        # flagged
        flags_str = ";".join(f"{r},{c}" for (r, c) in flagged_set)
        f.write(flags_str + "\n")


def read_slot(slot):
    """Read slot file; return tuple or None if missing."""
    path = SLOT_FILES[slot - 1]
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]
    if len(lines) < 2:
        return None
    ROWS_, COLS_, MINES_ = map(int, lines[0].split())
    elapsed = int(lines[1])
    seed = int(lines[2])

    board_data = [list(lines[3 + r]) for r in range(ROWS_)]
    rev_start = 3 + ROWS_

    revealed_data = [[c == "1" for c in lines[rev_start + r]] for r in range(ROWS_)]
    flagged_line = lines[rev_start + ROWS_] if len(lines) > rev_start + ROWS_ else ""
    flagged_set = set()
    if flagged_line:
        for pair in flagged_line.split(";"):
            if pair.strip():
                r, c = map(int, pair.split(","))
                flagged_set.add((r, c))
    return ROWS_, COLS_, MINES_, board_data, revealed_data, flagged_set, elapsed,seed


def slot_exists(slot):
    return os.path.exists(SLOT_FILES[slot - 1])


def delete_slot_file(slot):
    path = SLOT_FILES[slot - 1]
    if os.path.exists(path):
        os.remove(path)


# ---------- Game logic (original, lightly adapted) ----------
def start_game():
    global ROWS, COLS, MINES, input_window, player_name, current_save_slot
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

    current_save_slot = None  # fresh game has no associated save slot yet
    input_window.destroy()
    launch_game()


def place_mines():
    global board, mine_set, rng_seed

    # generate deterministic seed
    rng_seed = random.randint(0, 10**9)
    random.seed(rng_seed)

    board = [["0" for _ in range(COLS)] for _ in range(ROWS)]
    mine_set = set()

    # YOU DELETED THIS. PUT IT BACK.
    mine_positions = random.sample(range(ROWS * COLS), MINES)

    # place mines
    for idx in mine_positions:
        r, c = divmod(idx, COLS)
        board[r][c] = "M"
        mine_set.add((r, c))

    # compute number grid
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

        # delete the associated slot on loss (if any)
        if current_save_slot is not None:
            delete_slot_file(current_save_slot)

        elapsed = int(time.time() - start_time)
        save_score(player_name + "(Lost)", elapsed, ROWS, COLS, MINES)
        messagebox.showinfo("Boom!", f"You hit a mine! Time: {elapsed}s")
        root.destroy()
    elif value == "0":
        flood_fill(r, c)
    elif check_win():
        game_over = True

        # delete associated slot on win
        if current_save_slot is not None:
            delete_slot_file(current_save_slot)

        elapsed = int(time.time() - start_time)
        save_score(player_name, elapsed, ROWS, COLS, MINES)
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

        # delete associated slot on win-by-flag
        if current_save_slot is not None:
            delete_slot_file(current_save_slot)

        elapsed = int(time.time() - start_time)
        save_score(player_name, elapsed, ROWS, COLS, MINES)
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


def launch_game(resume=False):
    global root, revealed, timer_label, game_over, flagged, flags, mine_set, start_time

    game_over = False
    flagged = set()
    flags = 0
    mine_set = set()
    root = tk.Tk()
    root.title("Minesweeper")

    if not resume:
        place_mines()
        revealed = [[False for _ in range(COLS)] for _ in range(ROWS)]
        start_time = time.time()
    else:
        # when resuming, board and revealed are already set; just recompute mine_set
        mine_set = {(r, c) for r in range(ROWS) for c in range(COLS) if board[r][c] == "M"}

    create_buttons()

    # render revealed and flags if resuming
    if resume:
        for r in range(ROWS):
            for c in range(COLS):
                if revealed[r][c]:
                    val = board[r][c]
                    txt = "" if val == "0" else val
                    buttons[(r, c)].config(text=txt, relief=tk.SUNKEN, bg="#CFECEC", state=tk.DISABLED)
        for (r, c) in flagged:
            if (r, c) in buttons:
                buttons[(r, c)].config(text="F", fg="red")

    # Save Game button (choose slot)
    save_btn = tk.Button(root, text="Save Game", command=lambda: save_game_slot_prompt())
    save_btn.grid(row=ROWS + 2, column=0, columnspan=max(1, COLS // 2), pady=6)

    timer_label = tk.Label(root, text="Time: 0s", font=("Arial", 12, "bold"))
    timer_label.grid(row=0, column=0, columnspan=COLS)

    root.after(0, start_timer_and_ui)

    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"+{x}+{y}")

    root.mainloop()


# ---------- Save/Load UI actions ----------
def save_game_slot_prompt():
    """Popup to choose a slot to save into (1..3)."""
    prompt = tk.Toplevel()
    prompt.title("Save Game - Choose Slot")
    tk.Label(prompt, text="Choose save slot (1-3):").grid(row=0, column=0, columnspan=3, pady=6)

    def do_save(slot):
        global current_save_slot
        # warn about overwrite
        if slot_exists(slot):
            if not messagebox.askyesno("Overwrite?", f"Slot {slot} is occupied. Overwrite?"):
                return
        elapsed = int(time.time() - start_time)
        write_slot(slot, ROWS, COLS, MINES, board, revealed, flagged, elapsed)
        current_save_slot = slot
        messagebox.showinfo("Saved", f"Game saved to slot {slot}.")
        prompt.destroy()

    for i in range(1, 4):
        status = "Empty" if not slot_exists(i) else "Occupied"
        btn = tk.Button(prompt, text=f"Slot {i}\n({status})", width=12, command=lambda s=i: do_save(s))
        btn.grid(row=1, column=i - 1, padx=6, pady=6)


def load_game_prompt_from_menu():
    """Popup that shows slot statuses and allows loading one."""
    prompt = tk.Toplevel()
    prompt.title("Load Saved Game")
    tk.Label(prompt, text="Choose a slot to load:").grid(row=0, column=0, columnspan=3, pady=6)

    def do_load(slot):
        data = read_slot(slot)
        if data is None:
            messagebox.showerror("Empty", f"Slot {slot} is empty.")
            return
        # unpack and set globals, then start game resume
        global ROWS, COLS, MINES, board, revealed, flagged, start_time, current_save_slot
        ROWS, COLS, MINES, board, revealed, flagged, elapsed, seed = data
        global rng_seed
        rng_seed = seed
        random.seed(rng_seed)

        # set start_time so timer resumes
        start_time = time.time() - int(elapsed)
        current_save_slot = slot
        prompt.destroy()
        input_window.destroy()
        launch_game(resume=True)

    for i in range(1, 4):
        status = "Empty" if not slot_exists(i) else "Occupied"
        btn = tk.Button(prompt, text=f"Slot {i}\n({status})", width=12, command=lambda s=i: do_load(s))
        btn.grid(row=1, column=i - 1, padx=6, pady=6)


# ---------- MENU WINDOW ----------
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
tk.Button(input_window, text="Load Saved Game", command=load_game_prompt_from_menu).grid(row=6, column=0, columnspan=2, pady=5)

input_window.mainloop()
