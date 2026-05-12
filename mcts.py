from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from go_game import BOARD_SIZE, DRAW, Move, PASS_MOVE, GoGame


@dataclass
class MCTSNode:
    state: GoGame
    parent: "MCTSNode | None"
    move: Move
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
        rollout_limit: int = BOARD_SIZE * BOARD_SIZE,
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
        steps = 0

        while not rollout_state.is_over() and steps < self.rollout_limit:
            move = self._rollout_move(rollout_state)
            rollout_state = rollout_state.apply_move(move)
            steps += 1

        return rollout_state.winner()

    def _rollout_move(self, state: GoGame) -> Move:
        empties = state.empty_points()
        if not empties or self.rng.random() < 0.06:
            return PASS_MOVE

        attempts = min(4, len(empties))
        for _ in range(attempts):
            move = self.rng.choice(empties)
            if state.is_legal_move(move):
                return move

        return PASS_MOVE

    def _backpropagate(self, node: MCTSNode, winner: int) -> None:
        while node is not None:
            node.visits += 1
            if winner == DRAW:
                node.wins += 0.5
            elif winner == node.player_just_moved:
                node.wins += 1.0
            node = node.parent
