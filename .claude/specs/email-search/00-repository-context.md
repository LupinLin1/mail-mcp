# Mail MCP Server - Repository Context Analysis

## 📊 Repository Overview

### Project Identity
- **Name**: Mail MCP Server
- **Version**: v2.1.0
- **Type**: MCP (Model Context Protocol) Server / Python Package
- **Purpose**: High-performance email management server with trusted sender filtering
- **License**: MIT
- **Language**: Python (3.8+)

### Repository Structure
```
mail-mcp/
├── mail_mcp/                    # Main package
│   ├── main.py                  # MCP server entry point (3 core tools)
│   ├── config.py                # Configuration management + trusted senders
│   ├── imap_service.py          # IMAP service + caching integration
│   ├── smtp_service.py          # SMTP service + connection pooling
│   ├── connection_pool.py       # Connection pool management (v2.0 feature)
│   ├── cache.py                 # Caching management (v2.0 feature)
│   ├── performance.py           # Performance monitoring (v2.0 feature)
│   ├── models.py                # Data models and validation
│   ├── errors.py                # Comprehensive error handling
│   └── utils.py                 # Utility functions
├── tests/                       # Comprehensive test suite (19 test files)
├── .github/                     # CI/CD workflows
├── .claude/                     # Claude Code integration
├── .taskmaster/                 # Task Master AI integration
├── docs/                        # Documentation
└── Configuration files...
```

## 🛠️ Technology Stack

### Core Framework
- **FastMCP**: Primary framework for MCP server implementation
- **asyncio**: Asynchronous processing for high concurrency
- **Python Standard Library**: Email handling (imaplib, smtplib, email)

### Key Dependencies
```toml
[dependencies]
fastmcp = ">=0.4.0"              # MCP server framework
python-dotenv = ">=1.0.0"        # Environment variable management
aiohttp = ">=3.8.0"              # Async HTTP client
click = ">=8.0.0"                # CLI interface
requests = ">=2.25.0"            # HTTP requests
psutil = ">=5.8.0"               # System performance monitoring
```

### Development Tools
```toml
[dev-dependencies]
pytest = ">=7.0.0"               # Testing framework
pytest-asyncio = ">=0.21.0"     # Async testing support
black = ">=23.0.0"               # Code formatting
isort = ">=5.0.0"                # Import sorting
flake8 = ">=6.0.0"               # Linting
build = ">=0.10.0"               # Package building
twine = ">=4.0.0"                # PyPI publishing
```

## 🏗️ Architecture Analysis

### v2.0 Architecture Highlights
1. **Simplified MCP Tools**: Reduced from 12 tools to 3 core tools:
   - `check`: Smart email checking for trusted senders
   - `reply`: Intelligent email reply with attachments
   - `download_attachments`: Attachment download management
   - `performance_stats`: System monitoring

2. **Performance Optimization Layer**:
   - **Connection Pool**: IMAP/SMTP connection reuse
   - **Intelligent Caching**: LRU cache for email data
   - **Performance Monitoring**: Real-time metrics collection
   - **Async Architecture**: Full asynchronous processing

3. **Security Architecture**:
   - **Trusted Sender Filtering**: Whitelist-based security
   - **Input Validation**: Comprehensive parameter validation
   - **Error Classification**: Structured error handling system
   - **SSL/TLS Support**: Encrypted communications

### Component Design Patterns
- **Service Layer Pattern**: Separate IMAP/SMTP services
- **Configuration Management**: Dataclass-based configuration
- **Error Handling Strategy**: Hierarchical error classification
- **Caching Strategy**: LRU cache with performance monitoring
- **Connection Pooling**: Resource optimization pattern

## 🔧 Development Workflow

### Git Workflow
- **Current Branch**: `v2-refactor`
- **Recent Development**: Major v2.0 rewrite focused on performance
- **Branching Strategy**: Feature branches with main/master

### Testing Strategy
- **Framework**: pytest with asyncio support
- **Coverage**: 19 test files covering core functionality
- **Test Types**: Unit tests, integration tests, performance tests
- **CI/CD**: GitHub Actions for automated testing and publishing

### Code Quality Standards
- **Formatting**: Black (line length: 88)
- **Import Sorting**: isort with Black profile
- **Linting**: flake8 for code quality
- **Type Hints**: Comprehensive type annotations
- **Documentation**: Chinese documentation with English code

## 📋 Configuration Management

### Environment Variables Pattern
```bash
# v2.0 Simplified Configuration
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USE_SSL=true
SMTP_HOST=smtp.example.com
SMTP_PORT=587
TRUSTED_SENDERS=admin@company.com,boss@company.com
```

### Supported Email Providers
- Gmail (imap.gmail.com, smtp.gmail.com)
- QQ Mail (imap.qq.com, smtp.qq.com) - Recommended
- Outlook (outlook.office365.com, smtp-mail.outlook.com)
- 163 Mail (imap.163.com, smtp.163.com)
- Enterprise email servers

