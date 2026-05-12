#!/usr/bin/env bash
set -e
export PATH="$PWD:$PATH"

uv run python generate_screenshots.py
uv run python plot_results.py
pandoc report.md -o report.pdf --pdf-engine=xelatex
