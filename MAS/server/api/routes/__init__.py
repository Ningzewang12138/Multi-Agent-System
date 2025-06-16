# This file makes the routes directory a Python package

from . import chat, knowledge, system, sync, admin, web_admin, mcp, messages

__all__ = ['chat', 'knowledge', 'system', 'sync', 'admin', 'web_admin', 'mcp', 'messages']
