"""
エージェントCLI: learn / list / run / play / watch / stats / report コマンド

【使用方法】
# 学習: キャプチャJSONからワークフロー抽出
python3 -m agent.agent_cli learn --json-dir ./screenshots

# ワークフロー一覧
python3 -m agent.agent_cli list

# 自律実行
python3 -m agent.agent_cli run "Cursorでファイルを開いてGeminiに質問する"

# ワークフロー直接再生
python3 -m agent.agent_cli play <workflow_id>

# ドライラン
python3 -m agent.agent_cli run "テスト" --dry-run

# 常時学習モード
python3 -m agent.agent_cli watch
python3 -m agent.agent_cli watch --background

# 学習統計
python3 -m agent.agent_cli stats

# 再現性レポート
python3 -m agent.agent_cli report
python3 -m agent.agent_cli report --category "開発"
python3 -m agent.agent_cli report --format json
python3 -m agent.agent_cli report --output ./my_report.md

【処理内容】
- learn: JSON履歴 → セグメント分割 → AI分析 → ワークフロー保存
- list: 保存済みワークフロー一覧表示
- run: 目標テキストから自律実行
- play: ワークフローIDを指定して直接再生
- watch: 常時学習モード（新規キャプチャを自動検出してワークフロー抽出）
- stats: 学習統計表示（ワークフロー数、フィードバック、成功率等）
- report: 再現性レポート + 業務パーツカタログ生成

【依存】
agent.workflow_extractor, agent.workflow_store, agent.autonomous_loop,
agent.continuous_learner, agent.feedback_store, agent.config, agent.models,
agent.report_generator
"""

import argparse
import logging
import sys

from agent.config import AgentConfig


def cmd_learn(args):
    """学習コマンド: キャプチャJSONからワークフロー抽出"""
    from agent.workflow_extractor import WorkflowExtractor

    config = AgentConfig()
    json_dir = args.json_dir or config.screenshot_dir
    workflow_dir = args.workflow_dir or config.workflow_dir

    print(f"学習開始: {json_dir}")
    print(f"保存先: {workflow_dir}")

    extractor = WorkflowExtractor(
        json_dir=json_dir,
        workflow_dir=workflow_dir,
        model=args.model or config.openai_model,
        min_confidence=args.min_confidence,
    )

    if args.segments_only:
        segments = extractor.build_segments()
        print(f"\nセグメント数: {len(segments)}")
        for i, seg in enumerate(segments):
            print(f"  [{i+1}] {seg['app_name']} ({len(seg['steps'])}操作) "
                  f"{seg['start_time']} ~ {seg['end_time']}")
        return

    workflows = extractor.extract_all()
    print(f"\n抽出完了: {len(workflows)} ワークフロー")
    for wf in workflows:
        print(f"  - {wf.name} (confidence: {wf.confidence:.2f}, {len(wf.steps)}ステップ)")


def cmd_list(args):
    """一覧コマンド: 保存済みワークフロー表示"""
    from agent.workflow_store import WorkflowStore

    config = AgentConfig()
    store = WorkflowStore(args.workflow_dir or config.workflow_dir)

    workflows = store.list_all()
    if not workflows:
        print("保存済みワークフローはありません")
        return

    print(f"ワークフロー一覧 ({len(workflows)}件):\n")
    for wf in workflows:
        print(f"  ID: {wf.workflow_id}")
        print(f"  名前: {wf.name}")
        print(f"  説明: {wf.description}")
        print(f"  アプリ: {wf.app_name}")
        print(f"  ステップ数: {len(wf.steps)}")
        print(f"  タグ: {', '.join(wf.tags) if wf.tags else '-'}")
        print(f"  confidence: {wf.confidence:.2f}")
        print(f"  ステータス: {wf.status} (実行:{wf.execution_count}回)")
        print(f"  作成日: {wf.created_at}")
        if wf.parent_id:
            print(f"  バリアント元: {wf.parent_id}")
        print()

    if args.query:
        results = store.search(args.query)
        print(f"\n検索結果 '{args.query}': {len(results)}件")
        for wf in results:
            print(f"  - {wf.workflow_id}: {wf.name}")


def cmd_run(args):
    """自律実行コマンド"""
    from agent.autonomous_loop import AutonomousLoop
    from agent.models import ExecutionContext

    config = AgentConfig(dry_run=args.dry_run)
    ctx = ExecutionContext(
        goal=args.goal,
        workflow_id=args.workflow_id,
        dry_run=args.dry_run,
        max_steps=args.max_steps,
        step_delay=args.delay,
        confirm_dangerous=not args.no_confirm,
    )

    print(f"目標: {args.goal}")
    print(f"dry-run: {args.dry_run}")
    print(f"最大ステップ: {args.max_steps}")
    print()

    loop = AutonomousLoop(config)
    result = loop.run(ctx)

    print(f"\n{'='*50}")
    print(f"結果: {'成功' if result.success else '失敗'}")
    print(f"ステップ数: {result.steps_executed}")
    print(f"  成功: {result.steps_succeeded}")
    print(f"  失敗: {result.steps_failed}")
    print(f"目標達成: {'はい' if result.goal_achieved else 'いいえ'}")
    print(f"実行時間: {result.total_time_seconds:.1f}秒")
    if result.error:
        print(f"エラー: {result.error}")
    print(f"{'='*50}")


