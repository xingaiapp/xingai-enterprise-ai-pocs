# Keys

`private.pem` and `public.pem` are generated locally, never committed (see `.gitignore`).

```bash
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
chmod 600 keys/private.pem
chmod 644 keys/public.pem
```

The Authorization Server (`auth_server/`) holds `private.pem` — it never leaves that process. The Claims MCP Server (`mcp_server/`) only ever needs `public.pem`, fetched at runtime via `GET /jwks.json` from the Authorization Server (or, in the Docker Compose setup, mounted read-only into its own container) — it should never receive the private key at all.
