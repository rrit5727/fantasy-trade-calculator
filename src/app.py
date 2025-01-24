from flask import Flask, render_template, request, jsonify
from nrl_trade_calculator import calculate_trade_options, load_data
from typing import List, Dict, Any
import traceback

app = Flask(__name__)

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

    for player in option.get('players', []):
        prepared_player = {
            'name': player.get('name', ''),
            'position': player.get('position', ''),
            'price': int(player.get('price', 0)),
            'total_base': float(player.get('total_base', 0)),
            'base_premium': int(float(player.get('base_premium', 0))),
            'consecutive_good_weeks': int(player.get('consecutive_good_weeks', 0)),
            'avg_base': float(player.get('avg_base', 0)) if 'avg_base' in player else 0.0
        }
        
        # Only include priority_level if it exists
        if 'priority_level' in player:
            prepared_player['priority_level'] = int(player['priority_level'])
            
        prepared_option['players'].append(prepared_player)

    return prepared_option

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # Get data from the form
        player1 = request.form['player1']
        player2 = request.form['player2']
        strategy = request.form['strategy']
        trade_type = request.form['tradeType']
        allowed_positions = request.form.getlist('positions') if trade_type == 'positionalSwap' else []  # Get selected positions only for positional swap

        # Load consolidated data
        file_path = "NRL_stats.xlsx"
        consolidated_data = load_data(file_path)

        # Determine optimization strategy
        maximize_base = (strategy == '2')
        hybrid_approach = (strategy == '3')

        # Calculate trade options
        options = calculate_trade_options(
            consolidated_data=consolidated_data,
            traded_out_players=[player1, player2],
            maximize_base=maximize_base,
            hybrid_approach=hybrid_approach,
            max_options=10,
            allowed_positions=allowed_positions,  # Pass the allowed positions
            trade_type=trade_type  # Pass the trade type
        )

        # Prepare options for JSON response
        prepared_options = [prepare_trade_option(option) for option in options]

        return jsonify(prepared_options)

    except Exception as e:
        # Log the full error traceback for debugging
        error_traceback = traceback.format_exc()
        print(f"Error occurred: {error_traceback}")
        
        return jsonify({
            'error': f'An error occurred while calculating trade options: {str(e)}'
        }), 500

@app.route('/players', methods=['GET'])
def get_players():
    try:
        # Load consolidated data
        file_path = "NRL_stats.xlsx"
        consolidated_data = load_data(file_path)
        
        # Extract unique player names
        player_names = consolidated_data['Player'].unique().tolist()
        
        return jsonify(player_names)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)