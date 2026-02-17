# LeonelResponde Architecture Documentation

## Project Overview

**LeonelResponde** is a multimodal offline AI assistant designed for resource-constrained devices (Jetson Nano, Raspberry Pi, laptops) with:
- Local LLM engine with quantized models (GGUF format)
- Advanced memory management system (short/long-term memory)
- Knowledge base with vector embeddings (RAG)
- Multiple UI interfaces (console, PySide6, React frontend)
- REST API for programmatic access
- MCP (Model Context Protocol) server integration

**Current Phase**: Phase 1 - Core LLM engine with memory and knowledge base

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LEONEL RESPONDE SYSTEM                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              User Interfaces (Multiple)              │   │
│  │  ├─ React Frontend (TypeScript/Vite + Socket.IO)   │   │
│  │  ├─ Console UI (Interactive mode)                  │   │
│  │  └─ PySide6 UI (Desktop GUI)                       │   │
│  └──────────────────────────────────────────────────────┘   │
│           │         │                    │                   │
│  ┌────────┴─────────┴────────────────────┴────────────────┐  │
│  │              API Layer (FastAPI)                       │  │
│  │  • /query - LLM queries with context                 │  │
│  │  • /status - System status                          │  │
│  │  • /clear-memory - Memory management               │  │
│  │  • /add-document - Knowledge base updates          │  │
│  └────────────────────────────────────────────────────────┘  │
│           │                      │           │                │
│  ┌────────┴──────────┬───────────┴─────┬────┴────────────┐   │
│  │                   │                 │                 │    │
│  │                   ▼                 ▼                 ▼    │
│  │  ┌────────────────────────────────────────────────────┐   │
│  │  │          Core Backend Components                   │   │
│  │  ├─ LLM Manager (Model Loading/Inference)           │   │
│  │  ├─ Memory Service (LangChain-based)                │   │
│  │  ├─ Knowledge Base (FAISS + Embeddings)             │   │
│  │  ├─ Resource Monitor (CPU/Memory/GPU)               │   │
│  │  ├─ Backup Manager (Persistence)                    │   │
│  │  └─ Error Handler (Unified error management)        │   │
│  └────────────────────────────────────────────────────────┘  │
│           │                      │                  │         │
│           ▼                      ▼                  ▼         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │   LLM Models     │  │  Memory Store    │  │ Knowledge  │ │
│  │ (GGUF quantized) │  │ (JSON + SQLite)  │  │ Base Index │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         MCP Event Integration System                   │  │
│  │  • Event queue-based architecture                     │  │
│  │  • Server protocols (Voice, Memory, Filesystem)      │  │
│  │  • Async event processing with thread pool            │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Patterns

### 1. **Lazy Loading & Dependency Injection**
- **Pattern**: Lazy imports in `main.py` to optimize startup time
- **Purpose**: Avoid circular dependencies and reduce initial memory footprint
- **Example**: `_get_config()`, `_get_logger()`, `_get_component_initializer()`
- **Location**: `/Assistant/main.py` (lines 72-155)

### 2. **Unified Configuration**
- **Pattern**: Singleton configuration manager with dataclass-based sections
- **Purpose**: Single source of truth for all application settings
- **Key Sections**:
  - `PathConfig`: Directory structure and file locations
  - `LLMConfig`: Model parameters, inference settings
  - `MemoryConfig`: Memory management strategy (with LangChain integration)
  - `KnowledgeBaseConfig`: Embedding and RAG settings
  - `SystemConfig`: API, monitoring, performance settings
- **Location**: `/Assistant/src/backend/utils/unified_config.py`
- **Features**:
  - Environment variable overrides (e.g., `ENABLE_LANGCHAIN_MEMORY`)
  - Automatic directory creation
  - MCP configuration loading from JSON
  - Backwards compatibility exports

