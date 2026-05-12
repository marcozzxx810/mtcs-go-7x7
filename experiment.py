from __future__ import annotations

import argparse
import csv
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from go_game import BLACK, DEFAULT_KOMI, WHITE, GoGame
from mcts import MCTS


RESULT_PATH = Path("results/experiment_results.csv")

# Preset experiment configurations
PRESETS: dict[str, dict] = {
    "quick": {
        "simulations": [50, 100, 300],
        "ucts": [1.414],
        "games": 3,
        "description": "快速模式：3 种模拟次数 × 1 UCT × 3 局 = 9 局（约 2–5 分钟）",
    },
    "serious": {
        "simulations": [50, 100, 200, 300, 500],
        "ucts": [0.5, 1.414, 2.0],
        "games": 5,
        "description": "完整模式：5 种模拟次数 × 3 UCT × 5 局 = 75 局（约 20–40 分钟）",
    },
}


def play_selfplay_game(
    simulations: int,
    exploration: float,
    seed: int,
    board_size: int = 7,
    komi: float = DEFAULT_KOMI,
) -> dict[str, float | int]:
    rng = random.Random(seed)
    game = GoGame(board_size=board_size, komi=komi)
    total_time = 0.0
    total_nodes = 0
    searches = 0

    while not game.is_over():
        start = time.perf_counter()
        result = MCTS(simulations=simulations, exploration=exploration, rng=rng).search(game)
        elapsed = time.perf_counter() - start
        game = game.apply_move(result.move)
        total_time += elapsed
        total_nodes += result.nodes_created
        searches += 1

    winner = game.winner()
    black_score, white_score_komi = game.final_score()
    score_diff = black_score - white_score_komi  # positive = Black ahead

    return {
        "winner": winner,
        "moves": game.move_count,
        "avg_time_per_move": total_time / max(searches, 1),
        "total_wall_time": total_time,
        "avg_search_nodes": total_nodes / max(searches, 1),
        "score_black": black_score,
        "score_white_komi": white_score_komi,
        "score_diff": score_diff,
    }


def run_experiments(
    simulation_options: list[int],
    uct_options: list[float],
    games_per_group: int,
    seed_base: int,
    board_size: int = 7,
    komi: float = DEFAULT_KOMI,
) -> list[dict[str, float | int]]:
    grouped: dict[tuple[int, float], list[dict[str, float | int]]] = {
        (simulations, exploration): []
        for simulations in simulation_options
        for exploration in uct_options
    }
    workers = os.cpu_count() or 1

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for simulations in simulation_options:
            for exploration in uct_options:
                print(f"提交实验：simulations={simulations}, uct_c={exploration}", flush=True)
                for game_index in range(games_per_group):
                    seed = seed_base + simulations * 10000 + int(exploration * 1000) * 10 + game_index
                    future = executor.submit(
                        play_selfplay_game, simulations, exploration, seed, board_size, komi
                    )
                    futures[future] = (simulations, exploration)

        for future in as_completed(futures):
            key = futures[future]
            grouped[key].append(future.result())
            print(
                f"完成对局：simulations={key[0]}, uct_c={key[1]} "
                f"({len(grouped[key])}/{games_per_group})",
                flush=True,
            )

    rows: list[dict[str, float | int]] = []

    for simulations in simulation_options:
        for exploration in uct_options:
            results = grouped[(simulations, exploration)]
            n = len(results)

            black_wins = sum(1 for r in results if r["winner"] == BLACK)
            white_wins = sum(1 for r in results if r["winner"] == WHITE)
            draws = n - black_wins - white_wins

            avg_time = sum(r["avg_time_per_move"] for r in results) / n
            avg_wall = sum(r["total_wall_time"] for r in results) / n
            avg_moves = sum(r["moves"] for r in results) / n
            avg_nodes = sum(r["avg_search_nodes"] for r in results) / n
            avg_score_diff = sum(r["score_diff"] for r in results) / n

            rows.append(
                {
                    "simulations": simulations,
                    "uct_c": exploration,
                    "games": n,
                    "seed_base": seed_base,
                    "black_wins": black_wins,
                    "white_wins": white_wins,
                    "draws": draws,
                    "black_win_rate": black_wins / n,
                    "white_win_rate": white_wins / n,
                    "avg_time_per_move": avg_time,
                    "avg_total_wall_time": avg_wall,
                    "avg_game_moves": avg_moves,
                    "avg_search_nodes": avg_nodes,
                    "avg_score_diff": avg_score_diff,
                }
            )

    return rows


def save_results(rows: list[dict[str, float | int]]) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "simulations",
        "uct_c",
        "games",
        "seed_base",
        "black_wins",
        "white_wins",
        "draws",
        "black_win_rate",
        "white_win_rate",
        "avg_time_per_move",
        "avg_total_wall_time",
        "avg_game_moves",
        "avg_search_nodes",
        "avg_score_diff",
    ]
    with RESULT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCTS 围棋自我对弈实验",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            f"  {name}: {cfg['description']}" for name, cfg in PRESETS.items()
        ),
    )
    parser.add_argument(
        "--mode",
        choices=list(PRESETS.keys()),
        default="serious",
        help="实验预设（quick=快速验证，serious=完整实验）",
    )
    parser.add_argument("--seed", type=int, default=42, help="基础随机种子（保证复现性）")
    parser.add_argument("--board-size", type=int, choices=[7, 8, 9], default=7, help="棋盘大小")
    parser.add_argument("--komi", type=float, default=DEFAULT_KOMI, help="贴目")
    # Fine-grained overrides (override preset values)
    parser.add_argument(
        "--simulations",
        type=int,
        nargs="+",
        default=None,
        metavar="N",
        help="覆盖预设模拟次数列表，例如 --simulations 100 300 500",
    )
    parser.add_argument(
        "--ucts",
        type=float,
        nargs="+",
        default=None,
        metavar="C",
        help="覆盖预设 UCT 参数列表，例如 --ucts 0.5 1.414",
    )
    parser.add_argument("--games", type=int, default=None, help="覆盖每组对局数")
    args = parser.parse_args()

    preset = PRESETS[args.mode]
    sim_options = args.simulations if args.simulations else preset["simulations"]
    uct_options = args.ucts if args.ucts else preset["ucts"]
    games_per_group = args.games if args.games else preset["games"]

    total_games = len(sim_options) * len(uct_options) * games_per_group
    print(f"实验模式：{args.mode}  共 {total_games} 局")
    print(f"模拟次数：{sim_options}")
    print(f"UCT 参数：{uct_options}")
    print(f"每组对局数：{games_per_group}  棋盘：{args.board_size}×{args.board_size}  贴目：{args.komi}")
    print(f"基础随机种子：{args.seed}")

    rows = run_experiments(
        simulation_options=sim_options,
        uct_options=uct_options,
        games_per_group=games_per_group,
        seed_base=args.seed,
        board_size=args.board_size,
        komi=args.komi,
    )
    save_results(rows)
    print(f"\n实验结果已保存到 {RESULT_PATH}")


if __name__ == "__main__":
    main()
