from __future__ import annotations

import csv
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from go_game import BLACK, WHITE, GoGame
from mcts import MCTS


SIMULATION_OPTIONS = [100, 300, 500, 700, 900, 1000]
UCT_OPTIONS = [0.5, 1.414, 2.0]
GAMES_PER_GROUP = 5
RESULT_PATH = Path("results/experiment_results.csv")


def play_selfplay_game(simulations: int, exploration: float, seed: int) -> dict[str, float | int]:
    rng = random.Random(seed)
    game = GoGame()
    total_time = 0.0
    total_nodes = 0
    searches = 0

    while not game.is_over():
        start = time.perf_counter()
        result = MCTS(
            simulations=simulations,
            exploration=exploration,
            rollout_limit=16,
            rng=rng,
        ).search(game)
        elapsed = time.perf_counter() - start
        game = game.apply_move(result.move)

        total_time += elapsed
        total_nodes += result.nodes_created
        searches += 1

    winner = game.winner()
    return {
        "winner": winner,
        "moves": game.move_count,
        "avg_time_per_move": total_time / max(searches, 1),
        "avg_search_nodes": total_nodes / max(searches, 1),
    }


def run_experiments() -> list[dict[str, float | int]]:
    grouped: dict[tuple[int, float], list[dict[str, float | int]]] = {
        (simulations, exploration): []
        for simulations in SIMULATION_OPTIONS
        for exploration in UCT_OPTIONS
    }
    workers = min(4, os.cpu_count() or 1)

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for simulations in SIMULATION_OPTIONS:
            for exploration in UCT_OPTIONS:
                print(f"提交实验：simulations={simulations}, uct_c={exploration}", flush=True)
                for game_index in range(GAMES_PER_GROUP):
                    seed = simulations * 10000 + int(exploration * 1000) * 10 + game_index
                    future = executor.submit(play_selfplay_game, simulations, exploration, seed)
                    futures[future] = (simulations, exploration)

        for future in as_completed(futures):
            key = futures[future]
            grouped[key].append(future.result())
            print(
                f"完成对局：simulations={key[0]}, uct_c={key[1]} "
                f"({len(grouped[key])}/{GAMES_PER_GROUP})",
                flush=True,
            )

    rows: list[dict[str, float | int]] = []

    for simulations in SIMULATION_OPTIONS:
        for exploration in UCT_OPTIONS:
            black_wins = 0
            white_wins = 0
            draws = 0
            total_time = 0.0
            total_moves = 0
            total_nodes = 0.0

            for result in grouped[(simulations, exploration)]:
                if result["winner"] == BLACK:
                    black_wins += 1
                elif result["winner"] == WHITE:
                    white_wins += 1
                else:
                    draws += 1

                total_time += float(result["avg_time_per_move"])
                total_moves += int(result["moves"])
                total_nodes += float(result["avg_search_nodes"])

            rows.append(
                {
                    "simulations": simulations,
                    "uct_c": exploration,
                    "games": GAMES_PER_GROUP,
                    "black_wins": black_wins,
                    "white_wins": white_wins,
                    "draws": draws,
                    "black_win_rate": black_wins / GAMES_PER_GROUP,
                    "white_win_rate": white_wins / GAMES_PER_GROUP,
                    "avg_time_per_move": total_time / GAMES_PER_GROUP,
                    "avg_game_moves": total_moves / GAMES_PER_GROUP,
                    "avg_search_nodes": total_nodes / GAMES_PER_GROUP,
                }
            )

    return rows


def save_results(rows: list[dict[str, float | int]]) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "simulations",
        "uct_c",
        "games",
        "black_wins",
        "white_wins",
        "draws",
        "black_win_rate",
        "white_win_rate",
        "avg_time_per_move",
        "avg_game_moves",
        "avg_search_nodes",
    ]
    with RESULT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    rows = run_experiments()
    save_results(rows)
    print(f"实验结果已保存到 {RESULT_PATH}")


if __name__ == "__main__":
    main()
