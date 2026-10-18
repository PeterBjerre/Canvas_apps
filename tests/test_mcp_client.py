# -*- coding: utf-8 -*-
"""McpClient mod en falsk MCP-server (R2-067).

En server, der svarer paa initialize og derefter tier, skal give en
Timeout efter --timeout - ikke en terminal, der haenger, til nogen
trykker Ctrl+C."""
import sys
import textwrap
import time

import pytest

import canvas_mcp

FAKE = textwrap.dedent('''
    import json, sys, time
    for line in sys.stdin:
        msg = json.loads(line)
        if msg.get("method") == "initialize":
            print(json.dumps({"jsonrpc": "2.0", "id": msg["id"],
                              "result": {"capabilities": {}}}), flush=True)
        elif msg.get("method") == "exit_now":
            sys.exit(0)
        elif "id" in msg:
            time.sleep(60)    # haenger midt i kaldet
''')


@pytest.fixture
def client(tmp_path):
    script = tmp_path / "fake_server.py"
    script.write_text(FAKE, encoding="utf-8")
    c = canvas_mcp.McpClient([sys.executable, str(script)], timeout=2)
    c.start()
    yield c
    if c.proc.poll() is None:
        c.proc.kill()


def test_hanging_server_times_out(client):
    t0 = time.time()
    with pytest.raises(canvas_mcp.McpError, match="Timeout"):
        client.request("tools/list")
    assert time.time() - t0 < 10


def test_server_that_exits_is_reported(client):
    with pytest.raises(canvas_mcp.McpError, match="lukkede|stoppede"):
        client.request("exit_now", timeout=20)
