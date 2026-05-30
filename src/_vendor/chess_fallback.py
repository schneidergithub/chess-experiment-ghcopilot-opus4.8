"""Minimal pure-Python chess implementation — FALLBACK ONLY.

Implements just enough of the python-chess API used by this project:
- WHITE / BLACK constants
- square(file, rank) -> 0..63 (a1 = 0, file-major as in python-chess)
- square_file / square_rank
- Piece (symbol), Move (uci <-> object), Board

The Board supports FEN parsing, piece lookup, pseudo-legal + legal move
generation with full check detection (so puzzle solutions validate), SAN
generation, and push(). Castling, en passant, and promotion are supported
well enough for typical Lichess puzzle solutions.

This is NOT a complete or competition-grade engine; it exists so the pipeline
runs offline. When python-chess is installed, this module is never used.
"""

from __future__ import annotations

WHITE = True
BLACK = False

# Square indexing matches python-chess: a1=0, b1=1, ..., h1=7, a2=8, ..., h8=63
def square(file_index: int, rank_index: int) -> int:
    return rank_index * 8 + file_index


def square_file(sq: int) -> int:
    return sq & 7


def square_rank(sq: int) -> int:
    return sq >> 3


_FILES = "abcdefgh"


def square_name(sq: int) -> str:
    return f"{_FILES[square_file(sq)]}{square_rank(sq) + 1}"


def parse_square(name: str) -> int:
    f = _FILES.index(name[0])
    r = int(name[1]) - 1
    return square(f, r)


class Piece:
    __slots__ = ("piece_type", "color", "_symbol")

    def __init__(self, symbol: str):
        self._symbol = symbol
        self.color = WHITE if symbol.isupper() else BLACK
        self.piece_type = symbol.upper()

    def symbol(self) -> str:
        return self._symbol

    def __repr__(self) -> str:
        return f"Piece('{self._symbol}')"


class Move:
    __slots__ = ("from_square", "to_square", "promotion")

    def __init__(self, from_square: int, to_square: int, promotion: str | None = None):
        self.from_square = from_square
        self.to_square = to_square
        self.promotion = promotion  # lowercase piece letter or None

    @classmethod
    def from_uci(cls, uci: str) -> "Move":
        if len(uci) < 4:
            raise ValueError(f"invalid uci: {uci}")
        frm = parse_square(uci[0:2])
        to = parse_square(uci[2:4])
        promo = uci[4].lower() if len(uci) >= 5 else None
        return cls(frm, to, promo)

    def uci(self) -> str:
        s = square_name(self.from_square) + square_name(self.to_square)
        if self.promotion:
            s += self.promotion
        return s

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Move)
            and self.from_square == other.from_square
            and self.to_square == other.to_square
            and (self.promotion or None) == (other.promotion or None)
        )

    def __hash__(self) -> int:
        return hash((self.from_square, self.to_square, self.promotion))

    def __repr__(self) -> str:
        return f"Move.from_uci('{self.uci()}')"


_DIRS = {
    "N": [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)],
    "K": [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)],
}
_SLIDE = {
    "B": [(1, 1), (1, -1), (-1, 1), (-1, -1)],
    "R": [(1, 0), (-1, 0), (0, 1), (0, -1)],
    "Q": [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)],
}