### Security Configuration
- **Trusted Senders**: Core v2.0 security feature
- **App Passwords**: Required for most providers
- **SSL/TLS**: Configurable encryption settings

## 🚀 Deployment & Distribution

### Package Distribution
- **PyPI**: Available as `mail-mcp` package
- **Installation**: `pip install mail-mcp` or `uvx mail-mcp`
- **Entry Points**: 
  - `mail-mcp`: Main server
  - `mail-mcp-setup`: Configuration helper
  - `mail-mcp-config`: Configuration tool

### MCP Integration
- **Claude Code**: Native MCP server integration
- **uvx Support**: Zero-installation deployment
- **Configuration**: JSON-based MCP server configuration

### CI/CD Pipeline
- **GitHub Actions**: Automated build and publish
- **PyPI Publishing**: Automated package publishing on tags
- **Release Management**: Automated GitHub releases

## 📊 Performance Characteristics

### v2.0 Performance Improvements
- **50%+ faster response times** (via connection pooling)
- **80%+ cache hit rate** (intelligent caching)
- **10x concurrent processing capacity** (async architecture)
- **90% reduction in connection overhead**

### Monitoring & Metrics
- Connection pool statistics
- Cache performance metrics
- Response time measurements
- Error rate tracking

## 🔒 Security & Error Handling

### Error Classification System
```python
class ErrorCategory(Enum):
    CONFIGURATION = "configuration"    # 1000-1999
    NETWORK = "network"               # 2000-2999
    AUTHENTICATION = "authentication" # 3000-3999
    VALIDATION = "validation"         # 4000-4999
    FILE_SYSTEM = "file_system"      # 5000-5999
    EMAIL_PARSING = "email_parsing"   # 6000-6999
    PROTOCOL = "protocol"             # 7000-7999
```

### Security Best Practices
- Whitelist-based trusted sender filtering
- Application password requirements
- SSL/TLS encryption support
- Input validation and sanitization
- Error message sanitization

## 🧪 Testing & Quality Assurance

### Test Coverage Areas
- Configuration management testing
- IMAP/SMTP service testing
- Connection pool testing
- Cache performance testing
- Error handling testing
- Integration testing
- Performance benchmarking

### Quality Metrics
- 19 test files with comprehensive coverage
- Type safety with full annotations
- Code formatting with Black
- Import organization with isort
- Linting with flake8

## 🔄 Migration & Compatibility

### v1.x to v2.0 Migration
- **Breaking Changes**: Complete API rewrite
- **Tool Consolidation**: 12 tools → 3 core tools
- **Configuration Changes**: Simplified environment variables
- **Performance Upgrades**: New caching and pooling systems

### Compatibility Matrix
- **Python**: 3.8+ (supports 3.8 through 3.12)
- **Operating Systems**: Cross-platform (Windows, macOS, Linux)
- **Email Providers**: Major providers supported
- **MCP Clients**: Claude Code, compatible MCP clients

## 📖 Documentation Standards

### Documentation Language
- **User Documentation**: Chinese (README, CHANGELOG)
- **Code Documentation**: English (docstrings, comments)
- **API Documentation**: Chinese with English examples

### Documentation Types
- README with comprehensive setup guide
- CHANGELOG with detailed version history
- Configuration examples for major email providers
- Migration guide from v1.x
- Performance optimization guide

## 🎯 Integration Points

### Claude Code Integration
- `.claude/` directory for Claude Code configuration
- Custom commands and agents
- MCP server configuration examples
- Tool allowlist recommendations

### Task Master AI Integration
- `.taskmaster/` directory for project management
- Task tracking and planning
- AI-powered development workflow
- Project documentation templates

### External Services
- **Email Providers**: IMAP/SMTP protocol support
- **MCP Clients**: FastMCP framework compatibility
- **Package Registries**: PyPI distribution
- **CI/CD**: GitHub Actions integration

## 🔮 Architecture Implications for New Features

### Extensibility Points
1. **MCP Tools**: Easy to add new tools via FastMCP
2. **Service Layer**: Modular IMAP/SMTP service extension
3. **Caching**: Pluggable cache backends
4. **Monitoring**: Extensible performance metrics
5. **Error Handling**: Hierarchical error classification

### Performance Considerations
- Connection pooling limits (3 IMAP, 2 SMTP)
- Cache size limits (configurable)
- Async processing requirements
- Memory usage optimization

### Security Considerations
- Trusted sender validation
- Input sanitization requirements
- SSL/TLS configuration
- Error message sanitization

### Development Guidelines
- Follow existing code patterns
- Maintain type safety
- Add comprehensive tests
- Update documentation
- Consider performance impact
- Follow Chinese documentation standards

---

This repository represents a mature, production-ready MCP server with a focus on performance, security, and developer experience. The v2.0 architecture provides a solid foundation for extending email functionality while maintaining high performance and security standards.