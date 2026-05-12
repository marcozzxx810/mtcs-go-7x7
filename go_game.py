from __future__ import annotations

from collections import deque
from typing import Iterable, Sequence


BOARD_SIZE = 7
EMPTY = 0
BLACK = 1
WHITE = -1
DRAW = 0
PASS_MOVE = None
MAX_MOVES = BOARD_SIZE * BOARD_SIZE

Move = tuple[int, int] | None
Board = tuple[tuple[int, ...], ...]


def opponent(player: int) -> int:
    return -player


def player_name(player: int) -> str:
    if player == BLACK:
        return "黑方"
    if player == WHITE:
        return "白方"
    return "平局"


def new_board() -> Board:
    return tuple(tuple(EMPTY for _ in range(BOARD_SIZE)) for _ in range(BOARD_SIZE))


class GoGame:
    """Immutable 7x7 Go state with simplified Chinese area scoring."""

    __slots__ = (
        "board",
        "current_player",
        "previous_board",
        "consecutive_passes",
        "move_count",
        "last_move",
        "_legal_moves_cache",
    )

    def __init__(
        self,
        board: Board | None = None,
        current_player: int = BLACK,
        previous_board: Board | None = None,
        consecutive_passes: int = 0,
        move_count: int = 0,
        last_move: Move = None,
    ) -> None:
        self.board = board if board is not None else new_board()
        self.current_player = current_player
        self.previous_board = previous_board
        self.consecutive_passes = consecutive_passes
        self.move_count = move_count
        self.last_move = last_move
        self._legal_moves_cache: list[Move] | None = None

    def clone(self) -> "GoGame":
        return GoGame(
            board=self.board,
            current_player=self.current_player,
            previous_board=self.previous_board,
            consecutive_passes=self.consecutive_passes,
            move_count=self.move_count,
            last_move=self.last_move,
        )

    def is_over(self) -> bool:
        return (
            self.consecutive_passes >= 2
            or self.move_count >= MAX_MOVES
            or all(cell != EMPTY for row in self.board for cell in row)
        )

    def neighbors(self, row: int, col: int) -> Iterable[tuple[int, int]]:
        if row > 0:
            yield row - 1, col
        if row < BOARD_SIZE - 1:
            yield row + 1, col
        if col > 0:
            yield row, col - 1
        if col < BOARD_SIZE - 1:
            yield row, col + 1

    def empty_points(self) -> list[tuple[int, int]]:
        return [
            (row, col)
            for row in range(BOARD_SIZE)
            for col in range(BOARD_SIZE)
            if self.board[row][col] == EMPTY
        ]

    def legal_moves(self, include_pass: bool = True) -> list[Move]:
        if self.is_over():
            return []
        if include_pass and self._legal_moves_cache is not None:
            return list(self._legal_moves_cache)

        moves: list[Move] = []
        for move in self.empty_points():
            if self.is_legal_move(move):
                moves.append(move)
        if include_pass:
            moves.append(PASS_MOVE)
            self._legal_moves_cache = list(moves)
        return moves

    def is_legal_move(self, move: Move) -> bool:
        if self.is_over():
            return False
        if move is PASS_MOVE:
            return True
        row, col = move
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            return False
        if self.board[row][col] != EMPTY:
            return False

        captures = False
        connects_to_live_group = False
        for nr, nc in self.neighbors(row, col):
            value = self.board[nr][nc]
            if value == EMPTY:
                return True

            group, liberties = self._collect_group(self.board, nr, nc)
            liberties_without_move = liberties - {(row, col)}
            if value == opponent(self.current_player) and not liberties_without_move:
                captures = True
            elif value == self.current_player and liberties_without_move:
                connects_to_live_group = True

        if captures:
            return self._next_board_for_move(move) is not None
        return connects_to_live_group

    def apply_move(self, move: Move) -> "GoGame":
        if move is PASS_MOVE:
            if not self.is_legal_move(move):
                raise ValueError("游戏已经结束，不能继续 pass。")
            return GoGame(
                board=self.board,
                current_player=opponent(self.current_player),
                previous_board=self.board,
                consecutive_passes=self.consecutive_passes + 1,
                move_count=self.move_count + 1,
                last_move=PASS_MOVE,
            )

        next_board = self._next_board_for_move(move)
        if next_board is None:
            raise ValueError(f"非法落子：{format_move(move)}")
        return GoGame(
            board=next_board,
            current_player=opponent(self.current_player),
            previous_board=self.board,
            consecutive_passes=0,
            move_count=self.move_count + 1,
            last_move=move,
        )

    def try_apply_move(self, move: Move) -> "GoGame | None":
        if not self.is_legal_move(move):
            return None
        return self.apply_move(move)

    def _next_board_for_move(self, move: tuple[int, int]) -> Board | None:
        row, col = move
        board_lists = [list(board_row) for board_row in self.board]
        board_lists[row][col] = self.current_player

        captured: set[tuple[int, int]] = set()
        for nr, nc in self.neighbors(row, col):
            if board_lists[nr][nc] == opponent(self.current_player):
                group, liberties = self._collect_group(board_lists, nr, nc)
                if not liberties:
                    captured.update(group)

        for cr, cc in captured:
            board_lists[cr][cc] = EMPTY

        own_group, own_liberties = self._collect_group(board_lists, row, col)
        if not own_group or not own_liberties:
            return None

        next_board = tuple(tuple(board_row) for board_row in board_lists)
        if self.previous_board is not None and next_board == self.previous_board:
            return None
        return next_board

    def _collect_group(
        self, board: Sequence[Sequence[int]], row: int, col: int
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        color = board[row][col]
        if color == EMPTY:
            return set(), set()

        group: set[tuple[int, int]] = set()
        liberties: set[tuple[int, int]] = set()
        queue: deque[tuple[int, int]] = deque([(row, col)])
        group.add((row, col))

        while queue:
            r, c = queue.popleft()
            for nr, nc in self.neighbors(r, c):
                value = board[nr][nc]
                if value == EMPTY:
                    liberties.add((nr, nc))
                elif value == color and (nr, nc) not in group:
                    group.add((nr, nc))
                    queue.append((nr, nc))
        return group, liberties

    def area_score(self) -> tuple[int, int]:
        black_score = 0
        white_score = 0
        visited: set[tuple[int, int]] = set()

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                value = self.board[row][col]
                if value == BLACK:
                    black_score += 1
                elif value == WHITE:
                    white_score += 1
                elif (row, col) not in visited:
                    region, borders = self._empty_region(row, col, visited)
                    if borders == {BLACK}:
                        black_score += len(region)
                    elif borders == {WHITE}:
                        white_score += len(region)

        return black_score, white_score

    def _empty_region(
        self, row: int, col: int, visited: set[tuple[int, int]]
    ) -> tuple[set[tuple[int, int]], set[int]]:
        region: set[tuple[int, int]] = set()
        borders: set[int] = set()
        queue: deque[tuple[int, int]] = deque([(row, col)])
        visited.add((row, col))
        region.add((row, col))

        while queue:
            r, c = queue.popleft()
            for nr, nc in self.neighbors(r, c):
                value = self.board[nr][nc]
                if value == EMPTY and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    region.add((nr, nc))
                    queue.append((nr, nc))
                elif value in (BLACK, WHITE):
                    borders.add(value)
        return region, borders

    def winner(self) -> int:
        black_score, white_score = self.area_score()
        if black_score > white_score:
            return BLACK
        if white_score > black_score:
            return WHITE
        return DRAW

    def render(self) -> str:
        header = "   " + " ".join(chr(ord("A") + col) for col in range(BOARD_SIZE))
        lines = [header]
        symbols = {EMPTY: ".", BLACK: "X", WHITE: "O"}
        for row in range(BOARD_SIZE):
            line = f"{row + 1:>2} " + " ".join(
                symbols[self.board[row][col]] for col in range(BOARD_SIZE)
            )
            lines.append(line)
        return "\n".join(lines)


def format_move(move: Move) -> str:
    if move is PASS_MOVE:
        return "pass"
    row, col = move
    return f"{chr(ord('A') + col)}{row + 1}"


def parse_move(text: str) -> Move:
    raw = text.strip().lower()
    if raw in {"pass", "p", "跳过"}:
        return PASS_MOVE

    if len(raw) >= 2 and raw[0].isalpha() and raw[1:].isdigit():
        col = ord(raw[0].upper()) - ord("A")
        row = int(raw[1:]) - 1
        return row, col

    normalized = raw.replace(",", " ").replace("，", " ")
    parts = [part for part in normalized.split() if part]
    if len(parts) == 2 and all(part.isdigit() for part in parts):
        row = int(parts[0]) - 1
        col = int(parts[1]) - 1
        return row, col

    raise ValueError("请输入坐标，例如 D4、4 4，或 pass。")
