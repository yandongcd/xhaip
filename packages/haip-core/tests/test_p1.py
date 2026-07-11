"""测试热重载 + 可观测性 + 并行编排."""

import sys
import tempfile
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))


class TestHotReload:
    def test_watcher_start_stop(self):
        with tempfile.TemporaryDirectory() as d:
            from haip.agent.hotreload import HotReloadWatcher
            w = HotReloadWatcher(d, interval=0.1)
            w.start()
            assert w._running
            time.sleep(0.3)
            w.stop()
            assert not w._running

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            from haip.agent.hotreload import HotReloadWatcher
            w = HotReloadWatcher(d, interval=0.1)
            changed = w._scan()
            assert len(changed) == 0

    def test_file_change_detection(self):
        with tempfile.TemporaryDirectory() as d:
            from haip.agent.hotreload import HotReloadWatcher
            test_file = Path(d) / "test.yaml"
            test_file.write_text("version: '1.0'\n", encoding="utf-8")
            w = HotReloadWatcher(d, interval=0.1)
            w._mtimes = w._build_snapshot()
            time.sleep(0.3)
            test_file.write_text("version: '2.0'\n", encoding="utf-8")
            time.sleep(0.3)
            changed = w._scan()
            assert len(changed) >= 1

    def test_scan_detects_modification(self):
        with tempfile.TemporaryDirectory() as d:
            from haip.agent.hotreload import HotReloadWatcher
            test_file = Path(d) / "test.yaml"
            test_file.write_text("version: '1.0'\n", encoding="utf-8")
            w = HotReloadWatcher(d, interval=0.1)
            w._mtimes = w._build_snapshot()
            time.sleep(0.3)
            test_file.write_text("version: '2.0'\n", encoding="utf-8")
            time.sleep(0.3)
            changed = w._scan()
            assert len(changed) >= 1

    def test_scan_detects_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            from haip.agent.hotreload import HotReloadWatcher
            test_file = Path(d) / "remove_me.yaml"
            test_file.write_text("data\n", encoding="utf-8")
            w = HotReloadWatcher(d, interval=0.1)
            w._mtimes = w._build_snapshot()
            test_file.unlink()
            changed = w._scan()
            assert len(changed) >= 1

    def test_yaml_reload_on_modification(self):
        with tempfile.TemporaryDirectory() as d:
            from haip.agent.hotreload import HotReloadWatcher
            test_file = Path(d) / "agent_config.yaml"
            test_file.write_text("name: config\n", encoding="utf-8")
            w = HotReloadWatcher(d, interval=0.1)
            w._mtimes = w._build_snapshot()
            time.sleep(0.1)
            test_file.write_text("name: config_v2\n", encoding="utf-8")
            changed = w._scan()
            assert "agent_config.yaml" in str(changed) or any("agent_config.yaml" in c for c in changed)


class TestObservability:
    def test_trace_context(self):
        from haip.observability import TraceContext
        ctx = TraceContext()
        tid = ctx.start_trace("wf1")
        assert tid == "wf1"
        ctx.clear()
        assert len(ctx.spans) == 0

    def test_metrics_collector(self):
        from haip.observability import MetricsCollector
        mc = MetricsCollector()
        mc.record("pharmacy", "assess", 5.2, "ok")
        mc.record("pharmacy", "assess", 3.1, "ok")
        mc.record("pharmacy", "tpn", 12.0, "error")
        s = mc.summary()
        assert s["total_calls"] == 3
        assert s["total_errors"] == 1
        assert "pharmacy" in s["agents"]


class TestParallelOrchestrator:
    def test_independent_nodes_all_called(self):
        from haip.orchestrator import (
            A2AOrchestrator, TaskNode, TaskDAG, MockTransport,
        )
        transport = MockTransport({
            "a/t": {"status": "ok", "output": "a"},
            "b/t": {"status": "ok", "output": "b"},
            "c/t": {"status": "ok", "output": "c"},
        })
        orch = A2AOrchestrator(transport=transport)
        dag = TaskDAG(nodes=[
            TaskNode(id="1", agent="a", tool="t"),
            TaskNode(id="2", agent="b", tool="t"),
            TaskNode(id="3", agent="c", tool="t"),
        ])
        result = orch.execute(dag=dag)
        assert len(transport.call_log) == 3
        assert all(n.status == "completed" for n in result.nodes)
