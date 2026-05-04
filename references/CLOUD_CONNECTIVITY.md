# Cloud/Remote Connectivity for Pieces MCP

This reference covers connecting to Pieces MCP when the client and PiecesOS are on **different networks** -- i.e., you can't use LAN or localhost, and need an HTTPS tunnel.

For local/LAN setup (SSE, portproxy), see `MCP_ENDPOINTS.md` and `PREREQS.md`.

---

## 1) When to use cloud connectivity

Use this mode when:
- PiecesOS runs on machine A (e.g., your office Windows desktop)
- Your MCP client runs on machine B (e.g., a cloud server, a laptop on a different network, WSL on a remote host)
- Machines A and B are NOT on the same LAN

Do NOT use this mode when:
- Both are on the same machine (use `localhost:39300`)
- Both are on the same LAN (use the portproxy approach in `MCP_ENDPOINTS.md`)

---

## 2) Architecture

```
PiecesOS (port 39300)
        |
    localhost:39300
        |
   HTTPS tunnel (ngrok / Cloudflare / custom)
        |
   https://<tunnel-url>/model_context_protocol/2025-03-26/mcp
        |
   MCP client (via mcp-remote or direct curl)
```

**Key rule:** Cloud connections use `/mcp` (direct JSON-RPC), NOT `/sse` (Server-Sent Events). SSE requires a long-lived connection that does not tunnel reliably through HTTPS proxies.

---

## 3) Tunnel setup

### Option A: ngrok (most common)

On the PiecesOS machine:

```bash
# Install ngrok (one-time): https://ngrok.com/download
# Configure auth (one-time):
ngrok config add-authtoken <your-token>

# Start the tunnel:
ngrok http 39300
```

ngrok outputs a forwarding URL like:
```
https://abc123.ngrok-free.dev -> http://localhost:39300
```

**Important:** ngrok free tier assigns a new random URL every time you restart. For stable URLs, use a paid static domain or a different tunnel provider.

### Option B: Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:39300
```

Produces a URL like `https://random-words.trycloudflare.com`.

### Option C: Custom HTTPS proxy

Any reverse proxy (nginx, Caddy, Traefik, etc.) that terminates TLS and forwards to `localhost:39300` on the PiecesOS machine. The domain can be anything -- `pieces.yourdomain.com`, etc.

### Option D: Pieces team-provided tunnel

Pieces may provide a pre-configured tunnel URL like:
```
https://username.tunnel.company.stream
```

Use it the same way as any other tunnel URL.

---

## 4) Build and verify the MCP URL

Given a tunnel base URL, construct the MCP endpoint:

```
TUNNEL_BASE  = https://abc123.ngrok-free.dev
MCP_URL      = ${TUNNEL_BASE}/model_context_protocol/2025-03-26/mcp
```

### 4.1 Sanity check (always run first)

```bash
curl -i "https://abc123.ngrok-free.dev/model_context_protocol/2025-03-26/mcp"
```

**Expected success response (HTTP 400):**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32000,
    "message": "Bad Request: mcp-session-id header or sessionId query parameter is required"
  },
  "id": null
}
```

This 400 error is **good** -- it means:
- The route exists
- The MCP server is running
- It's ready to accept properly-formed requests

**If you get 404, 502, HTML, or timeout:** The tunnel is down or PiecesOS is not running. Fix that before proceeding.

---

## 5) Session management (direct curl)

When using the `/mcp` endpoint directly (not via mcp-remote), you manage sessions yourself.

### Session lifecycle

1. **Initialize** -- send a request with any client-chosen session ID
2. **Extract** -- get the server-assigned session ID from the response headers
3. **Reuse** -- use that server-assigned session ID for all subsequent requests

### Required headers (all requests)

```
Content-Type: application/json
Accept: application/json, text/event-stream
mcp-session-id: <SESSION_ID>
```

Missing either `Content-Type` or `Accept` will cause failures.

### Critical: use file-based JSON for curl

Shell quoting can mangle JSON -- zsh and bash handle quotes differently. **Always** use `--data-binary @file.json` instead of inline `-d '{...}'`.

### Critical: use string JSON-RPC IDs

Use `"id": "1"` (string), NOT `"id": 1` (integer). The server is sensitive to ID types.

### Step 1: Initialize

Create `init.json`:
```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "0.1.0",
    "capabilities": {},
    "clientInfo": {
      "name": "your-agent-name",
      "version": "1.0"
    }
  },
  "id": "1"
}
```

Send:
```bash
curl -i -X POST "https://abc123.ngrok-free.dev/model_context_protocol/2025-03-26/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: init-request-001" \
  --data-binary @init.json
```

**Extract the session ID from the response headers** (not the body):
```
HTTP/2 200
content-type: application/json
mcp-session-id: 1774202062499    <-- THIS is your session ID
```

The server-assigned session ID is typically a 13-digit Unix timestamp in milliseconds (e.g., `1774202062499`).

Response body:
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "protocolVersion": "0.1.0",
    "capabilities": { "tools": {} },
    "serverInfo": { "name": "pieces", "version": "1.0.0" }
  }
}
```

### Step 2: Query Long-Term Memory

