#!/bin/bash

# Mail MCP 启动脚本
# 设置环境变量
export PYTHONPATH="/app/mail-mcp"
export IMAP_HOST="imap.qq.com"
export IMAP_PORT="993"
export IMAP_USE_SSL="true"
export IMAP_USERNAME="yingke_20@qq.com"
export IMAP_PASSWORD="qpenmibvbmrjdabj"
export SMTP_HOST="smtp.qq.com"
export SMTP_PORT="465"
export SMTP_USE_SSL="true"
export SMTP_USERNAME="yingke_20@qq.com"
export SMTP_PASSWORD="qpenmibvbmrjdabj"
export HOST="localhost"
export PORT="8000"
export LOG_LEVEL="INFO"
export TRUSTED_SENDERS="lupin.lin@qq.com,7585525@qq.com"

# 启动 Mail MCP
exec python -m mail_mcp.main "$@"