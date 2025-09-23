# Email Search Requirements Confirmation

## Original Request
**Feature**: 搜索邮件 (Email Search)

## Repository Context Impact
- **Integration Point**: Add as new MCP tool `search` to existing architecture
- **Technology Stack**: Python async/await patterns, FastMCP framework
- **Existing Patterns**: Follow IMAP connection patterns from `check` tool
- **Code Style**: Chinese documentation, English code comments, type annotations
- **Error Handling**: Integrate with existing error classification system

## Clarification Rounds

### Round 1: Initial Questions
**Questions Asked**: Search scope, criteria, filters, integration approach, performance requirements, output format

### Round 2: User Response Analysis
**User provided detailed requirements**:

1. **搜索范围**: 收件箱 + 已发送邮件 (不包括垃圾邮件)
2. **搜索字段**: 邮件主题 + 正文内容
3. **搜索模式**: 关键词 + 模糊搜索 (不支持正则表达式)
4. **筛选条件**: 日期范围筛选
5. **结果处理**: 不限制数量 + 支持分页 + 按日期排序(新的在前)
6. **集成方式**: 新MCP工具
7. **性能要求**: 无特殊响应时间要求，不需要缓存
8. **输出格式**: 邮件基本信息 + 邮件摘要 + 唯一标识符
9. **使用场景**: 快速查找特定邮件

## Final Confirmed Requirements

### Functional Specifications

#### 1. Search Scope
- **Target Folders**: INBOX + Sent (排除垃圾邮件文件夹)
- **Search Fields**: Subject + Body content
- **Search Mode**: Keyword-based fuzzy search (no regex support)

#### 2. Search Parameters
```python
SearchRequest:
- query: str (搜索关键词, required)
- date_from: Optional[str] (开始日期, format: YYYY-MM-DD)
- date_to: Optional[str] (结束日期, format: YYYY-MM-DD) 
- page: Optional[int] (页码, default: 1)
- page_size: Optional[int] (每页大小, default: 20)
```

#### 3. Result Format
```python
SearchResult:
- total_count: int (总结果数)
- current_page: int (当前页码)
- total_pages: int (总页数)
- emails: List[EmailResult]

EmailResult:
- uid: str (邮件唯一标识符)
- subject: str (邮件主题)
- sender: str (发件人)
- recipient: str (收件人)
- date: str (邮件日期)
- folder: str (所在文件夹: "INBOX" | "Sent")
- summary: str (邮件内容摘要, ~200字符)
- has_attachments: bool (是否有附件)
```

#### 4. Sorting & Pagination
- **Default Sort**: 按日期降序 (最新邮件在前)
- **Pagination**: 支持分页，默认每页20条
- **No Limit**: 不限制总结果数量

### Technical Specifications

#### 1. MCP Tool Integration
- **Tool Name**: `search`
- **Framework**: FastMCP following existing patterns
- **IMAP Integration**: Reuse connection patterns from existing tools
- **Error Handling**: Integrate with existing error classification

#### 2. Implementation Approach
- **No Caching**: 实时搜索，不实现结果缓存
- **Performance**: 无特殊性能要求，优先功能完整性
- **Async Support**: 遵循现有async/await模式
- **Security**: 遵循现有安全模型

#### 3. Search Algorithm
- **Fuzzy Matching**: 支持部分匹配和相似词匹配
- **Multi-field Search**: 同时搜索主题和正文
- **Date Filtering**: 在IMAP层面进行日期筛选优化
- **Folder Filtering**: 明确限制在INBOX和Sent文件夹

### Integration Points
1. **mail_client.py**: 扩展邮件客户端添加搜索方法
2. **main.py**: 添加新的`search` MCP工具
3. **existing patterns**: 遵循现有工具的参数验证和错误处理
4. **logging**: 集成现有日志系统

### Quality Score Assessment

| Category | Score | Analysis |
|----------|-------|----------|
| **Functional Clarity (30 points)** | 28/30 | 明确的搜索范围、字段、模式和结果格式 |
| **Technical Specificity (25 points)** | 24/25 | 详细的技术规范和集成方案 |
| **Implementation Completeness (25 points)** | 23/25 | 完整的API设计和错误处理考虑 |
| **Business Context (20 points)** | 19/20 | 明确的使用场景和用户价值 |

**Final Quality Score: 94/100** ✅

## Repository Integration Summary
- 新增`search` MCP工具集成到现有架构
- 遵循现有代码风格和错误处理模式  
- 利用现有IMAP连接基础设施
- 无性能优化要求，专注功能实现
- 支持中文文档风格，保持代码英文注释

## Implementation Ready
Requirements achieve 94/100 quality score and are ready for implementation phase.