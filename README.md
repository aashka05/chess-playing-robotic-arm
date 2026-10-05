# Chess Playing Robotic Arm

Play chess against a Stockfish-powered robotic arm. The system has following parts:

| Part | Where it runs | Folder |
|---|---|---|
| **Backend** (FastAPI, PostgreSQL, game logic) | The computer next to the arm (USB serial to the Arduino) | `backend/` |
| **Vision** (ArUco rectification, YOLO pieces, move matching) | Used by the backend; scripts also run standalone | `vision/` |
| **Arm control** (move planning, square → servo angles, serial/mock driver) | Used by the backend; `send_angles.py` also runs standalone | `controller/` |
| **Engine** (Stockfish binary + Python wrappers) | Used by the backend | `stockfish/` |
| **Controller app** (Flutter), phone B | Beside the board: setup, chess clock, history, replay | `app/` |
| **Camera app** (same Flutter app in *Camera mode*), phone A | Mounted above the board | `app/` |

```
phone B ──REST + WS──▶ backend ◀──WS (capture requests) + upload── phone A
                          │
                          ├── PostgreSQL
                          ├── Stockfish (2 processes: play + analysis)
                          └── USB serial ──▶ Arduino arm
```

---

## 1. Game flow

1. **Setup 1.** Place the empty board with the four ArUco markers visible and press OK. Phone A takes a photo and `rectify_board` finds the 64 squares. The calibration is saved to `backend/data/calibration.json`.
2. **Setup 2.** Set up the pieces and press OK. The photo is compared with the starting position. Wrong squares are shown in red on a board diagram; fix them and press OK again, repeating until the position is correct.
3. **Setup 3.** Choose your colour, the difficulty and the time control, then press **Start**.
4. **Clock screen.** The backend owns the clocks and the state machine; the app only displays them.
   - You move, then tap your clock. The robot's clock starts, phone A takes a photo, and the move is identified (see below). Stockfish replies and the arm plays the move. Then your clock starts.
   - If you play Black, the robot opens without any detection.
   - **Move not recognized:** nothing is applied. The robot's time is refunded, your clock resumes, and the app asks you to restore the position and press the clock again.
   - **Promotion (robot):** the arm removes the pawn and the app asks you to put the promoted piece on the square and press OK. The clocks are paused meanwhile.
   - **Arm error:** the app asks you to finish the robot's move by hand and press OK. The clocks are paused.
   - **Game end:** checkmate, stalemate and draw rules (`board.outcome(claim_draw=True)`), resignation, time-out (a draw if the opponent has insufficient material) and abort. The result, termination reason, final FEN and PGN are saved.
5. **History and replay.** Tap any game to step through the moves, with an evaluation bar and graph from the stored Stockfish evals. Admins see every player's games.

### How move detection works
The backend never reads the board from scratch. `detect_pieces` (your YOLO code) gives a piece and confidence per square. `vision/move_matcher.py` then scores every **legal** move by how well its resulting position agrees with those detections. A move is accepted only if all of these hold:
- it beats the runner-up and "no move made" by a clear margin;
- the squares it changes agree with the camera;
- at least 80% of the board agrees overall.

This handles castling, en passant and promotion (the promoted piece type comes from the detection), and it tolerates a misclassified piece type or an unrelated missed piece. Your original diff-based `detect_move()` still runs as a cross-check and is logged when it disagrees.

---

## 2. Arm

In serial mode the backend speaks the existing Arduino protocol from `controller/send_angles.py`. Each command is one line, `SEQ,g0,base,shoulder,elbow,wristPitch,wristRoll,g1`, and the Arduino replies `SEQ DONE` or `ERROR…`, with a timeout. Squares are mirrored before lookup, the JSON order is `[m0, m3, m2, m1]`, the wrist roll is fixed at 180 and the gripper angles depend on the piece type, all as in the original script.

A robot move is broken into pick/place commands:
- **Capture:** the captured piece goes to the `graveyard` first, then the piece moves.
- **Castling:** the king moves, then the rook.
- **En passant:** the pawn on the passed square is removed, then the pawn moves.
- **Promotion:** the pawn goes to the graveyard, then you place the new piece.

Every command writes 6 `motor_log` rows (servos 0–4 and the gripper) with success or failure.

In serial mode the backend checks every square of a move **before** sending anything. If an entry is missing, the arm doesn't move and the app asks you to make the robot's move by hand. The mock arm uses zeros for missing entries so development isn't blocked.

---

## 3. Project layout

```
backend/
  app/api/        REST routers + WebSockets (/ws/games/{id}, /ws/camera)
  app/core/       settings, DB session, JWT + argon2
  app/models/     SQLAlchemy models (user_table, game_table, move_table, motor_log)
  app/schemas/    Pydantic request/response models
  app/services/   game_service (orchestration), state_machine, clock_service,
                  game_rules, detection_service, engine_service, arm_service, repository
  app/camera/     CameraSource interface + AppUploadCameraSource
  alembic/        migrations
  tests/          unit + game-flow tests (pytest)
vision/
  rectify_board.py, map_pieces_to_squares.py, move_detection.py
                  your scripts, refactored to take numpy images; CLI kept
  move_matcher.py legal-move matching used by the backend
runs/detect/merged-from-scratch2/weights/best.pt
                  YOLO weights (the only model; MODEL_PATH in map_pieces_to_squares.py)
controller/
  send_angles.py  your manual/vision-driven arm script
  planner.py      chess move → pick/place operations
  angles.py       square → servo angles (angles_dict.json), SEQ command format
  driver.py       serial + mock arm drivers
  angles_dict.json
stockfish/
  stockfish       engine binary (Stockfish 19, macOS universal)
  engine.py       async wrapper used by the backend (Skill Level + move time)
  stockfish_engine.py  your synchronous wrapper, used by the move_detection CLI
app/lib/
  core/           typed API client, reconnecting WebSocket, models, providers
  features/       auth, home, setup (incl. camera mode), game (clock), history, replay
  shared/         chess board, eval bar/graph, formatting
requirements.txt  one venv for everything (includes the three below)
```

### Decisions and limitations
- Only one game can run at a time, because there is one board and one arm.
- A game left `in_progress` when the backend stops is marked `aborted` on the next start; games can't be resumed.
- Setup progress is held in memory. The schema has no calibration table, so calibration is stored in a JSON file.
- The increment is added only when a move is accepted. Clocks pause while waiting for you to help the arm.
- Registration creates `client` accounts; admins are created with `python -m app.cli create-admin`.
- Phone A must keep the app open in the foreground in Camera mode.
