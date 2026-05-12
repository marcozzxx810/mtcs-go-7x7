from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from go_game import DRAW, Move, PASS_MOVE, GoGame, opponent


@dataclass
class MCTSNode:
    state: GoGame
    parent: "MCTSNode | None"
    move: Move
    # Wins are credited from the perspective of the player who just moved
    # into this node's board state (i.e. opponent of state.current_player).
    player_just_moved: int
    untried_moves: list[Move] | None = None
    children: list["MCTSNode"] = field(default_factory=list)
    visits: int = 0
    wins: float = 0.0

    def best_child(self, exploration: float) -> "MCTSNode":
        log_parent = math.log(max(self.visits, 1))

        def score(child: MCTSNode) -> float:
            if child.visits == 0:
                return float("inf")
            exploitation = child.wins / child.visits
            exploration_term = exploration * math.sqrt(log_parent / child.visits)
            return exploitation + exploration_term

        return max(self.children, key=score)


@dataclass
class MCTSResult:
    move: Move
    root: MCTSNode
    nodes_created: int


class MCTS:
    def __init__(
        self,
        simulations: int = 300,
        exploration: float = 1.414,
        rollout_limit: int | None = None,  # None → 2 × board_size² per rollout
        rng: random.Random | None = None,
    ) -> None:
        self.simulations = simulations
        self.exploration = exploration
        self.rollout_limit = rollout_limit
        self.rng = rng if rng is not None else random.Random()
        self.nodes_created = 0

    def search(self, state: GoGame) -> MCTSResult:
        legal_moves = state.legal_moves()
        if not legal_moves:
            return MCTSResult(PASS_MOVE, self._make_node(state, None, None, []), 1)

        self.rng.shuffle(legal_moves)
        root = self._make_node(state, None, None, legal_moves)
        self.nodes_created = 1

        for _ in range(self.simulations):
            node = self._select_and_expand(root)
            winner = self._simulate(node.state)
            self._backpropagate(node, winner)

        if not root.children:
            return MCTSResult(PASS_MOVE, root, self.nodes_created)

        # Robust-child selection: most visited, tie-broken by win rate.
        best = max(
            root.children,
            key=lambda child: (
                child.visits,
                child.wins / child.visits if child.visits else 0.0,
            ),
        )
        return MCTSResult(best.move, root, self.nodes_created)

    def _make_node(
        self,
        state: GoGame,
        parent: MCTSNode | None,
        move: Move,
        untried_moves: list[Move] | None = None,
    ) -> MCTSNode:
        player_just_moved = -state.current_player
        return MCTSNode(
            state=state,
            parent=parent,
            move=move,
            player_just_moved=player_just_moved,
            untried_moves=untried_moves,
        )

    def _select_and_expand(self, root: MCTSNode) -> MCTSNode:
        node = root
        while not node.state.is_over():
            untried_moves = self._untried_moves(node)
            if untried_moves:
                move = untried_moves.pop()
                child_state = node.state.apply_move(move)
                child = self._make_node(child_state, node, move)
                node.children.append(child)
                self.nodes_created += 1
                return child
            if not node.children:
                return node
            node = node.best_child(self.exploration)
        return node

    def _untried_moves(self, node: MCTSNode) -> list[Move]:
        if node.untried_moves is None:
            node.untried_moves = node.state.legal_moves()
            self.rng.shuffle(node.untried_moves)
        return node.untried_moves

    def _simulate(self, state: GoGame) -> int:
        rollout_state = state.clone()
        # Rollout limit is a secondary safeguard; game.is_over() (double-pass
        # or max_moves cap) is the normal termination signal.
        limit = (
            self.rollout_limit
            if self.rollout_limit is not None
            else state.board_size * state.board_size * 2
        )
        steps = 0
        while not rollout_state.is_over() and steps < limit:
            move = self._rollout_move(rollout_state)
            rollout_state = rollout_state.apply_move(move)
            steps += 1
        return rollout_state.winner()

    # ------------------------------------------------------------------
    # Heuristic rollout policy
    # ------------------------------------------------------------------
    # Priority chain (first match wins):
    #   1. Capture opponent stones (prefer larger captures).
    #   2. Avoid obvious self-atari that would lose ≥1 stone for free.
    #   3. Play near existing stones (proximity heuristic).
    #   4. Random legal non-pass move.
    #   5. Pass — only when no useful non-pass moves remain.
    # ------------------------------------------------------------------

    def _rollout_move(self, state: GoGame) -> Move:
        legal_non_pass = [m for m in state.empty_points() if state.is_legal_move(m)]

        if not legal_non_pass:
            return PASS_MOVE

        # Skip filling own eyes — doing so never gains territory.
        non_eye = [m for m in legal_non_pass if not self._is_own_eye(state, m)]
        if not non_eye:
            return PASS_MOVE  # Only eye-fills remain; passing is correct play.

        # 1. Capture moves: prioritise the largest capture available.
        captures = self._find_captures(state, non_eye)
        if captures:
            max_size = max(n for _, n in captures)
            best = [m for m, n in captures if n == max_size]
            return self.rng.choice(best)

        # 2. Filter out obvious bad self-atari moves.
        safe = [m for m in non_eye if not self._is_bad_selfatari(state, m)]
        candidates = safe if safe else non_eye  # don't pass if all moves look risky

        # 3. Prefer moves adjacent to existing stones over isolated plays.
        near = [m for m in candidates if self._has_stone_neighbor(state, m)]
        if near:
            return self.rng.choice(near)

        # 4. Random legal non-pass fallback.
        return self.rng.choice(candidates)

    def _is_own_eye(self, state: GoGame, move: tuple[int, int]) -> bool:
        """True if every neighbour of `move` belongs to the current player."""
        row, col = move
        player = state.current_player
        return all(state.board[nr][nc] == player for nr, nc in state.neighbors(row, col))

    def _find_captures(
        self, state: GoGame, moves: list[tuple[int, int]]
    ) -> list[tuple[tuple[int, int], int]]:
        """Return (move, stones_captured) for every move that takes ≥1 opponent stone."""
        opp = opponent(state.current_player)
        result: list[tuple[tuple[int, int], int]] = []
        for move in moves:
            row, col = move
            n_captured = 0
            seen: set[tuple[int, int]] = set()
            for nr, nc in state.neighbors(row, col):
                if state.board[nr][nc] == opp and (nr, nc) not in seen:
                    group, liberties = state._collect_group(state.board, nr, nc)
                    seen.update(group)
                    # Group has exactly one liberty remaining (this move's point).
                    if liberties == {(row, col)}:
                        n_captured += len(group)
            if n_captured > 0:
                result.append((move, n_captured))
        return result

    def _is_bad_selfatari(self, state: GoGame, move: tuple[int, int]) -> bool:
        """True if the move leaves own group with ≤1 liberty that is flanked by opponents.

        Avoids moves that hand stones to the opponent with no compensating
        capture.  We skip this check when the move also captures (handled
        above), so we only need to evaluate the no-capture branch here.
        """
        row, col = move
        player = state.current_player
        opp = opponent(player)

        # Simulate placement (no captures possible here, checked above).
        board_lists = [list(r) for r in state.board]
        board_lists[row][col] = player

        _, own_liberties = state._collect_group(board_lists, row, col)

        if len(own_liberties) > 1:
            return False  # Multiple liberties — safe.

        if not own_liberties:
            return True  # Zero liberties = suicide (shouldn't be legal, but guard it).

        # Single liberty left: risky if that liberty is heavily attacked.
        lib_r, lib_c = next(iter(own_liberties))
        opp_pressure = sum(
            1 for nr, nc in state.neighbors(lib_r, lib_c)
            if state.board[nr][nc] == opp
        )
        return opp_pressure >= 2

    def _has_stone_neighbor(self, state: GoGame, move: tuple[int, int]) -> bool:
        """True if `move` is adjacent to at least one stone (any colour)."""
        row, col = move
        return any(state.board[nr][nc] != 0 for nr, nc in state.neighbors(row, col))

    def _backpropagate(self, node: MCTSNode, winner: int) -> None:
        while node is not None:
            node.visits += 1
            if winner == DRAW:
                node.wins += 0.5
            elif winner == node.player_just_moved:
                node.wins += 1.0
            node = node.parent
