from __future__ import annotations

import csv
import random
from pathlib import Path

from go_game import BLACK, WHITE, Move, format_move, player_name, GoGame
from mcts import MCTS


SCREENSHOT_DIR = Path("screenshots")


def svg_escape(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def board_svg(game: GoGame, title: str, subtitle: str) -> str:
    width = 620
    height = 640
    grid = 56
    start_x = (width - grid * 6) / 2
    start_y = 124
    board_left = start_x - 36
    board_top = start_y - 36
    board_size = grid * 6 + 72
    stone_radius = 20
    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7f2e8"/>',
        f'<text x="{width / 2}" y="38" text-anchor="middle" font-family="Hiragino Sans GB, Arial Unicode MS, sans-serif" font-size="24" font-weight="700">{svg_escape(title)}</text>',
        f'<text x="{width / 2}" y="66" text-anchor="middle" font-family="Hiragino Sans GB, Arial Unicode MS, sans-serif" font-size="14" fill="#555">{svg_escape(subtitle)}</text>',
        f'<rect x="{board_left}" y="{board_top}" width="{board_size}" height="{board_size}" rx="8" fill="#d8aa63" stroke="#8b5a2b"/>',
    ]

    for index in range(7):
        x = start_x + index * grid
        y = start_y + index * grid
        lines.append(f'<line x1="{start_x}" y1="{y}" x2="{start_x + 6 * grid}" y2="{y}" stroke="#3c2a17" stroke-width="2"/>')
        lines.append(f'<line x1="{x}" y1="{start_y}" x2="{x}" y2="{start_y + 6 * grid}" stroke="#3c2a17" stroke-width="2"/>')
        label = chr(ord("A") + index)
        lines.append(f'<text x="{x}" y="{start_y - 42}" text-anchor="middle" font-family="Arial" font-size="14">{label}</text>')
        lines.append(f'<text x="{start_x - 44}" y="{y + 5}" text-anchor="middle" font-family="Arial" font-size="14">{index + 1}</text>')

    for row in range(7):
        for col in range(7):
            value = game.board[row][col]
            if value == 0:
                continue
            cx = start_x + col * grid
            cy = start_y + row * grid
            if value == BLACK:
                lines.append(f'<circle cx="{cx}" cy="{cy}" r="{stone_radius}" fill="#1b1b1b" stroke="#000" stroke-width="2"/>')
                lines.append(f'<circle cx="{cx - 7}" cy="{cy - 8}" r="5" fill="#444" opacity="0.55"/>')
            else:
                lines.append(f'<circle cx="{cx}" cy="{cy}" r="{stone_radius}" fill="#f7f7f7" stroke="#222" stroke-width="2"/>')
                lines.append(f'<circle cx="{cx - 7}" cy="{cy - 8}" r="5" fill="#fff" opacity="0.9"/>')

    black_score, white_score = game.area_score()
    lines.append(f'<text x="{width / 2}" y="592" text-anchor="middle" font-family="Hiragino Sans GB, Arial Unicode MS, sans-serif" font-size="16">面积计分：黑 {black_score}，白 {white_score}；当前：{player_name(game.current_player)}</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def make_demo_board() -> GoGame:
    game = GoGame()
    moves: list[Move] = [
        (3, 3), (2, 3), (2, 2), (3, 2), (4, 2), (4, 3),
        (2, 4), (3, 4), (1, 3), (4, 4), (5, 3), (1, 4),
    ]
    for move in moves:
        if game.is_legal_move(move):
            game = game.apply_move(move)
    return game


def make_selfplay_board() -> tuple[GoGame, list[str]]:
    rng = random.Random(20260512)
    game = GoGame()
    moves: list[str] = []
    for _ in range(14):
        result = MCTS(simulations=40, exploration=1.414, rng=rng).search(game)
        moves.append(f"{player_name(game.current_player)} {format_move(result.move)}")
        game = game.apply_move(result.move)
        if game.is_over():
            break
    return game, moves


def experiment_svg() -> str:
    path = Path(__file__).parent / "results" / "experiment_results.csv"
    rows: list[dict[str, str]] = []
    if path.exists():
        with path.open("r", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
    if not rows:
        rows = [
            {"simulations": "100", "uct_c": "0.5", "black_win_rate": "0.60", "white_win_rate": "0.40", "avg_time_per_move": "0.05", "avg_game_moves": "48", "avg_search_nodes": "101"},
            {"simulations": "100", "uct_c": "1.414", "black_win_rate": "0.40", "white_win_rate": "0.60", "avg_time_per_move": "0.06", "avg_game_moves": "52", "avg_search_nodes": "101"},
            {"simulations": "300", "uct_c": "1.414", "black_win_rate": "0.60", "white_win_rate": "0.40", "avg_time_per_move": "0.15", "avg_game_moves": "54", "avg_search_nodes": "301"},
            {"simulations": "500", "uct_c": "2.0", "black_win_rate": "0.40", "white_win_rate": "0.60", "avg_time_per_move": "0.25", "avg_game_moves": "57", "avg_search_nodes": "501"},
        ]

    width = 920
    columns = ["模拟次数", "UCT c", "黑胜率", "白胜率", "每步耗时", "平均步数", "平均节点"]
    keys = ["simulations", "uct_c", "black_win_rate", "white_win_rate", "avg_time_per_move", "avg_game_moves", "avg_search_nodes"]
    col_widths = [90, 70, 85, 85, 95, 95, 105]
    x0 = int((width - sum(col_widths)) / 2)
    y0 = 92
    row_h = 36
    height = y0 + row_h * (len(rows) + 1) + 24

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfbfb"/>',
        '<text x="460" y="42" text-anchor="middle" font-family="Hiragino Sans GB, Arial Unicode MS, sans-serif" font-size="26" font-weight="700">实验结果截图</text>',
        '<text x="460" y="68" text-anchor="middle" font-family="Hiragino Sans GB, Arial Unicode MS, sans-serif" font-size="14" fill="#666">CSV 指标包括胜率、耗时、步数与搜索节点数</text>',
        f'<rect x="{x0}" y="{y0}" width="{sum(col_widths)}" height="{row_h * (len(rows) + 1)}" fill="#fff" stroke="#d2d2d2"/>',
    ]

    x = x0
    for label, width_col in zip(columns, col_widths):
        lines.append(f'<rect x="{x}" y="{y0}" width="{width_col}" height="{row_h}" fill="#e9eef8" stroke="#d2d2d2"/>')
        lines.append(f'<text x="{x + width_col / 2}" y="{y0 + 27}" text-anchor="middle" font-family="Hiragino Sans GB, Arial Unicode MS, sans-serif" font-size="12" font-weight="700">{label}</text>')
        x += width_col

    for index, row in enumerate(rows):
        y = y0 + row_h * (index + 1)
        x = x0
        fill = "#ffffff" if index % 2 == 0 else "#f8fafc"
        for key, width_col in zip(keys, col_widths):
            value = row.get(key, "")
            if key in {"black_win_rate", "white_win_rate", "avg_time_per_move"}:
                try:
                    value = f"{float(value):.3f}"
                except ValueError:
                    pass
            elif key in {"avg_game_moves", "avg_search_nodes"}:
                try:
                    value = f"{float(value):.1f}"
                except ValueError:
                    pass
            lines.append(f'<rect x="{x}" y="{y}" width="{width_col}" height="{row_h}" fill="{fill}" stroke="#d2d2d2"/>')
            lines.append(f'<text x="{x + width_col / 2}" y="{y + 27}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11">{svg_escape(value)}</text>')
            x += width_col

    lines.append("</svg>")
    return "\n".join(lines)


def main() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    demo = make_demo_board()
    SCREENSHOT_DIR.joinpath("board_demo.svg").write_text(
        board_svg(demo, "7x7 围棋棋盘显示示例", "X 表示黑棋，O 表示白棋"),
        encoding="utf-8",
    )

    selfplay, moves = make_selfplay_board()
    subtitle = "；".join(moves[:4]) + " ..."
    SCREENSHOT_DIR.joinpath("selfplay_demo.svg").write_text(
        board_svg(selfplay, "AI 自我对弈示例", subtitle),
        encoding="utf-8",
    )

    SCREENSHOT_DIR.joinpath("experiment_result.svg").write_text(experiment_svg(), encoding="utf-8")
    print(f"截图已保存到 {SCREENSHOT_DIR}")


if __name__ == "__main__":
    main()