def cmd_play(args):
    """ワークフロー直接再生コマンド"""
    from agent.autonomous_loop import AutonomousLoop

    config = AgentConfig()
    loop = AutonomousLoop(config)

    print(f"ワークフロー再生: {args.workflow_id}")
    print(f"dry-run: {args.dry_run}")
    print()

    params = {}
    if args.param:
        for p in args.param:
            key, _, value = p.partition("=")
            params[key] = value

    result = loop.play_workflow(
        workflow_id=args.workflow_id,
        dry_run=args.dry_run,
        delay=args.delay,
        parameters=params if params else None,
    )

    print(f"\n{'='*50}")
    print(f"結果: {'成功' if result.success else '失敗'}")
    print(f"ステップ数: {result.steps_executed} (成功: {result.steps_succeeded}, 失敗: {result.steps_failed})")
    print(f"実行時間: {result.total_time_seconds:.1f}秒")
    if result.error:
        print(f"エラー: {result.error}")
    print(f"{'='*50}")


def cmd_watch(args):
    """常時学習コマンド: 新規キャプチャを自動検出してワークフロー抽出"""
    import threading
    from agent.continuous_learner import ContinuousLearner

    config = AgentConfig()
    learner = ContinuousLearner(config)

    print("常時学習モード起動")
    print(f"  監視先: {config.screenshot_dir}")
    print(f"  ポーリング間隔: {learner.poll_interval}秒")
    print(f"  リファイン間隔: {learner.refine_interval}サイクル")
    print(f"  停止: Ctrl+C")
    print()

    if args.background:
        thread = threading.Thread(target=learner.run, daemon=True)
        thread.start()
        print("[background] バックグラウンドで常時学習を起動しました")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            learner.stop()
            thread.join(timeout=5.0)
            print("\n停止しました")
    else:
        try:
            learner.run()
        except KeyboardInterrupt:
            learner.stop()
            print("\n停止しました")


def cmd_report(args):
    """再現性レポート + 業務パーツカタログ生成"""
    from pathlib import Path
    from agent.feedback_store import FeedbackStore
    from agent.report_generator import ReportGenerator
    from agent.workflow_store import WorkflowStore

    config = AgentConfig()
    store = WorkflowStore(args.workflow_dir or config.workflow_dir)
    feedback_dir = str(Path(config.workflow_dir) / "feedback")
    feedback = FeedbackStore(feedback_dir)
    gen = ReportGenerator(store, feedback)

    output = gen.generate(format=args.format, category=args.category)

    # レポートを reports/ にも保存
    from datetime import datetime
    reports_dir = Path(config.workflow_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    ext = "json" if args.format == "json" else "md"
    report_path = reports_dir / f"report_{datetime.now().strftime('%Y%m%d')}.{ext}"
    report_path.write_text(output, encoding="utf-8")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"レポート保存: {out_path}")
        print(f"カタログ更新完了: {Path(config.workflow_dir) / 'parts' / 'catalog.json'}")
    else:
        print(output)
        if args.format != "json":
            print(f"カタログ更新完了: {Path(config.workflow_dir) / 'parts' / 'catalog.json'}")


