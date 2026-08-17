# Remote Expense Tracker MCP Server

A deployed, cloud-ready Model Context Protocol (MCP) server for tracking, listing, and summarizing expenses over HTTP / SSE transport.

- **Deployed Endpoint**: [`https://remote-server-sb.fastmcp.app/mcp`](https://remote-server-sb.fastmcp.app/mcp)
- **Transport**: Streamable HTTP / Server-Sent Events (SSE)
- **Framework**: FastMCP (`fastmcp` v3.4.7+)
- **Database Engine**: Async SQLite (`aiosqlite`) with WAL mode

---

## 🚀 Connecting to Deployed Server

To connect your MCP client (e.g., Claude Desktop, Cursor, or an AI Agent host) to this deployed remote MCP server over HTTP:

### Client Configuration (`claude_desktop_config.json` or MCP Client Config)

```json
{
  "mcpServers": {
    "remote-expense-tracker": {
      "url": "https://remote-server-sb.fastmcp.app/mcp"
    }
  }
}
```

---

## 🛠️ MCP Tools & Resources

### Tools exposed in [`main.py`](file:///Users/shlokbam/Documents/Code/MCP%20%28Model%20Context%20Protocol%29/Remote_Server/main.py)

1. **`add_expense`** (`async`)
   - **Description**: Add a new expense entry to SQLite database (`date`, `amount`, `category`, `subcategory`, `note`).
   - **Returns**: `{"status": "success", "id": <id>, "message": "Expense added successfully"}`

2. **`list_expenses`** (`async`)
   - **Description**: List expense entries within an inclusive date range ordered by date and ID descending.
   - **Parameters**: `start_date`, `end_date`

3. **`summarize`** (`async`)
   - **Description**: Summarize expenses by category within a date range with optional category filter. Returns `total_amount` and entry count.
   - **Parameters**: `start_date`, `end_date`, `category=None`

### Resource

- **URI**: `expense:///categories` (`application/json`)
- **Description**: Serves fresh category taxonomy from [`categories.json`](file:///Users/shlokbam/Documents/Code/MCP%20%28Model%20Context%20Protocol%29/Remote_Server/categories.json) with automatic fallback defaults.

---

## ⚙️ Architecture & Design

- **Async Database Handling**: Built with `aiosqlite` to handle non-blocking concurrent async requests in cloud environments.
- **WAL Journaling Mode**: SQLite configured with `PRAGMA journal_mode=WAL` for concurrent read/write operations.
- **Serverless Writable Storage**: Database path set to `tempfile.gettempdir()` (`/tmp/expenses.db`) to ensure write permissions across containerized cloud runtimes (e.g. Prefect Horizon / FastMCP Cloud).

---

## 💻 Local Development

### 1. Install Dependencies
```zsh
uv sync
```

### 2. Run Local HTTP Server (Port 8000)
```zsh
uv run main.py
```

### 3. Run Dev Inspector
```zsh
uv run fastmcp dev inspector main.py
```