### 3. **Centralized Error Handling**
- **Pattern**: Error handler with context, severity levels, and categories
- **Purpose**: Consistent error reporting and recovery strategies
- **Implementation**: `ErrorHandler` with `ErrorCategory` and `ErrorSeverity` enums
- **Location**: `/Assistant/src/backend/utils/error_handler.py`
- **Features**: 
  - Resilient operations with retry logic
  - Context-aware error logging
  - Fallback strategies per component

### 4. **Component Initialization Pattern**
- **Pattern**: Factory functions with staged initialization
- **Purpose**: Manage startup sequence, handle optional components, enable dry-init mode
- **Key Function**: `initialize_components()` (returns dict of initialized systems)
- **Location**: `/Assistant/src/backend/core/component_initializer.py`
- **Features**:
  - Dry-init mode for lightweight testing
  - Individual component error isolation
  - Automatic fallback handling
  - Resource monitoring integration

### 5. **Event-Driven MCP Integration**
- **Pattern**: Event queue with background worker thread
- **Purpose**: Bridge between MCP servers and internal event system
- **Architecture**:
  - `MCPEventBridge`: Main coordinator
  - `LocalEventSystem`: Fallback implementation
  - Queue-based async processing
  - Typed event protocols
- **Location**: `/Assistant/src/backend/mcp_event_integration.py`
- **Server Types**: Voice, Memory, SQLite, Filesystem

### 6. **UI Abstraction Layer**
- **Pattern**: Adapter pattern for multiple UI implementations
- **Purpose**: Switch between console, PySide6, and web UIs without code changes
- **Implementations**:
  - `ConsoleUI`: Terminal-based interface
  - `PySide6UI`: Desktop graphical interface
  - `AdaptiveInteractiveMode`: Route to appropriate UI
- **Location**: `/Assistant/src/backend/ui/`

### 7. **Memory Architecture (Tiered)**
- **Pattern**: Multi-layer memory with automatic transitions
- **Components**:
  - **Short-term**: Recent interactions (in-memory cache)
  - **Long-term**: Persistent storage (JSON/SQLite)
  - **LangChain Integration**: Optional conversational memory with summaries
- **Purpose**: Balance performance with persistence
- **Location**: `/Assistant/src/backend/memory/memory_service.py`

### 8. **Knowledge Base (RAG Pattern)**
- **Pattern**: Vector database with semantic search
- **Technology**: 
  - FAISS for vector indexing
  - SentenceTransformers for embeddings
  - JSON for document storage
- **Purpose**: Semantic retrieval for context-aware responses
- **Location**: `/Assistant/src/backend/llm/knowledge_base.py`

### 9. **Unified Logging System**
- **Pattern**: Structured logging with operation context
- **Purpose**: Trace execution flow and performance metrics
- **Features**:
  - JSON-formatted structured logs
  - Context managers for operation tracking
  - Dynamic log level control
  - E2E timing and tracing
- **Location**: `/Assistant/src/backend/utils/unified_logger.py`

### 10. **Resource Monitoring & Protection**
- **Pattern**: Threshold-based alerts with callbacks
- **Purpose**: Prevent system overload and kernel panics
- **Monitors**: CPU, Memory, GPU, Disk
- **Location**: `/Assistant/src/backend/utils/resource_monitor.py`

---

## Directory Structure

### Backend (`/Assistant/src/backend/`)

