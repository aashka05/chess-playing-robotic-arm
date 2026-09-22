import chess
import chess.engine
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

STOCKFISH_PATH = Path(
    r"C:\Users\veera\Desktop\chess-playing-robotic-arm\stockfish\stockfish.exe"
)

SEARCH_DEPTH = 15
ELO = 1500


# ============================================================
# STOCKFISH ENGINE
# ============================================================

class StockfishEngine:

    def __init__(self, stockfish_path=STOCKFISH_PATH,
                 depth=SEARCH_DEPTH,
                 elo=ELO):

        self.stockfish_path = str(stockfish_path)
        self.depth = depth
        self.elo = elo

        if not Path(self.stockfish_path).exists():
            raise FileNotFoundError(
                f"Stockfish executable not found:\n"
                f"{self.stockfish_path}"
            )

        print("=" * 60)
        print("STOCKFISH ENGINE")
        print("=" * 60)
        print(f"Stockfish path : {self.stockfish_path}")
        print(f"Search depth   : {self.depth}")
        print(f"ELO            : {self.elo}")
        print()

        self.engine = chess.engine.SimpleEngine.popen_uci(
            self.stockfish_path
        )

        # Limit playing strength
        self.engine.configure({
            "UCI_LimitStrength": True,
            "UCI_Elo": self.elo
        })

    # --------------------------------------------------------
    # GET BEST MOVE
    # --------------------------------------------------------

    def get_best_move(self, fen):

        board = chess.Board(fen)

        result = self.engine.analyse(
            board,
            chess.engine.Limit(depth=self.depth)
        )

        move = result["pv"][0]

        return move.uci()

    # --------------------------------------------------------
    # GET BEST MOVE + UPDATED FEN
    # --------------------------------------------------------

    def get_best_move_and_fen(self, fen):

        board = chess.Board(fen)

        result = self.engine.analyse(
            board,
            chess.engine.Limit(depth=self.depth)
        )

        move = result["pv"][0]

        # Apply Stockfish's move to the board
        board.push(move)

        updated_fen = board.fen()

        return move.uci(), updated_fen

    # --------------------------------------------------------
    # CLOSE ENGINE
    # --------------------------------------------------------

    def close(self):

        if self.engine:
            self.engine.quit()
            self.engine = None


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    engine = StockfishEngine()

    try:

        # Example position
        fen = "rnbqkb1r/pppp1ppp/4pn2/8/2PP4/5N2/PP2PPPP/RNBQKB1R b KQkq - 1 3"

        print("FEN:")
        print(fen)
        print()

        move, new_fen = engine.get_best_move_and_fen(fen)

        print("Stockfish move:")
        print(move)

        print()
        print("FEN after Stockfish move:")
        print(new_fen)

    finally:
        engine.close()