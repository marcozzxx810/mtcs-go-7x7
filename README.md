# 基于 MCTS 的 7x7 围棋决策程序

本项目使用 `uv` 管理 Python 环境，使用 `pandoc` 生成中文实验报告。

```bash
uv sync
uv run python main.py
uv run python main.py --mode selfplay
uv run python experiment.py
uv run python plot_results.py
uv run python generate_screenshots.py
bash build_report.sh
```

如果中文 PDF 字体有问题，可手动指定中文字体：

```bash
pandoc report.md -o report.pdf --pdf-engine=xelatex -V CJKmainfont="Noto Sans CJK SC"
```
