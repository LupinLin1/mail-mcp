#!/bin/bash
# Mail MCP 启动脚本，用于Claude Code CLI

export IMAP_HOST="imap.qq.com"
export IMAP_PORT="993"
export IMAP_USERNAME="yingke_20@qq.com"
export IMAP_PASSWORD="qpenmibvbmrjdabj"
export IMAP_USE_SSL="true"
export SMTP_HOST="smtp.qq.com"
export SMTP_PORT="465"
export SMTP_USERNAME="yingke_20@qq.com"
export SMTP_PASSWORD="qpenmibvbmrjdabj"
export SMTP_USE_TLS="true"
export TRUSTED_SENDERS="7585525@qq.com,lupin.lin@qq.com"

# 启动Mail MCP服务器 - 使用正确的入口点
exec mail-mcp "$@"