def cmd_stats(args):
    """統計コマンド: MetaAnalyzerによる学習統計を表示"""
    from pathlib import Path
    from agent.feedback_store import FeedbackStore
    from agent.meta_analyzer import MetaAnalyzer
    from agent.workflow_store import WorkflowStore

    config = AgentConfig()
    store = WorkflowStore(args.workflow_dir or config.workflow_dir)
    feedback_dir = str(Path(config.workflow_dir) / "feedback")
    feedback = FeedbackStore(feedback_dir)
    analyzer = MetaAnalyzer(store, feedback)

    # レポート生成
    days = getattr(args, 'days', 7)
    report = analyzer.generate_report(days=days)

    print(f"=== 学習統計（直近{days}日間） ===\n")
    print(f"ワークフロー数: {sum(report['status_distribution'].values())}")
    print(f"  DRAFT: {report['status_distribution'].get('draft', 0)}")
    print(f"  TESTED: {report['status_distribution'].get('tested', 0)}")
    print(f"  ACTIVE: {report['status_distribution'].get('active', 0)}")
    print(f"  DEPRECATED: {report['status_distribution'].get('deprecated', 0)}")
    print(f"\nフィードバック数: {report['total_feedbacks']}")
    print(f"全体成功率: {report['overall_success_rate']*100:.1f}%")

    # アプリ別統計
    if report["app_stats"]:
        print("\n--- アプリ別統計 ---")
        for app, stats in report["app_stats"].items():
            print(f"  {app}: {stats['count']}回 成功率:{stats['success_rate']*100:.0f}% 平均:{stats['avg_duration']:.1f}秒")

    # Top 使用
    if report["top_used"]:
        print("\n--- よく使うワークフロー Top5 ---")
        for item in report["top_used"]:
            print(f"  {item['name']}: {item['execution_count']}回 成功率:{item['success_rate']*100:.0f}%")

    # Top 失敗
    if report["top_failures"]:
        print("\n--- 失敗が多いワークフロー Top5 ---")
        for item in report["top_failures"]:
            print(f"  {item['name']}: 失敗{item['failure_count']}回 成功率:{item['success_rate']*100:.0f}%")

    # 改善提案
    suggestions = report["suggestions"]
    if suggestions:
        print(f"\n--- 改善提案 ({len(suggestions)}件) ---")
        for s in suggestions:
            icon = {"high": "!!!", "medium": "!!", "low": "!"}[s["priority"]]
            auto = " [自動適用可]" if s.get("auto_applicable") else ""
            print(f"  [{icon}] {s['name']}: {s['suggestion']}{auto}")

    # 処理済みキャプチャ
    processed_path = Path(config.screenshot_dir) / "_agent_processed.txt"
    if processed_path.exists():
        processed_count = len([
            line for line in processed_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ])
        print(f"\n処理済みキャプチャ: {processed_count}件")

    # リカバリパターン
    try:
        from agent.recovery_learner import RecoveryLearner
        patterns_path = str(Path(config.workflow_dir) / "recovery_patterns.json")
        recovery = RecoveryLearner(patterns_path)
        reliable = recovery.get_reliable_patterns()
        if reliable:
            print(f"\n--- 学習済みリカバリパターン ({len(reliable)}件) ---")
            for p in reliable[:5]:
                print(f"  {p['error_code']}@{p['app_name'] or '*'} → {p['recovery_action']} "
                      f"(成功率:{p['success_rate']*100:.0f}%, {p['sample_count']}件)")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="操作履歴学習・自律再現エージェント",
        prog="python3 -m agent.agent_cli",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログ出力")
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")

    # learn
    p_learn = subparsers.add_parser("learn", help="キャプチャJSONからワークフロー抽出")
    p_learn.add_argument("--json-dir", help="キャプチャJSONディレクトリ")
    p_learn.add_argument("--workflow-dir", help="ワークフロー保存先")
    p_learn.add_argument("--model", help="AIモデル (default: gpt-5)")
    p_learn.add_argument("--min-confidence", type=float, default=0.5, help="最低confidence (default: 0.5)")
    p_learn.add_argument("--segments-only", action="store_true", help="セグメント分割のみ（AI分析なし）")

    # list
    p_list = subparsers.add_parser("list", help="保存済みワークフロー一覧")
    p_list.add_argument("--workflow-dir", help="ワークフローディレクトリ")
    p_list.add_argument("--query", "-q", help="キーワード検索")

    # run
    p_run = subparsers.add_parser("run", help="目標テキストから自律実行")
    p_run.add_argument("goal", help="目標テキスト")
    p_run.add_argument("--workflow-id", help="使用するワークフローID")
    p_run.add_argument("--dry-run", action="store_true", help="実際に操作しない")
    p_run.add_argument("--max-steps", type=int, default=50, help="最大ステップ数")
    p_run.add_argument("--delay", type=float, default=1.0, help="ステップ間待機秒数")
    p_run.add_argument("--no-confirm", action="store_true", help="危険操作の確認をスキップ")

    # play
    p_play = subparsers.add_parser("play", help="ワークフロー直接再生")
    p_play.add_argument("workflow_id", help="ワークフローID")
    p_play.add_argument("--dry-run", action="store_true", help="実際に操作しない")
    p_play.add_argument("--delay", type=float, default=1.0, help="ステップ間待機秒数")
    p_play.add_argument("--param", action="append", help="パラメータ (key=value)")

    # watch
    p_watch = subparsers.add_parser("watch", help="常時学習モード（新規キャプチャの自動検出・学習）")
    p_watch.add_argument("--background", action="store_true", help="バックグラウンド起動")

    # report
    p_report = subparsers.add_parser("report", help="再現性レポート + 業務パーツカタログ生成")
    p_report.add_argument("--workflow-dir", help="ワークフローディレクトリ")
    p_report.add_argument("--category", help="カテゴリフィルタ（例: 開発, ブラウザ/Web）")
    p_report.add_argument("--format", choices=["markdown", "json"], default="markdown", help="出力形式")
    p_report.add_argument("--output", "-o", help="出力ファイルパス")

    # stats
    p_stats = subparsers.add_parser("stats", help="学習統計表示")
    p_stats.add_argument("--workflow-dir", help="ワークフローディレクトリ")

    args = parser.parse_args()

    # ログ設定
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "learn": cmd_learn, "list": cmd_list, "run": cmd_run,
        "play": cmd_play, "watch": cmd_watch, "report": cmd_report,
        "stats": cmd_stats,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
