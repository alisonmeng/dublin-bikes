from sqlalchemy import text

from db_engine import build_engine

engine = build_engine(echo=True)

with engine.connect() as conn:
    with conn.begin():
        sql_station = '''
        CREATE TABLE IF NOT EXISTS station (
            `number` INTEGER NOT NULL,
            contract_name VARCHAR(128),
            `name` VARCHAR(128),
            address VARCHAR(128),
            bike_stands INTEGER,
            lat FLOAT,
            lng FLOAT,
            banking BOOLEAN,
            bonus BOOLEAN,
            PRIMARY KEY (`number`)
        ) ENGINE=InnoDB;
        '''
        conn.execute(text(sql_station))

    sql_availability = """
    CREATE TABLE IF NOT EXISTS availability (
        `number` INTEGER NOT NULL,
        available_bike_stands INTEGER,
        available_bikes INTEGER,
        status VARCHAR(128),
        last_update BIGINT NOT NULL,
        PRIMARY KEY (`number`, last_update)
    );
    """
    conn.execute(text(sql_availability))
    print("Station and Availability create table successfully")