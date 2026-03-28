#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DramaSwarm 可视化服务器启动脚本

用法:
  python run_viz.py                  # 默认端口 8765
  python run_viz.py --port 3000      # 指定端口
  python run_viz.py --host 0.0.0.0   # 允许外部访问
"""

import argparse

# 加载 .env 环境变量（需在 import swarmsim 之前）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    parser = argparse.ArgumentParser(description="DramaSwarm GraphRAG 可视化")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8765, help="端口号")
    parser.add_argument("--reload", action="store_true", help="开发模式（自动重载）")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(
        "swarmsim.viz.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
