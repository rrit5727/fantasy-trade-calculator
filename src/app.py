from flask import Flask, render_template, request, jsonify
from nrl_trade_calculator import calculate_trade_options, load_data, assign_priority_level
from typing import List, Dict, Any
import traceback
import pandas as pd

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

def simulate_rule_levels(consolidated_data: pd.DataFrame, rounds: List[int]) -> None:
    player_name = consolidated_data['Player'].unique()[0]  # Assuming the first player in the data

    # Rule descriptions
    rule_descriptions = {
        1: "BPRE >= 14 for last 3 weeks",
        2: "BPRE >= 21 for last 2 weeks",
        3: "2 week Average BPRE >= 26",
        4: "BPRE >= 12 for last 3 weeks",
        5: "BPRE >= 19 for last 2 weeks",
        6: "2 week Average BPRE >= 24",
        7: "BPRE >= 10 for last 3 weeks",
        8: "BPRE >= 17 for last 2 weeks",
        9: "2 week Average BPRE >= 22",
        10: "BPRE >= 8 for last 3 weeks",
        11: "BPRE >= 15 for last 2 weeks",
        12: "2 week Average BPRE >= 20",
        13: "BPRE >= 6 for last 3 weeks",
        14: "BPRE >= 13 for last 2 weeks",
        15: "2 week Average BPRE >= 18",
        16: "BPRE >= 10 for last 2 weeks",
        17: "2 week Average BPRE >= 15",
        18: "BPRE >= 8 for last 2 weeks",
        19: "2 week Average BPRE >= 13",
        20: "BPRE >= 6 for last 2 weeks",
        21: "2 week Average BPRE >= 11",
        22: "BPRE >= 2 for last 3 weeks",
        23: "BPRE >= 4 for last 2 weeks",
        24: "2 week Average BPRE >= 9",
        25: "No rules satisfied"
    }

    for round_num in rounds:
        # Get the last 4 rounds up to the current round
        recent_rounds = sorted(consolidated_data['Round'].unique())
        recent_rounds = [r for r in recent_rounds if r <= round_num][-4:]
        cumulative_data = consolidated_data[consolidated_data['Round'].isin(recent_rounds)]
        player_data = cumulative_data[cumulative_data['Player'] == player_name]
        
        if player_data.empty:
            print(f"Round {round_num}: No data for player {player_name}")
            continue
        
        priority_level = assign_priority_level(player_data.iloc[-1], cumulative_data)
        rule_description = rule_descriptions.get(priority_level, "Unknown rule")
        print(f"Rule levels passed as at round {round_num}: Rule Level Satisfied: {priority_level} - {rule_description}")

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # Get data from the form
        player1 = request.form['player1']
        player2 = request.form['player2']
        strategy = request.form['strategy']
        trade_type = request.form['tradeType']
        allowed_positions = request.form.getlist('positions') if trade_type == 'positionalSwap' else []

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
            allowed_positions=allowed_positions,
            trade_type=trade_type
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
    try:
        # Prompt user for action
        while True:
            choice = input("\nDo you want to:\n1. Run the ordinary trade calculator\n2. Run rule set simulation for 1 player\nEnter 1 or 2: ")
            if choice in ['1', '2']:
                break
            print("Invalid input. Please enter 1 or 2.")

        # Load the appropriate data file based on user choice
        file_path = "NRL_stats.xlsx" if choice == '1' else "player_simulation.xlsx"
        consolidated_data = load_data(file_path)
        print(f"Successfully loaded data for {consolidated_data['Round'].nunique()} rounds")

        if choice == '2':
            rounds = list(range(1, int(consolidated_data['Round'].max()) + 1))  # Simulate for all rounds
            simulate_rule_levels(consolidated_data, rounds)
        else:
            # Run the ordinary trade calculator
            app.run(debug=True)

    except FileNotFoundError:
        print("Error: Could not find data file in the current directory")
    except ValueError as e:
        print("Error:", str(e))
    except Exception as e:
        print("An error occurred:", str(e))