```
src/backend/
├── api.py                         # FastAPI REST endpoints
├── mcp_event_integration.py       # MCP server bridge
│
├── core/
│   ├── component_initializer.py  # Startup orchestration
│   ├── service_manager.py         # Service lifecycle
│   └── context_manager.py         # Context management
│
├── llm/
│   ├── model_manager.py           # LLM loading/inference (llama-cpp-python)
│   ├── knowledge_base.py          # FAISS + embeddings for RAG
│   ├── leonel_personality.py      # Personality/persona system
│   ├── leonel_response_generator.py  # Response generation pipeline
│   └── smart_context.py           # Context assembly logic
│
├── memory/
│   ├── memory_service.py          # Main memory orchestrator (LangChain)
│   └── personal_info_extractor.py # User info extraction
│
├── ui/
│   ├── console_ui.py              # Terminal interface
│   ├── pyside6_ui.py              # Desktop GUI (Qt)
│   ├── pyside6_web_ui.py          # Web-based GUI option
│   ├── adaptive_interactive_mode.py  # UI routing
│   ├── interactive_mode.py        # Command handling
│   ├── ui_abstraction.py          # UI interface contract
│   └── command_handlers.py        # CLI command processing
│
├── context/
│   └── text_context_processor.py  # Context extraction/assembly
│
├── utils/
│   ├── unified_config.py          # Configuration manager
│   ├── unified_logger.py          # Structured logging
│   ├── error_handler.py           # Error management
│   ├── resource_monitor.py        # System monitoring
│   ├── backup_manager.py          # Persistence/backups
│   ├── validators.py              # Input validation
│   ├── tracing.py                 # Performance tracing
│   ├── dependency_validator.py    # Dependency checking
│   └── system_protection.py       # Kernel panic prevention
│
├── vision/                        # Vision processing (phase 2)
├── voice/                         # Voice processing (phase 2)
├── finetuning/                    # Model fine-tuning (phase 4)
└── social/                        # Social/persona features (phase 3)
```

### Frontend (`/frontend/`)

```
frontend/
├── src/
│   ├── App.tsx                    # Main app component
│   ├── main.tsx                   # Entry point
│   ├── index.css                  # Tailwind styles
│   │
│   ├── components/
│   │   ├── ChatInterface.tsx       # Main chat UI
│   │   ├── MessageBubble.tsx       # Message rendering
│   │   ├── InputField.tsx          # User input
│   │   ├── Header.tsx              # Header/status
│   │   └── StatusIndicator.tsx     # System status
│   │
│   ├── services/
│   │   ├── api.ts                  # HTTP client (axios)
│   │   └── websocket.ts            # WebSocket connection
│   │
│   └── store/
│       ├── chatStore.ts            # Chat state (Zustand)
│       └── settingsStore.ts        # Settings state
│
├── package.json                   # Dependencies (React 19, Vite, TypeScript)
├── vite.config.ts                 # Vite configuration
└── tailwind.config.js             # Tailwind CSS config
```

### Root Configuration Files

```
/Assistant/
├── main.py                        # Entry point
├── pyproject.toml                 # Project metadata
├── requirements.txt               # Runtime dependencies
├── requirements-dev.txt           # Dev tools (pytest, mypy, ruff, black)
├── mcp_config.json                # MCP server configuration
├── pyrightconfig.json             # Type checking config
└── env.example                    # Environment template
```

---

## Core Components & Interactions

### 1. **LLM Manager** (`model_manager.py`)
**Responsibility**: Load and manage language models
```python
class LLMManager:
    - load_model(model_path): Load GGUF quantized model
    - query(prompt): Generate response
    - query_with_context(prompt, context): Augmented generation
    - get_status(): Return model info and stats
```

### 2. **Memory Service** (`memory_service.py`)
**Responsibility**: Manage conversation history with LangChain integration
```python
class MemoryService:
    - add_interaction(user_msg, assistant_response): Store exchange
    - get_recent_context(k=5): Get recent interactions
    - get_relevant_memory(query, max_items=3): Semantic search
    - reset(): Clear memory
    - save_memory(): Persist to disk
```

### 3. **Knowledge Base** (`knowledge_base.py`)
**Responsibility**: RAG (Retrieval-Augmented Generation) system
```python
class KnowledgeBase:
    - initialize_index(): Setup FAISS embeddings
    - query(text, top_k=2): Retrieve relevant documents
    - add_document(content, metadata): Add to knowledge base
    - save_embedding_cache(): Persist embeddings
```

### 4. **API Server** (`api.py`)
**Responsibility**: REST interface
**Endpoints**:
- `GET /` - Health check
- `GET /status` - System status
- `POST /query` - LLM query with optional RAG/memory
- `POST /clear-memory` - Memory management
- `POST /add-document` - Knowledge base update

