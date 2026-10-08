"""Repositories: thin data-access objects over a SQLAlchemy Session.

Repositories receive an injected Session and may query/add/flush, but never
commit. Transaction boundaries are owned by the future service/use-case layer
(see app/db/session.py and the M1-03 transaction-ownership decision).
"""
