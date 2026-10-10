import urllib.request
import json

packages = [
    'SQLAlchemy', 'GeoAlchemy2', 'asyncpg', 'psycopg', 'psycopg-binary', 
    'shapely', 'fastapi', 'pydantic', 'alembic', 'uvicorn', 'pyproj', 'geopandas'
]

for pkg in packages:
    try:
        url = f'https://pypi.org/pypi/{pkg}/json'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"{pkg}=={data['info']['version']}")
    except Exception as e:
        print(f"{pkg}: error {e}")