### 5. **Component Initializer** (`component_initializer.py`)
**Responsibility**: Orchestrate startup sequence
**Key Function**: `initialize_components(dry_init=False)`
**Initializes**:
1. LLM Manager
2. Memory Service
3. Knowledge Base
4. Resource Monitor
5. Backup Manager

### 6. **Unified Config** (`unified_config.py`)
**Responsibility**: Central configuration
**Key Features**:
- Singleton pattern with `get_config()`
- Environment variable overrides
- Automatic directory creation
- LangChain memory toggle via `ENABLE_LANGCHAIN_MEMORY`

---

## Execution Flow

### Startup Sequence (main.py)
```
1. _configure_environment()
   └─ Load unified config
   └─ Set environment variables

2. validate_system_configuration()
   └─ Check paths, model availability, settings

3. initialize_optimized_system()
   └─ Auto-detect hardware
   └─ Apply performance optimizations

4. initialize_system_protection()
   └─ Start resource monitoring

5. initialize_system_components(dry_init=False)
   └─ LLM Manager
   └─ Memory Service
   └─ Knowledge Base
   └─ Resource Monitor
   └─ Backup Manager

6. Execute requested mode:
   ├─ Interactive (Console/PySide6)
   │  └─ adaptive_interactive_mode(components, ui_type)
   ├─ API Server
   │  └─ start_api(host, port)
   └─ Tests
      └─ run_integration_tests()

7. cleanup_system_resources()
   └─ Save memory
   └─ Persist knowledge base
   └─ Stop monitors
```

### Query Processing (API)
```
POST /query
├─ Validate input
├─ If RAG enabled:
│  └─ Query knowledge base (FAISS)
├─ If memory enabled:
│  ├─ Get recent context (short-term)
│  └─ Get relevant memories (long-term)
├─ Combine contexts
├─ Call LLM with prompt + context
├─ Store interaction in memory
└─ Return response with timing/tokens
```

---

## Configuration Patterns

### Environment Variables
```bash
# LangChain Memory Toggle
ENABLE_LANGCHAIN_MEMORY=true|false

# System
PYTHONIOENCODING=utf-8
PYTORCH_ENABLE_MPS_FALLBACK=1
TOKENIZERS_PARALLELISM=false
```

### Key Configuration Sections
```python
config = get_config()

# LLM Settings
config.llm.model_name          # Model filename
config.llm.max_tokens          # Response length
config.llm.temperature         # Creativity (0.0-2.0)
config.llm.response_timeout    # Timeout in seconds

# Memory Settings
config.memory.enable_long_term_memory  # Enable persistence
config.memory.max_short_term_memory    # Cache size
config.memory.langchain.enable         # LangChain toggle
config.memory.langchain.window_k       # Context window

# Knowledge Base
config.knowledge_base.embedding_model     # all-MiniLM-L6-v2
config.knowledge_base.chunk_size          # Text chunks
config.knowledge_base.similarity_threshold  # Search filter

# System
config.system.api_host         # Default: 127.0.0.1
config.system.api_port         # Default: 8000
config.system.debug_mode       # Enable verbose logging
```

---

## Integration Points

### MCP (Model Context Protocol)
- **Integration**: `MCPEventBridge` in `mcp_event_integration.py`
- **Server Types**: Voice, Memory, SQLite, Filesystem
- **Pattern**: Event queue → Background worker → Event emission
- **Configuration**: `mcp_config.json`

### LangChain Integration
- **Memory**: Optional conversational memory with summaries
- **Toggle**: Environment variable `ENABLE_LANGCHAIN_MEMORY`
- **Purpose**: Enhanced context window management
- **Location**: `config.memory.langchain` settings

### Frontend-Backend Communication
- **Primary**: REST API (FastAPI)
- **Optional**: WebSocket (Socket.IO) for real-time events
- **Frontend Stack**: React 19 + TypeScript + Vite + Zustand
- **Styling**: Tailwind CSS

---

## Testing Strategy

