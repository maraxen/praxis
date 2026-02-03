# Praxis Development Commands

# Generate the browser-mode SQLite database using pre-discovered backends and protocols
generate-db:
	uv run --with pylibftdi scripts/generate_browser_db.py
