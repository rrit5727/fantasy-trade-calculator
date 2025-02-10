import os
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from dotenv import load_dotenv
from nrl_trade_calculator import (
    calculate_trade_options, 
    assign_priority_level, 
    is_player_locked,
    precompute_player_stats
)
import pandas as pd
from db_operations import import_excel_data, create_db_connection
import traceback
from sqlalchemy import text
from typing import Dict, Any

load_dotenv()

app = Flask(__name__)
db = SQLAlchemy()
cache = Cache()

# Cache configuration
cache_config = {
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
}

# Initialize extensions
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///nrl_stats.db')
db.init_app(app)
cache.init_app(app, config=cache_config)

# Define models at global scope
class Player(db.Model):
    __tablename__ = 'player_stats'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Add autoincrement
    Player = db.Column(db.String(100))
    Team = db.Column(db.String(50))
    POS1 = db.Column(db.String(10))
    POS2 = db.Column(db.String(10))  # Add this line
    Price = db.Column(db.Numeric(10,2))
    Total_base = db.Column(db.Integer)
    Base_exceeds_price_premium = db.Column(db.Numeric(10,2))
    Round = db.Column(db.Integer)
    Age = db.Column(db.Integer)

def get_player_stats_df():
    """
    Retrieve player stats from database and return as DataFrame
    """
    with app.app_context():
        players = Player.query.all()
        data = [{
            'Player': p.Player,
            'Team': p.Team,
            'POS1': p.POS1,
            'Price': float(p.Price),
            'Total_base': p.Total_base,
            'Base_exceeds_price_premium': float(p.Base_exceeds_price_premium),
            'Round': p.Round,
            'Age': p.Age
        } for p in players]
        return pd.DataFrame(data)

def prepare_trade_option(option: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare trade option data for JSON response, ensuring all required fields exist
    and are properly formatted.
    """
    prepared_option = {
        'players': [],
        'total_price': int(option.get('total_price', 0)),
        'salary_remaining': int(option.get('salary_remaining', 0)),
        'total_base': float(option.get('total_base', 0)),
        'total_base_premium': float(option.get('total_base_premium', 0)),
        'total_avg_base': float(option.get('total_avg_base', 0)) if 'total_avg_base' in option else 0.0,
        'combo_avg_bpre': float(option.get('combo_avg_bpre', 0)) if 'combo_avg_bpre' in option else 0.0
    }
    return prepared_option

def initialize_database():
    """Initialize database by importing Excel data."""
    try:
        with app.app_context():
            # Drop all existing tables and create new ones
            db.drop_all()
            db.create_all()
            
            # Create a new connection
            conn = create_db_connection()
            
            # Import the Excel data using the existing function from db_operations
            import_excel_data('NRL_stats.xlsx')
            
            # Close the connection
            conn.close()
            
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

# Initialize database when starting the app
initialize_database()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check_player_lockout', methods=['POST'])
def check_player_lockout():
    try:
        player_name = request.form['player_name']
        simulate_datetime = request.form.get('simulateDateTime')
        
        # Load data from database
        consolidated_data = get_player_stats_df()
        
        is_locked = is_player_locked(player_name, consolidated_data, simulate_datetime)
        
        return jsonify({
            'is_locked': is_locked
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        player1 = request.form['player1']
        player2 = request.form.get('player2')
        strategy = request.form['strategy']
        trade_type = request.form['tradeType']
        allowed_positions = request.form.getlist('positions')
        apply_lockout = 'applyLockout' in request.form
        simulate_datetime = request.form.get('simulateDateTime')

        # Load data from database
        consolidated_data = get_player_stats_df()

        traded_out = [player1]
        if player2:
            traded_out.append(player2)

        # Get player data for salary calculation
        player_data = []
        for player_name in traded_out:
            player = Player.query.filter_by(Player=player_name).first()
            if player:
                player_data.append(player)

        # Calculate salary freed
        salary_freed = sum(float(p.Price) for p in player_data)

        # Get available players
        max_round = db.session.query(db.func.max(Player.Round)).scalar()
        query = Player.query.filter(
            Player.Round == max_round,
            ~Player.Player.in_(traded_out)
        )

        # Fetch the first 5 players for debugging
        first_five_players = Player.query.limit(5).all()
        first_five_players_data = [{
            'name': player.Player,
            'team': player.Team,
            'price': float(player.Price)
        } for player in first_five_players]

        # Filter by allowed positions if specified
        if allowed_positions:
            query = query.filter(Player.POS1.in_(allowed_positions))

        # Convert to DataFrame with correct column names
        players = query.all()
        df = pd.DataFrame([{
            'Player': p.Player,
            'Team': p.Team,
            'POS1': p.POS1,
            'Price': float(p.Price),
            'Total_base': p.Total_base,
            'Base_exceeds_price_premium': float(p.Base_exceeds_price_premium),
            'Round': p.Round,
            'Age': p.Age
        } for p in players])

        # Rename columns to match what calculate_trade_options expects
        df = df.rename(columns={
            'Base_exceeds_price_premium': 'Base exceeds price premium'
        })

        # Calculate trade options
        options = calculate_trade_options(
            consolidated_data=df,
            traded_out_players=traded_out,
            maximize_base=(strategy == '2'),
            hybrid_approach=(strategy == '3'),
            allowed_positions=allowed_positions,
            trade_type=trade_type,
            simulate_datetime=simulate_datetime,
            apply_lockout=apply_lockout,
            salary_freed=salary_freed
        )

        # Prepare options for JSON response
        prepared_options = [prepare_trade_option(option) for option in options[:10]]

        return jsonify({
            'options': prepared_options,
            'first_five_players': first_five_players_data
        })

    except Exception as e:
        app.logger.error(f"Calculation error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/check_db_connection', methods=['GET'])
def check_db_connection():
    try:
        # Attempt to execute a simple query
        db.session.execute(text('SELECT 1'))
        return jsonify({'message': 'Database connection is successful!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/first_players', methods=['GET'])
def first_players():
    try:
        first_five_players = Player.query.limit(5).all()
        first_five_players_data = [{
            'name': player.Player,
            'team': player.Team,
            'price': float(player.Price)
        } for player in first_five_players]
        
        return jsonify({'players': first_five_players_data}), 200
    except Exception as e:
        app.logger.error(f"Error fetching first players: {str(e)}")
        return jsonify({'error': 'Failed to fetch players'}), 500

@app.route('/get_player_price', methods=['POST'])
def get_player_price():
    try:
        player_name = request.form.get('player_name')
        player = Player.query.filter_by(Player=player_name).first()
        
        if player:
            return jsonify({'price': float(player.Price)}), 200
        else:
            return jsonify({'error': 'Player not found'}), 404
    except Exception as e:
        app.logger.error(f"Error getting player price: {str(e)}")
        return jsonify({'error': 'Failed to get player price'}), 500

@app.route('/players', methods=['GET'])
def get_players():
    try:
        # Load data from database
        consolidated_data = get_player_stats_df()
        player_names = consolidated_data['Player'].unique().tolist()
        return jsonify(player_names)
    except Exception as e:
        app.logger.error(f"Error getting players: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)