class Board:
    def __init__(self, fen: str | None = None):
        self.squares: list[Piece | None] = [None] * 64
        self.turn = WHITE
        self.castling = ""
        self.ep_square: int | None = None
        if fen is None:
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        self._load_fen(fen)

    def _load_fen(self, fen: str) -> None:
        parts = fen.split()
        if len(parts) < 2:
            raise ValueError(f"invalid FEN: {fen}")
        placement = parts[0]
        ranks = placement.split("/")
        if len(ranks) != 8:
            raise ValueError(f"invalid FEN ranks: {fen}")
        for r_idx, row in enumerate(ranks):
            rank = 7 - r_idx
            file = 0
            for ch in row:
                if ch.isdigit():
                    file += int(ch)
                else:
                    if file > 7:
                        raise ValueError(f"invalid FEN row: {row}")
                    self.squares[square(file, rank)] = Piece(ch)
                    file += 1
            if file != 8:
                raise ValueError(f"invalid FEN row width: {row}")
        self.turn = WHITE if parts[1] == "w" else BLACK
        self.castling = parts[2] if len(parts) > 2 and parts[2] != "-" else ""
        if len(parts) > 3 and parts[3] != "-":
            self.ep_square = parse_square(parts[3])
        else:
            self.ep_square = None

    def copy(self) -> "Board":
        b = Board.__new__(Board)
        b.squares = list(self.squares)
        b.turn = self.turn
        b.castling = self.castling
        b.ep_square = self.ep_square
        return b

    def piece_at(self, sq: int) -> Piece | None:
        return self.squares[sq]

    def king_square(self, color: bool) -> int | None:
        target = "K" if color == WHITE else "k"
        for sq, p in enumerate(self.squares):
            if p is not None and p.symbol() == target:
                return sq
        return None

    def _attacks_from(self, sq: int, piece: Piece) -> list[int]:
        f = square_file(sq)
        r = square_rank(sq)
        out: list[int] = []
        pt = piece.piece_type
        if pt == "P":
            direction = 1 if piece.color == WHITE else -1
            for df in (-1, 1):
                nf, nr = f + df, r + direction
                if 0 <= nf < 8 and 0 <= nr < 8:
                    out.append(square(nf, nr))
        elif pt in _DIRS:
            for df, dr in _DIRS[pt]:
                nf, nr = f + df, r + dr
                if 0 <= nf < 8 and 0 <= nr < 8:
                    out.append(square(nf, nr))
        elif pt in _SLIDE:
            for df, dr in _SLIDE[pt]:
                nf, nr = f + df, r + dr
                while 0 <= nf < 8 and 0 <= nr < 8:
                    s = square(nf, nr)
                    out.append(s)
                    if self.squares[s] is not None:
                        break
                    nf += df
                    nr += dr
        return out

    def is_attacked_by(self, color: bool, sq: int) -> bool:
        for s, p in enumerate(self.squares):
            if p is None or p.color != color:
                continue
            if sq in self._attacks_from(s, p):
                return True
        return False

    def is_check(self) -> bool:
        ks = self.king_square(self.turn)
        if ks is None:
            return False
        return self.is_attacked_by(not self.turn, ks)

    def _pseudo_legal(self) -> list[Move]:
        moves: list[Move] = []
        for sq, p in enumerate(self.squares):
            if p is None or p.color != self.turn:
                continue
            f = square_file(sq)
            r = square_rank(sq)
            pt = p.piece_type
            if pt == "P":
                direction = 1 if p.color == WHITE else -1
                start_rank = 1 if p.color == WHITE else 6
                promo_rank = 7 if p.color == WHITE else 0
                one = square(f, r + direction) if 0 <= r + direction < 8 else None
                if one is not None and self.squares[one] is None:
                    self._add_pawn(moves, sq, one, r + direction == promo_rank)
                    if r == start_rank:
                        two = square(f, r + 2 * direction)
                        if self.squares[two] is None:
                            moves.append(Move(sq, two))
                for df in (-1, 1):
                    nf, nr = f + df, r + direction
                    if 0 <= nf < 8 and 0 <= nr < 8:
                        t = square(nf, nr)
                        tp = self.squares[t]
                        if tp is not None and tp.color != p.color:
                            self._add_pawn(moves, sq, t, nr == promo_rank)
                        elif t == self.ep_square:
                            moves.append(Move(sq, t))
            else:
                for t in self._attacks_from(sq, p):
                    tp = self.squares[t]
                    if tp is None or tp.color != p.color:
                        moves.append(Move(sq, t))
        moves.extend(self._castling_moves())
        return moves

    def _add_pawn(self, moves: list[Move], frm: int, to: int, promo: bool) -> None:
        if promo:
            for pr in ("q", "r", "b", "n"):
                moves.append(Move(frm, to, pr))
        else:
            moves.append(Move(frm, to))

    def _castling_moves(self) -> list[Move]:
        out: list[Move] = []
        if self.is_check():
            return out
        if self.turn == WHITE:
            king_from = parse_square("e1")
            if self.squares[king_from] and self.squares[king_from].symbol() == "K":
                if "K" in self.castling and self._clear_unattacked(["f1", "g1"], "e1"):
                    if self.squares[parse_square("h1")] and self.squares[parse_square("h1")].symbol() == "R":
                        out.append(Move(king_from, parse_square("g1")))
                if "Q" in self.castling and self._clear_unattacked(["d1", "c1"], "e1") and self.squares[parse_square("b1")] is None:
                    if self.squares[parse_square("a1")] and self.squares[parse_square("a1")].symbol() == "R":
                        out.append(Move(king_from, parse_square("c1")))
        else:
            king_from = parse_square("e8")
            if self.squares[king_from] and self.squares[king_from].symbol() == "k":
                if "k" in self.castling and self._clear_unattacked(["f8", "g8"], "e8"):
                    if self.squares[parse_square("h8")] and self.squares[parse_square("h8")].symbol() == "r":
                        out.append(Move(king_from, parse_square("g8")))
                if "q" in self.castling and self._clear_unattacked(["d8", "c8"], "e8") and self.squares[parse_square("b8")] is None:
                    if self.squares[parse_square("a8")] and self.squares[parse_square("a8")].symbol() == "r":
                        out.append(Move(king_from, parse_square("c8")))
        return out

    def _clear_unattacked(self, names: list[str], king_name: str) -> bool:
        for n in names:
            if self.squares[parse_square(n)] is not None:
                return False
            if self.is_attacked_by(not self.turn, parse_square(n)):
                return False
        return True

    def _apply(self, move: Move) -> None:
        piece = self.squares[move.from_square]
        if piece is None:
            return
        # En passant capture
        if piece.piece_type == "P" and move.to_square == self.ep_square and self.squares[move.to_square] is None:
            cap_rank = square_rank(move.from_square)
            cap_sq = square(square_file(move.to_square), cap_rank)
            self.squares[cap_sq] = None
        self.squares[move.from_square] = None
        # Promotion
        if move.promotion:
            sym = move.promotion.upper() if piece.color == WHITE else move.promotion.lower()
            self.squares[move.to_square] = Piece(sym)
        else:
            self.squares[move.to_square] = piece
        # Castling rook movement
        if piece.piece_type == "K":
            df = square_file(move.to_square) - square_file(move.from_square)
            if abs(df) == 2:
                r = square_rank(move.from_square)
                if df > 0:  # king side
                    rook = self.squares[square(7, r)]
                    self.squares[square(7, r)] = None
                    self.squares[square(5, r)] = rook
                else:
                    rook = self.squares[square(0, r)]
                    self.squares[square(0, r)] = None
                    self.squares[square(3, r)] = rook
        # Update ep square
        self.ep_square = None
        if piece.piece_type == "P" and abs(square_rank(move.to_square) - square_rank(move.from_square)) == 2:
            mid = (move.to_square + move.from_square) // 2
            self.ep_square = mid

    @property
    def legal_moves(self) -> list[Move]:
        legal: list[Move] = []
        for mv in self._pseudo_legal():
            trial = self.copy()
            trial._apply(mv)
            ks = trial.king_square(self.turn)
            if ks is None or not trial.is_attacked_by(not self.turn, ks):
                legal.append(mv)
        return legal

    def is_legal(self, move: Move) -> bool:
        return any(move == m for m in self.legal_moves)

    def san(self, move: Move) -> str:
        piece = self.squares[move.from_square]
        if piece is None:
            return move.uci()
        pt = piece.piece_type
        # Castling
        if pt == "K" and abs(square_file(move.to_square) - square_file(move.from_square)) == 2:
            san = "O-O" if square_file(move.to_square) == 6 else "O-O-O"
        else:
            capture = self.squares[move.to_square] is not None or (
                pt == "P" and move.to_square == self.ep_square
            )
            dest = square_name(move.to_square)
            if pt == "P":
                san = (f"{_FILES[square_file(move.from_square)]}x" if capture else "") + dest
                if move.promotion:
                    san += "=" + move.promotion.upper()
            else:
                disamb = self._disambiguation(move, piece)
                san = pt + disamb + ("x" if capture else "") + dest
        # Check / checkmate suffix
        trial = self.copy()
        trial._apply(move)
        trial.turn = not self.turn
        if trial.is_check():
            san += "#" if not trial.legal_moves else "+"
        return san

    def _disambiguation(self, move: Move, piece: Piece) -> str:
        others = []
        for sq, p in enumerate(self.squares):
            if sq == move.from_square or p is None:
                continue
            if p.color == piece.color and p.piece_type == piece.piece_type:
                if move.to_square in self._attacks_from(sq, p):
                    # ensure that move would be legal-ish (same target reachable)
                    others.append(sq)
        if not others:
            return ""
        same_file = any(square_file(s) == square_file(move.from_square) for s in others)
        same_rank = any(square_rank(s) == square_rank(move.from_square) for s in others)
        if not same_file:
            return _FILES[square_file(move.from_square)]
        if not same_rank:
            return str(square_rank(move.from_square) + 1)
        return square_name(move.from_square)

    def push(self, move: Move) -> None:
        # Update castling rights on king/rook movement or rook capture.
        piece = self.squares[move.from_square]
        self._apply(move)
        if piece is not None:
            if piece.symbol() == "K":
                self.castling = self.castling.replace("K", "").replace("Q", "")
            elif piece.symbol() == "k":
                self.castling = self.castling.replace("k", "").replace("q", "")
            elif piece.symbol() == "R":
                if move.from_square == parse_square("h1"):
                    self.castling = self.castling.replace("K", "")
                elif move.from_square == parse_square("a1"):
                    self.castling = self.castling.replace("Q", "")
            elif piece.symbol() == "r":
                if move.from_square == parse_square("h8"):
                    self.castling = self.castling.replace("k", "")
                elif move.from_square == parse_square("a8"):
                    self.castling = self.castling.replace("q", "")
        self.turn = not self.turn
