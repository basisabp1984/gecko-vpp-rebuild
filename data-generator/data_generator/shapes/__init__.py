"""Shape generators — one module per data domain.

Each module exposes an ``async def generate(conn, ...) -> int`` function
returning the count of rows inserted.
"""