### Test Files Location
`/Assistant/tests/`
- `unit/` - Individual component tests
- `integration/` - System-wide tests
- `performance/` - Benchmark tests
- `fixtures/` - Test fixtures and mocks

### Test Tools
- **pytest**: Test framework
- **mypy**: Type checking
- **ruff**: Linting and code style
- **black**: Code formatting
- **pytest-forked**: Process isolation

### Quality Gates
- All tests must pass
- Type checking with mypy
- Code style enforcement with ruff and black
- Safe merge to main requires CI workflow

---

## Performance Optimization

### Resource Constraints
- **Target Devices**: Jetson Nano, Raspberry Pi, laptops with limited RAM
- **Memory Budget**: 256-512MB for cache
- **Model Size**: Quantized GGUF models (3-5GB)

### Optimization Strategies
1. **Lazy Loading**: Import modules only when needed
2. **Caching**: Embeddings, model inference results
3. **Threading**: Non-blocking I/O operations
4. **Thresholds**: Early warnings at 50-60% resource usage
5. **Compression**: Optional memory/backup compression

### Configuration Tuning
```python
# For constrained devices:
config.llm.n_gpu_layers = 10        # Fewer GPU layers
config.llm.batch_size = 128         # Smaller batch
config.memory.cache_size = 50       # Smaller cache
config.memory.max_short_term = 20   # Fewer interactions
config.system.max_concurrent_requests = 2
```

---

## Development Workflow

### Adding a New Feature
1. **Update Configuration** (`unified_config.py`)
   - Add dataclass with defaults
   - Register in `UnifiedConfig.__init__`

2. **Implement Component** (`src/backend/...`)
   - Follow error handling patterns
   - Use structured logging
   - Add to component initialization

3. **Add to Initialization** (`component_initializer.py`)
   - Register in `initialize_components()`
   - Add cleanup in `cleanup_components()`

4. **Update API** if needed (`api.py`)
   - Add endpoints
   - Use FastAPI models
   - Add error handling

5. **Test**
   - Add unit tests (`tests/unit/`)
   - Add integration tests (`tests/integration/`)
   - Run quality checks

6. **Document**
   - Update component docstrings
   - Add to architecture docs if significant

### Common Patterns to Use
```python
# Configuration access
from src.backend.utils.unified_config import get_config
config = get_config()

# Logging
from src.backend.utils.unified_logger import get_unified_logger
logger = get_unified_logger("MyComponent")
logger.info("Message", extra_field=value)

# Error handling
from src.backend.utils.error_handler import resilient_operation
with resilient_operation("my_operation", "action_name"):
    # Your code here
    pass

# Component cleanup
def cleanup_my_component(components):
    if components.get("my_component"):
        components["my_component"].shutdown()
```

---

## Key Decisions & Trade-offs

| Decision | Rationale |
|----------|-----------|
| Quantized GGUF models | Reduced memory footprint for constrained devices |
| Lazy imports in main.py | Minimize startup time and circular dependencies |
| LangChain optional | Flexibility without hard dependency |
| Queue-based MCP events | Async processing without blocking main thread |
| Singleton config | Single source of truth, easier testing |
| Multi-UI support | Same core works with console/GUI/web |
| JSON for memory | Human-readable, portable, but slower than binary |
| FAISS for knowledge base | Fast vector search, pure Python, CPU-friendly |

---

## Future Enhancements (Phases 2-4)

- **Phase 2**: Voice integration (STT/TTS)
- **Phase 3**: Vision processing (image recognition)
- **Phase 4**: Fine-tuning system (LoRA/QLoRA)
- **Phase 5**: Advanced personas and social features
- **Optimization**: Distributed inference, GPU acceleration

---

## Running the System

### Interactive Mode (Console)
```bash
python main.py --interactive
```

### API Server
```bash
python main.py --api
```

### With GUI
```bash
python main.py --ui pyside6
```

### Testing
```bash
pytest tests/
mypy src/
ruff check src/
black --check src/
```

### Configuration
Edit `/Assistant/src/backend/utils/unified_config.py` for system settings.

---

*Last Updated: October 2024*
