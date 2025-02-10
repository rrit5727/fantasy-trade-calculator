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
import traceback
from datetime import datetime
from sqlalchemy import text

# Load environment variables from .env file
load_dotenv() 

# Initialize database outside of create_app to make it globally available
db = SQLAlchemy()
cache = Cache()

def create_app():
    app = Flask(__name__)
    print("Flask app initialized")

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://')  # Heroku fix
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configure caching
    cache_config = {
        'CACHE_TYPE': 'RedisCache' if 'REDIS_URL' in os.environ else 'SimpleCache',
        'CACHE_REDIS_URL': os.environ.get('REDIS_URL'),
        'CACHE_DEFAULT_TIMEOUT': 300
    }
    
    # Initialize extensions
    db.init_app(app)
    cache.init_app(app, config=cache_config)

    # Define models
    class Player(db.Model):
        __tablename__ = 'players'
        id = db.Column(db.Integer, primary_key=True)
        Player = db.Column(db.String(80))
        Team = db.Column(db.String(50))
        POS1 = db.Column(db.String(50))
        Price = db.Column(db.Integer)
        Total_base = db.Column(db.Integer)
        Base_exceeds_price_premium = db.Column(db.Integer)
        consecutive_good_weeks = db.Column(db.Integer)
        avg_bpre = db.Column(db.Float)
        avg_base = db.Column(db.Float)
        priority_level = db.Column(db.Integer)
        Round = db.Column(db.Integer)
        Age = db.Column(db.Integer)

    def initialize_data():
        with app.app_context():
            db.create_all()
            
            if not Player.query.first():
                # Only load if database is empty
                file_path = os.path.join(app.root_path, 'NRL_stats.xlsx')
                
                if os.path.exists(file_path):
                    df = pd.read_excel(file_path)
                    print(f"Loaded DataFrame columns: {df.columns.tolist()}")
                    df = precompute_player_stats(df)
                    
                    # Batch insert
                    chunks = [df[i:i+1000] for i in range(0, df.shape[0], 1000)]
                    for chunk in chunks:
                        print(f"Inserting {len(chunk)} records")
                        db.session.bulk_insert_mappings(Player, chunk.to_dict(orient='records'))
                    
                    db.session.commit()
                    print("Commit successful.")
                    app.logger.info(f"Loaded {len(df)} players into database")
                else:
                    app.logger.warning("No Excel file found - using existing database")
            
            # Log the first 5 players in the database
            first_five_players = Player.query.limit(5).all()
            for player in first_five_players:
                print(f"Player: {player.Player}, Team: {player.Team}, Price: {player.Price}")

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/calculate', methods=['POST'])
    @cache.memoize(60)
    def calculate():
        try:
            # Extract form data with debug logging
            player1 = request.form['player1']
            player2 = request.form.get('player2', '')
            print(f"Received player names: player1='{player1}', player2='{player2}'")
            
            # Debug logging for database content
            sample_players = Player.query.limit(5).all()
            print("Sample players in database:", [p.Player for p in sample_players])
            
            strategy = request.form['strategy']
            trade_type = request.form['tradeType']
            allowed_positions = request.form.getlist('positions')
            apply_lockout = 'applyLockout' in request.form
            simulate_datetime = request.form.get('simulateDateTime')

            # Get current round
            max_round = db.session.query(db.func.max(Player.Round)).scalar()
            
            # Convert database query to DataFrame for comparison
            traded_out = [p for p in [player1, player2] if p]
            print(f"Looking up players in database: {traded_out}")
            
            # Debug the actual database query
            player_data = Player.query.filter(
                Player.Player.in_(traded_out),
                Player.Round == max_round
            ).all()
            print(f"Found players in database: {[p.Player for p in player_data]}")
            missing_players = []
            for player_name in traded_out:
                # Get the latest entry for each player, regardless of round
                player = Player.query.filter_by(Player=player_name)\
                                    .order_by(Player.Round.desc())\
                                    .first()
                if player:
                    player_data.append(player)
                else:
                    missing_players.append(player_name)

            if missing_players:
                return jsonify({
                    'error': f"Players not found in database: {', '.join(missing_players)}"
                }), 404

            # Calculate salary freed
            salary_freed = sum(p.Price for p in player_data)

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
                'price': player.Price
            } for player in first_five_players]

            # Apply lockout if enabled
            if apply_lockout and simulate_datetime:
                locked_teams = get_locked_teams(simulate_datetime)
                query = query.filter(~Player.Team.in_(locked_teams))

            # Filter by allowed positions if specified
            if allowed_positions:
                query = query.filter(Player.POS1.in_(allowed_positions))

            # Convert to DataFrame with correct column names
            players = query.all()
            df = pd.DataFrame([{
                'Player': p.Player,
                'Team': p.Team,
                'POS1': p.POS1,
                'Price': p.Price,
                'Total_base': p.Total_base,
                'Base_exceeds_price_premium': p.Base_exceeds_price_premium,
                'consecutive_good_weeks': p.consecutive_good_weeks,
                'avg_bpre': p.avg_bpre,
                'avg_base': p.avg_base,
                'priority_level': p.priority_level,
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
                apply_lockout=apply_lockout
            )

            return jsonify({
                'options': options[:10],
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
                'price': player.Price
            } for player in first_five_players]
            
            return jsonify({'players': first_five_players_data}), 200
        except Exception as e:
            app.logger.error(f"Error fetching first players: {str(e)}")
            return jsonify({'error': 'Failed to fetch players'}), 500

    @app.route('/get_player_price', methods=['POST'])
    def get_player_price():
        player_name = request.form.get('player_name')
        player = Player.query.filter_by(Player=player_name).first()
        
        if player:
            return jsonify({'price': player.Price}), 200
        else:
            return jsonify({'error': 'Player not found'}), 404

    # Helper functions
    def get_locked_teams(simulate_datetime):
        # Implement your lockout logic using SQL queries
        locked_teams = []  # Your existing logic here
        return locked_teams

    # Initialize data when the app is created
    with app.app_context():
        initialize_data()

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port, debug=False)