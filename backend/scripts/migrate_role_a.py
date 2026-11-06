from app.db import engine
from app.migration import migrate

if __name__ == '__main__':
    with engine.begin() as connection: migrate(connection)
    print('Schema upgrade completed. Existing revisions, approvals and documents retained.')
