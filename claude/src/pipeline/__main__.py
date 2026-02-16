"""
パッケージとして実行するためのエントリポイント

【使用方法】
python -m pipeline.learning_pipeline --once
python -m pipeline.learning_pipeline --watch-dir ./screenshots
"""

from pipeline.learning_pipeline import main

main()
