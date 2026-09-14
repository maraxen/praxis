"""training/ package bootstrap for pytest.

floor_gen lives at training/floor_gen/ (task-mandated path) while the
parallel P2.1 owner's pyproject.toml uses a src/ layout. This empty
rootdir conftest puts training/ itself on sys.path so `import floor_gen`
works regardless of how the member is eventually packaged. Import arrow
stays legal per F2-rev2: floor_gen imports coxswain.plr.*, never reverse.
"""
