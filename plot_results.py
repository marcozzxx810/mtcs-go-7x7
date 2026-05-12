from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter


RESULT_PATH = Path("results/experiment_results.csv")
FIGURE_DIR = Path("figures")
UCT_COLORS = {
    0.5: "#2563eb",
    1.414: "#c2410c",
    2.0: "#15803d",
}


def configure_matplotlib() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams["font.sans-serif"] = [
        "Hiragino Sans GB",
        "Arial Unicode MS",
        "STHeiti",
        "SimHei",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"
    plt.rcParams["axes.edgecolor"] = "#d4d4d8"
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["font.size"] = 11
    plt.rcParams["axes.titlesize"] = 15
    plt.rcParams["axes.labelsize"] = 11
    plt.rcParams["xtick.labelsize"] = 10
    plt.rcParams["ytick.labelsize"] = 10
    plt.rcParams["legend.fontsize"] = 9.5
    plt.rcParams["axes.labelcolor"] = "#27272a"
    plt.rcParams["xtick.color"] = "#3f3f46"
    plt.rcParams["ytick.color"] = "#3f3f46"


def read_rows() -> list[dict[str, float]]:
    if not RESULT_PATH.exists():
        raise FileNotFoundError(f"未找到 {RESULT_PATH}，请先运行 uv run python experiment.py")
    rows: list[dict[str, float]] = []
    with RESULT_PATH.open("r", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            rows.append({key: float(value) for key, value in row.items()})
    return rows


def grouped_average(rows: list[dict[str, float]], key: str) -> tuple[list[int], list[float]]:
    grouped: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        grouped[int(row["simulations"])].append(row[key])
    x_values = sorted(grouped)
    y_values = [sum(grouped[x]) / len(grouped[x]) for x in x_values]
    return x_values, y_values


def unique_values(rows: list[dict[str, float]], key: str) -> list[float]:
    return sorted({row[key] for row in rows})


def metric_by_simulation(rows: list[dict[str, float]], key: str) -> dict[int, list[float]]:
    grouped: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        grouped[int(row["simulations"])].append(row[key])
    return grouped


def pivot(rows: list[dict[str, float]], key: str) -> tuple[list[int], list[float], list[list[float]]]:
    simulations = [int(value) for value in unique_values(rows, "simulations")]
    ucts = unique_values(rows, "uct_c")
    lookup = {(int(row["simulations"]), row["uct_c"]): row[key] for row in rows}
    matrix = [[lookup[(simulation, uct)] for simulation in simulations] for uct in ucts]
    return simulations, ucts, matrix


def finish_figure(fig: plt.Figure, filename: str) -> None:
    fig.savefig(FIGURE_DIR / filename, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_win_rate_heatmap(rows: list[dict[str, float]]) -> None:
    simulations, ucts, black_matrix = pivot(rows, "black_win_rate")
    _, _, white_matrix = pivot(rows, "white_win_rate")

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.25), dpi=180, constrained_layout=True)
    fig.suptitle("胜率矩阵：模拟次数 × UCT 参数", fontsize=16, fontweight="bold")

    specs = [
        (axes[0], black_matrix, "黑方胜率", "Greys"),
        (axes[1], white_matrix, "白方胜率", "Blues"),
    ]

    images = []
    for ax, matrix, title, cmap in specs:
        image = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=1, aspect="auto")
        images.append(image)
        ax.set_title(title, fontsize=12, pad=10)
        ax.set_xlabel("MCTS 模拟次数")
        ax.set_xticks(range(len(simulations)), labels=[str(value) for value in simulations])
        ax.set_yticks(range(len(ucts)), labels=[f"{value:g}" for value in ucts])
        ax.set_ylabel("UCT c")
        ax.tick_params(length=0)
        for row_index, row in enumerate(matrix):
            for col_index, value in enumerate(row):
                text_color = "white" if value >= 0.55 and cmap == "Greys" else "#111827"
                ax.text(
                    col_index,
                    row_index,
                    f"{value:.0%}",
                    ha="center",
                    va="center",
                    fontsize=11,
                    fontweight="bold",
                    color=text_color,
                )
        for spine in ax.spines.values():
            spine.set_visible(False)

    colorbar = fig.colorbar(images[-1], ax=axes.ravel().tolist(), shrink=0.86, pad=0.02)
    colorbar.ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    fig.text(
        0.5,
        -0.02,
        "每个单元格为 5 局自我对弈结果；平局不计入黑方或白方胜率。",
        ha="center",
        fontsize=10,
        color="#52525b",
    )
    finish_figure(fig, "win_rate_vs_simulations.png")


