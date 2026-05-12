# 基于 MCTS 的 7x7 围棋决策程序

本项目实现了一个基于蒙特卡洛树搜索（MCTS）的小棋盘围棋决策程序，支持 7×7、8×8、9×9 棋盘。

## 环境准备

推荐使用 `uv`（快速）：

```bash
uv sync
```

或标准 pip：

```bash
pip install -r requirements.txt
```

> **注意**：生成 PDF 报告需要额外安装 `pandoc` 和 `xelatex`，程序本身运行**不依赖** pandoc。

---

## 运行方式

### 人机对战（你执黑，AI 执白）

```bash
uv run python main.py --mode human
uv run python main.py --mode human --simulations 500 --komi 6.5 --board-size 7
```

### AI 自我对弈

```bash
uv run python main.py --mode selfplay
uv run python main.py --mode selfplay --simulations 300 --seed 42
uv run python main.py --mode selfplay --board-size 9 --komi 6.5 --simulations 200
```

### 快速实验（约 2–5 分钟）

```bash
uv run python experiment.py --mode quick --seed 42
```

### 完整实验（约 30–60 分钟，90 局）

```bash
uv run python experiment.py --mode serious --seed 42
```

### 自定义实验参数

```bash
uv run python experiment.py --simulations 100 300 500 --ucts 1.414 --games 5 --seed 0
```

### 生成评价图表

```bash
uv run python plot_results.py
```

### 生成程序截图（SVG）

```bash
uv run python generate_screenshots.py
```

### 构建完整报告（需要 pandoc + xelatex）

```bash
bash build_report.sh
```

---

## 主要命令行参数

| 参数 | 说明 | 默认值 |
|---|---|---|
| `--mode` | 运行模式（human / selfplay） | human |
| `--simulations` | 每步 MCTS 模拟次数 | 300 |
| `--uct` | UCT 探索参数 c | 1.414 |
| `--seed` | 随机种子（保证复现） | 无 |
| `--board-size` | 棋盘大小（7 / 8 / 9） | 7 |
| `--komi` | 白方贴目 | 6.5 |
| `--max-turns` | 安全步数上限 | 3 × board\_size² |

---

## 规则说明

- 简化中国规则（面积计分）
- 白方贴目 6.5（可通过 `--komi` 调整）
- 简单劫（不实现完整 superko）
- 双方连续 pass 后终局（安全上限作为兜底）
- 不实现死子判断（依赖 rollout 将死子提净后再 pass）
