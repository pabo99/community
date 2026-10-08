"""Service / use-case layer.

Services own transaction boundaries: they coordinate repositories and commit
once per unit of work. Repositories themselves never commit.
"""
