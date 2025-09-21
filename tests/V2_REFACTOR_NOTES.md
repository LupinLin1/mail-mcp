# V2.0 重构 - 测试文件变更说明

## 概述
v2.0 重构将现有的9个MCP工具精简为2个：`check` 和 `reply`。

## 测试文件状态

### 保留的测试文件（核心服务）
- `test_config.py` - ✅ 保留：配置系统测试
- `test_models.py` - ✅ 保留：数据模型测试  
- `test_imap_service.py` - ✅ 保留：IMAP服务核心功能测试
- `test_smtp_service.py` - ✅ 保留：SMTP服务核心功能测试

### 需要重构的测试文件（工具相关）
以下测试文件对应的工具将被移除，需要重构为新的 `check` 和 `reply` 工具测试：

- `test_list_messages.py` - 🔄 重构：功能合并到 `check` 工具
- `test_get_message.py` - 🔄 重构：功能合并到 `check` 工具  
- `test_search_mark_functionality.py` - 🔄 重构：功能合并到 `check` 工具
- `test_attachment_tools.py` - 🔄 重构：功能合并到 `check` 工具
- `test_send_email_with_attachments.py` - 🔄 重构：功能合并到 `reply` 工具

### 新增测试文件（v2.0）
- `test_check_tool.py` - 📝 新增：测试新的 `check` 工具
- `test_reply_tool.py` - 📝 新增：测试新的 `reply` 工具

## 重构策略
1. 保留核心服务测试，确保底层功能稳定
2. 将工具测试重构为集成测试，测试新的 `check` 和 `reply` 工具
3. 确保测试覆盖率保持在80%以上
4. 添加可信发件人功能的测试用例

## 执行计划
1. ✅ 标记现有测试文件状态
2. 🔄 实现新的 `check` 和 `reply` 工具
3. 📝 编写新工具的测试用例
4. 🧪 运行完整测试套件
5. 📊 验证代码覆盖率

最后更新：$(date)