"""Domain modules, one per Pingen API domain.

Each module exposes ``TOOLS``: a mapping of tool name -> plain function whose
first parameter is a :class:`pingen_mcp_server.client.PingenClient`. The server
wraps these into MCP tools; tests call the functions directly with a fake
client. Tool names are the vendored spec's ``operationId`` with ``.``/``-``
replaced by ``_`` (see design.md decision 2).
"""

DOMAIN_MODULES = ("batches", "channels", "directory", "files", "letters", "webhooks")
