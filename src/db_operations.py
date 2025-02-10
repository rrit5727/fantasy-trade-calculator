import pandas as pd
from sqlalchemy import create_engine, text
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Database connection parameters from the .env file
DB_PARAMS = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_DATABASE'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT')
}

# Define the columns we want to keep
COLUMNS_TO_KEEP = [
    'Round',
    'Player',
    'Team',
    'Age',
    'POS1',
    'POS2',
    'Price',
    'Priced at',
    'PTS',
    'Total base',
    'Base exceeds price premium'
]

def create_db_connection():
    """Create database connection"""
    return psycopg2.connect(**DB_PARAMS)

def get_column_definitions():
    """Generate SQL column definitions for desired columns"""
    column_types = {
        'Round': 'INTEGER',
        'Player': 'VARCHAR(100)',
        'Team': 'VARCHAR(50)',
        'Age': 'INTEGER',
        'POS1': 'VARCHAR(10)',
        'POS2': 'VARCHAR(10)',
        'Price': 'DECIMAL(10,2)',
        'Priced_at': 'DECIMAL(10,2)',
        'PTS': 'INTEGER',
        'Total_base': 'INTEGER',
        'Base_exceeds_price_premium': 'DECIMAL(10,2)'
    }
    
    columns = []
    for col in column_types.keys():
        columns.append(f'"{col}" {column_types[col]}')
    
    return columns

def create_table(conn):
    """Create the table with only the desired columns"""
    column_defs = get_column_definitions()
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
    
    # Select only the columns we want to keep
    df = df[COLUMNS_TO_KEEP]
    
    # Clean column names (replace spaces with underscores)
    df.columns = [col.strip().replace(' ', '_') for col in df.columns]
    
    # Create SQLAlchemy engine
    engine = create_engine(f'postgresql://{DB_PARAMS["user"]}:{DB_PARAMS["password"]}@{DB_PARAMS["host"]}:{DB_PARAMS["port"]}/{DB_PARAMS["database"]}')
    
    # Remove any $ signs and convert to numeric
    if 'Price' in df.columns:
        df['Price'] = df['Price'].replace('[\$,]', '', regex=True).astype(float)
    
    # Create table with matching columns
    conn = create_db_connection()
    create_table(conn)
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