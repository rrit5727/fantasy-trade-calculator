import pandas as pd
from sqlalchemy import create_engine, text
import psycopg2
from datetime import datetime

# Database connection parameters
DB_PARAMS = {
    'host': 'localhost',
    'database': 'NRL_FANTASY_TRADE_CALC',
    'user': 'postgres',
    'password': '8wriebsA',
    'port': '5433'
}

def create_db_connection():
    """Create database connection"""
    return psycopg2.connect(**DB_PARAMS)

def get_column_definitions(df):
    """Generate SQL column definitions based on DataFrame columns"""
    column_types = {
        'Round': 'INTEGER',
        'Player': 'VARCHAR(100)',
        'Team': 'VARCHAR(50)',
        'Age': 'INTEGER',
        'POS1': 'VARCHAR(10)',
        'POS2': 'VARCHAR(10)',
        'Price': 'DECIMAL(10,2)',
        'Priced at': 'DECIMAL(10,2)',
        'PTS': 'INTEGER',
        'AVG': 'DECIMAL(10,2)',
        'MP': 'INTEGER',
        'T': 'INTEGER',
        'TS': 'INTEGER',
        'G': 'INTEGER',
        'FG': 'INTEGER',
        'TA': 'INTEGER',
        'LB': 'INTEGER',
        'LBA': 'INTEGER',
        'TCK': 'INTEGER',
        'TB': 'INTEGER',
        'MT': 'INTEGER',
        'OFG': 'INTEGER',
        'OFH': 'INTEGER',
        'ER': 'INTEGER',
        'TO': 'INTEGER',
        'FTF': 'INTEGER',
        'MG': 'INTEGER',
        'KM': 'INTEGER',
        'KD': 'INTEGER',
        'Total base': 'INTEGER',
        'Base exceeds price premium': 'DECIMAL(10,2)'
    }
    
    # Default type for any column not explicitly defined
    default_type = 'VARCHAR(100)'
    
    columns = []
    for col in df.columns:
        clean_col = col.strip().replace(' ', '_')  # Replace spaces with underscores
        col_type = column_types.get(col, default_type)
        columns.append(f'"{clean_col}" {col_type}')
    
    return columns

def create_table(conn, df):
    """Create the table with columns matching the DataFrame"""
    column_defs = get_column_definitions(df)
    create_table_sql = f"""
    DROP TABLE IF EXISTS player_stats;
    CREATE TABLE player_stats (
        id SERIAL PRIMARY KEY,
        {','.join(column_defs)}
    );
    """
    
    with conn.cursor() as cur:
        cur.execute(create_table_sql)
    conn.commit()

def import_excel_data(excel_file_path):
    """Import data from Excel to PostgreSQL"""
    # Read Excel file
    df = pd.read_excel(excel_file_path)
    
    # Clean column names (replace spaces with underscores)
    df.columns = [col.strip().replace(' ', '_') for col in df.columns]
    
    # Create SQLAlchemy engine
    engine = create_engine(f'postgresql://{DB_PARAMS["user"]}:{DB_PARAMS["password"]}@{DB_PARAMS["host"]}:{DB_PARAMS["port"]}/{DB_PARAMS["database"]}')
    
    # Remove any $ signs and convert to numeric
    if 'Price' in df.columns:
        df['Price'] = df['Price'].replace('[\$,]', '', regex=True).astype(float)
    
    # Create table with matching columns
    conn = create_db_connection()
    create_table(conn, df)
    conn.close()
    
    # Import data
    df.to_sql('player_stats', engine, if_exists='replace', index=False)

def main():
    try:
        # Import data
        import_excel_data('NRL_stats.xlsx')
        print("Data import completed successfully!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()