from __future__ import annotations

import argparse
import random
import time

from go_game import BLACK, WHITE, Move, format_move, parse_move, player_name, GoGame
from mcts import MCTS


def ai_move(game: GoGame, simulations: int, exploration: float, rng: random.Random) -> tuple[Move, float, int]:
    start = time.perf_counter()
    result = MCTS(simulations=simulations, exploration=exploration, rng=rng).search(game)
    elapsed = time.perf_counter() - start
    return result.move, elapsed, result.nodes_created


def print_result(game: GoGame) -> None:
    black_score, white_score = game.area_score()
    winner = game.winner()
    print(game.render())
    print(f"终局得分：黑方 {black_score}，白方 {white_score}")
    print(f"胜者：{player_name(winner)}")


def run_human_game(simulations: int, exploration: float, seed: int | None) -> None:
    rng = random.Random(seed)
    game = GoGame()
    print("7x7 围棋人机对战。你执黑棋 X，AI 执白棋 O。")
    print("输入示例：D4、4 4 或 pass。")

    while not game.is_over():
        print()
        print(game.render())
        print(f"当前回合：{player_name(game.current_player)}")

        if game.current_player == BLACK:
            while True:
                try:
                    move = parse_move(input("你的落子："))
                    if game.is_legal_move(move):
                        game = game.apply_move(move)
                        break
                    print("非法落子，请重新输入。")
                except ValueError as exc:
                    print(exc)
        else:
            move, elapsed, nodes = ai_move(game, simulations, exploration, rng)
            print(f"AI 落子：{format_move(move)}，耗时 {elapsed:.3f}s，搜索节点 {nodes}")
            game = game.apply_move(move)

    print()
    print_result(game)


def run_selfplay(simulations: int, exploration: float, seed: int | None) -> None:
    rng = random.Random(seed)
    game = GoGame()
    total_time = 0.0
    total_nodes = 0

    print("7x7 围棋 AI 自我对弈开始。")
    while not game.is_over():
        move, elapsed, nodes = ai_move(game, simulations, exploration, rng)
        total_time += elapsed
        total_nodes += nodes
        print(
            f"{game.move_count + 1:02d}. {player_name(game.current_player)} "
            f"{format_move(move):>4}  time={elapsed:.3f}s nodes={nodes}"
        )
        game = game.apply_move(move)

    print()
    print_result(game)
    print(f"总步数：{game.move_count}")
    print(f"平均每步耗时：{total_time / max(game.move_count, 1):.3f}s")
    print(f"平均搜索节点数：{total_nodes / max(game.move_count, 1):.1f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="基于 MCTS 的 7x7 围棋决策程序")
    parser.add_argument("--mode", choices=["human", "selfplay"], default="human", help="运行模式")
    parser.add_argument("--simulations", type=int, default=300, help="每步 MCTS 模拟次数")
    parser.add_argument("--uct", type=float, default=1.414, help="UCT 探索参数 c")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    args = parser.parse_args()

    if args.mode == "selfplay":
        run_selfplay(args.simulations, args.uct, args.seed)
    else:
        run_human_game(args.simulations, args.uct, args.seed)


if __name__ == "__main__":
    main()
