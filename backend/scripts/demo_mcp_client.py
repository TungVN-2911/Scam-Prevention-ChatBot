# Script DEMO (khong phai pytest) - tu tao token cho 1 role bat ky roi goi
# thang cac tool trong MCP Server, tach biet voi luong Chat that.
import asyncio
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.auth import create_access_token
from app.config import settings


async def main(username: str, role: str) -> None:
    token = create_access_token(username, role)
    print(f"Token demo cho username='{username}' role='{role}' (tu tao tai cho, KHONG qua /api/login)\n")

    http_client = httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"})
    async with streamable_http_client(settings.mcp_server_url, http_client=http_client) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tool khả dụng (luôn hiện đủ, phân quyền chặn ở lúc GỌI):")
            for t in tools.tools:
                print(f"  - {t.name}")
            print()

            calls = [
                ("search_scam_patterns", {"query": ""}),
                ("list_hotlines", {}),
                ("summarize_pending_reports", {}),
            ]
            for tool_name, arguments in calls:
                try:
                    result = await session.call_tool(tool_name, arguments)
                    if result.is_error:
                        print(f"[BỊ CHẶN] {tool_name}: {result.content}")
                    else:
                        print(f"[OK] {tool_name}: {len(result.content)} phần kết quả")
                except Exception as e:
                    print(f"[LỖI] {tool_name}: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Cách dùng: python demo_mcp_client.py <username> <role>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