def save_metric_profile(
    rows: list[dict[str, float]],
    filename: str,
    title: str,
    ylabel: str,
    key: str,
    formatter: FuncFormatter | None = None,
) -> None:
    simulations = [int(value) for value in unique_values(rows, "simulations")]
    ucts = unique_values(rows, "uct_c")
    by_sim = metric_by_simulation(rows, key)
    means = [sum(by_sim[simulation]) / len(by_sim[simulation]) for simulation in simulations]
    lows = [min(by_sim[simulation]) for simulation in simulations]
    highs = [max(by_sim[simulation]) for simulation in simulations]

    fig, ax = plt.subplots(figsize=(8.6, 4.35), dpi=180)
    ax.fill_between(simulations, lows, highs, color="#94a3b8", alpha=0.16, label="UCT 范围")
    ax.plot(
        simulations,
        means,
        color="#111827",
        linewidth=2.4,
        marker="D",
        markersize=5,
        label="参数均值",
        zorder=3,
    )

    for uct in ucts:
        values = [
            next(row[key] for row in rows if int(row["simulations"]) == simulation and row["uct_c"] == uct)
            for simulation in simulations
        ]
        ax.plot(
            simulations,
            values,
            marker="o",
            markersize=5,
            linewidth=1.8,
            color=UCT_COLORS.get(uct, "#71717a"),
            label=f"UCT c={uct:g}",
            alpha=0.95,
        )

    ax.set_title(title, fontsize=15, pad=12)
    ax.set_xlabel("MCTS 模拟次数")
    ax.set_ylabel(ylabel)
    ax.set_xticks(simulations)
    if formatter is not None:
        ax.yaxis.set_major_formatter(formatter)
    ax.grid(axis="y", color="#e4e4e7", linewidth=0.8)
    ax.grid(axis="x", visible=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    fig.text(
        0.5,
        0.01,
        "点为每组 5 局自我对弈均值；浅色带表示同一模拟次数下不同 UCT 参数的范围。",
        ha="center",
        fontsize=10,
        color="#52525b",
    )
    plt.tight_layout()
    finish_figure(fig, filename)


def save_nodes_chart(rows: list[dict[str, float]]) -> None:
    simulations = [int(value) for value in unique_values(rows, "simulations")]
    ucts = unique_values(rows, "uct_c")
    positions = list(range(len(simulations)))
    by_sim = metric_by_simulation(rows, "avg_search_nodes")
    node_means = [sum(by_sim[simulation]) / len(by_sim[simulation]) for simulation in simulations]
    node_lows = [min(by_sim[simulation]) for simulation in simulations]
    node_highs = [max(by_sim[simulation]) for simulation in simulations]
    yerr = [
        [mean - low for mean, low in zip(node_means, node_lows)],
        [high - mean for mean, high in zip(node_means, node_highs)],
    ]

    fig, ax_nodes = plt.subplots(figsize=(8.6, 4.45), dpi=180)
    bars = ax_nodes.bar(
        positions,
        node_means,
        width=0.56,
        color="#dbeafe",
        edgecolor="#2563eb",
        linewidth=1.1,
        yerr=yerr,
        capsize=4,
        label="平均扩展节点数",
        zorder=2,
    )
    ax_nodes.set_title("搜索规模与吞吐率：模拟次数对比", fontsize=15, pad=12)
    ax_nodes.set_xlabel("MCTS 模拟次数")
    ax_nodes.set_ylabel("平均搜索节点数")
    ax_nodes.set_xticks(positions, labels=[str(value) for value in simulations])
    ax_nodes.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:,.0f}"))
    ax_nodes.grid(axis="y", color="#e4e4e7", linewidth=0.8)
    ax_nodes.grid(axis="x", visible=False)
    ax_nodes.spines["top"].set_visible(False)

    for bar, value in zip(bars, node_means):
        ax_nodes.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(node_means) * 0.025,
            f"{value:.0f}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#1e3a8a",
        )

    ax_rate = ax_nodes.twinx()
    for uct in ucts:
        throughput = []
        for simulation in simulations:
            row = next(
                row
                for row in rows
                if int(row["simulations"]) == simulation and row["uct_c"] == uct
            )
            throughput.append(row["avg_search_nodes"] / row["avg_time_per_move"])
        ax_rate.plot(
            positions,
            throughput,
            marker="o",
            markersize=4,
            linewidth=1.7,
            color=UCT_COLORS.get(uct, "#71717a"),
            label=f"UCT c={uct:g} 吞吐率",
            alpha=0.95,
            zorder=3,
        )
    ax_rate.set_ylabel("搜索吞吐率（节点/秒）")
    ax_rate.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:,.0f}"))
    ax_rate.spines["top"].set_visible(False)
    ax_rate.spines["left"].set_visible(False)

    handles_left, labels_left = ax_nodes.get_legend_handles_labels()
    handles_right, labels_right = ax_rate.get_legend_handles_labels()
    ax_nodes.legend(
        handles_left + handles_right,
        labels_left + labels_right,
        ncol=2,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
    )
    fig.text(
        0.5,
        0.01,
        "柱状为每步平均扩展节点数；折线为单位时间搜索吞吐率，更能反映搜索成本变化。",
        ha="center",
        fontsize=10,
        color="#52525b",
    )
    plt.tight_layout()
    finish_figure(fig, "nodes_vs_simulations.png")


def main() -> None:
    configure_matplotlib()
    rows = read_rows()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    save_win_rate_heatmap(rows)
    save_metric_profile(
        rows,
        "time_vs_simulations.png",
        "平均每步耗时：模拟次数与 UCT 参数对比",
        "秒/步",
        "avg_time_per_move",
        FuncFormatter(lambda value, _pos: f"{value:.2f}"),
    )
    save_metric_profile(
        rows,
        "moves_vs_simulations.png",
        "平均游戏步数：模拟次数与 UCT 参数对比",
        "步数",
        "avg_game_moves",
        FuncFormatter(lambda value, _pos: f"{value:.0f}"),
    )
    save_nodes_chart(rows)
    print(f"图表已保存到 {FIGURE_DIR}")


if __name__ == "__main__":
    main()