Create `query.json`:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ask_pieces_ltm",
    "arguments": {
      "question": "What did I work on today?",
      "chat_llm": "gpt-4"
    }
  },
  "id": "2"
}
```

Send (using the server-assigned session ID):
```bash
curl -i -X POST "https://abc123.ngrok-free.dev/model_context_protocol/2025-03-26/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: 1774202062499" \
  --data-binary @query.json
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"summaries\":[...],\"events\":[...]}"
      }
    ]
  }
}
```

The `text` field contains raw JSON with `summaries[]` and `events[]` arrays. Parse this and synthesize a natural-language answer.

### Step 3: Create a Memory

Create `create_memory.json`:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "create_pieces_memory",
    "arguments": {
      "summary_description": "Agent + Pieces: Cloud Integration Setup",
      "summary": "# Cloud Integration Setup\n\n## What We Did\n- Verified Pieces MCP via ngrok tunnel\n- Configured mcp-remote bridge\n- Tested ask_pieces_ltm over the tunnel\n\n## Key Learnings\n- Use /mcp not /sse for cloud\n- File-based JSON for curl\n- String JSON-RPC IDs",
      "project": "Agent + Pieces"
    }
  },
  "id": "3"
}
```

Send (same session ID):
```bash
curl -i -X POST "https://abc123.ngrok-free.dev/model_context_protocol/2025-03-26/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: 1774202062499" \
  --data-binary @create_memory.json
```

### Session ID quick reference

| Stage | Header value | Source |
|---|---|---|
| Initialize request | Any string you choose (e.g., `init-001`) | You create it |
| Initialize response | 13-digit timestamp (e.g., `1774202062499`) | Extract from response header |
| All subsequent requests | The server-assigned value | Reuse the extracted value |

### Common mistakes

| Wrong | Correct |
|---|---|
| Inline JSON: `-d '{...}'` | File-based: `--data-binary @file.json` |
| Integer ID: `"id": 1` | String ID: `"id": "1"` |
| Missing `Accept` header | Include `Accept: application/json, text/event-stream` |
| Reusing initial session ID (`init-001`) | Use server-assigned session ID from initialize response |
| Looking for session ID in response body | Session ID is in the **response headers** |
| Calling tools before initialize | Always call `initialize` first |

---

## 6) Using mcp-remote (recommended for MCP clients)

For MCP clients that use stdio-based server configs (VS Code, Claude Desktop, Cursor, etc.), `mcp-remote` acts as a bridge -- it connects to the remote `/mcp` endpoint and exposes it as a local stdio server.

### Install

```bash
npm install -g mcp-remote@0.1.38
```

### Configure

Add to your client's MCP server config (location varies by client):

```json
{
  "mcpServers": {
    "pieces": {
      "command": "mcp-remote",
      "args": [
        "https://abc123.ngrok-free.dev/model_context_protocol/2025-03-26/mcp"
      ]
    }
  }
}
```

**Note:** No `/sse` here. This is the MCP-only configuration.

`mcp-remote` handles session management automatically -- you do not need to manually call `initialize` or track session IDs. Just use the Pieces tools through your client's normal MCP interface.

### Restart after config change

After editing the MCP config, restart your client or gateway so it picks up the Pieces server.

---

## 7) Tunnel options comparison

| Tunnel type | Example URL | Pros | Cons |
|---|---|---|---|
| ngrok (free) | `https://abc123.ngrok-free.dev` | Easiest setup | URL changes on restart |
| ngrok (paid) | `https://pieces.your-domain.ngrok-free.dev` | Stable URL | Paid |
| Cloudflare Tunnel | `https://random.trycloudflare.com` | Free, no signup for quick tunnels | Random URL |
| Custom proxy | `https://pieces.yourdomain.com` | Full control, stable URL | Requires domain + TLS setup |
| Pieces team tunnel | `https://user.tunnel.company.stream` | Pre-configured | May require Pieces team setup |

The MCP endpoint path is always the same regardless of tunnel type:
```
<tunnel-url>/model_context_protocol/2025-03-26/mcp
```

---

## 8) End-to-end setup checklist

1. [ ] PiecesOS is installed + running on the remote machine
2. [ ] LTM is enabled in the Pieces Desktop App
3. [ ] HTTPS tunnel is running and forwarding to `localhost:39300`
4. [ ] Sanity check passes: `curl -i "<tunnel-url>/model_context_protocol/2025-03-26/mcp"` returns HTTP 400 with session ID error
5. [ ] MCP client configured with the `/mcp` endpoint (via mcp-remote or direct)
6. [ ] `mcp-remote` installed if using the bridge approach
7. [ ] Client/gateway restarted after config change
8. [ ] Test: call `ask_pieces_ltm` with a simple question to verify end-to-end

---

## 9) Troubleshooting (cloud-specific)

See also `TROUBLESHOOTING.md` for general failure modes.

### 9.1 Sanity check returns 404/502/timeout
- Tunnel is down or PiecesOS is not running
- Ask the human to restart both
- If ngrok was restarted, get the new URL

### 9.2 Initialize returns HTTP 500
- Use file-based JSON (`--data-binary @file.json`)
- Use string IDs (`"id": "1"`)
- Include BOTH `Content-Type` and `Accept` headers
- If still failing, restart PiecesOS and the tunnel

### 9.3 Tools missing after mcp-remote config
- Confirm `mcp-remote` is installed: `mcp-remote --help`
- Confirm config uses `/mcp` not `/sse`
- Restart the gateway/client
- Test with direct curl to isolate: if curl works but mcp-remote doesn't, the issue is the bridge

### 9.4 ask_pieces_ltm times out over tunnel
- Tunnels add latency -- expect slower responses than LAN
- Narrow the query (add time window, topic filter)
- Test with direct curl to check if it's a tunnel issue vs a query issue
- Confirm the tunnel is still alive

### 9.5 Raw JSON responses
- This is correct behavior, not a bug
- Parse the JSON and synthesize a natural-language answer
- The `summaries[]` and `events[]` arrays contain structured data for the agent

### 9.6 Tunnel URL changed (ngrok restarted)
- Free-tier ngrok assigns a new URL on each restart
- Update the MCP config with the new URL
- Restart the client/gateway
- Consider paid ngrok (static domain) or a custom tunnel for stability
