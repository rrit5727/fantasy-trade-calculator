import pandas as pd
from typing import List, Dict, Tuple
from dataclasses import dataclass
from itertools import combinations

@dataclass
class Player:
    name: str
    price: int
    position: str
    points: int
    avg: float

def calculate_trade_options(
    data: pd.DataFrame,
    traded_out_players: List[str],
    max_options: int = 10
) -> List[Dict]:
    """
    Calculate possible trade combinations based on salary freed up from traded players.
    Suggests the same number of players to trade in as were traded out.
    
    Args:
        data: DataFrame containing player data
        traded_out_players: List of player names to trade out
        max_options: Maximum number of trade combinations to return
    
    Returns:
        List of dictionaries containing possible trade combinations
    """
    # Clean price data and convert to integers
    data['Price'] = data['Price'].str.replace(',', '').str.replace(' ', '').str.replace('"', '').astype(int)
    
    # Calculate total salary freed up and get traded out players' info
    traded_players = data[data['Player'].isin(traded_out_players)]
    salary_freed = traded_players['Price'].sum()
    positions_needed = traded_players['POS'].tolist()
    num_players_needed = len(traded_out_players)
    
    # Filter available players by position needed and price
    available_players = data[
        ~data['Player'].isin(traded_out_players) & 
        (data['POS'].isin(positions_needed))
    ]
    
    # Generate all possible combinations of players by position
    valid_combinations = []
    
    # Get all possible position combinations that match what we need
    pos_combinations = list(combinations(positions_needed, len(positions_needed)))
    
    for pos_combo in pos_combinations:
        # Get potential players for each position
        players_by_position = []
        for pos in pos_combo:
            pos_players = available_players[
                (available_players['POS'] == pos) & 
                (available_players['Price'] <= salary_freed)
            ].to_dict('records')
            players_by_position.append(pos_players)
        
        # Generate combinations of players
        for players in combinations(available_players.to_dict('records'), num_players_needed):
            # Check if combination matches required positions
            player_positions = [p['POS'] for p in players]
            if sorted(player_positions) != sorted(positions_needed):
                continue
                
            # Calculate total price and average points
            total_price = sum(p['Price'] for p in players)
            total_avg_points = sum(p['AVG'] for p in players)
            
            # Check if combination is within budget
            if total_price <= salary_freed:
                valid_combinations.append({
                    'players': [
                        {
                            'name': p['Player'],
                            'position': p['POS'],
                            'price': p['Price'],
                            'avg_points': p['AVG']
                        } for p in players
                    ],
                    'total_price': total_price,
                    'total_avg_points': total_avg_points,
                    'salary_remaining': salary_freed - total_price
                })
    
    # Sort combinations by total average points
    valid_combinations.sort(key=lambda x: x['total_avg_points'], reverse=True)
    
    return valid_combinations[:max_options]

if __name__ == "__main__":
    # Read the CSV file
    try:
        data = pd.read_csv("NRL_stats.csv")
        print("Successfully loaded data with", len(data), "players")
        
        # Example: Trading out Hughes and Grant
        traded_players = ["J. Hughes", "H. Grant"]
        
        print(f"\nCalculating trade options for trading out: {', '.join(traded_players)}")
        options = calculate_trade_options(data, traded_players)
        
        # Print results
        for i, option in enumerate(options, 1):
            print(f"\nOption {i}:")
            print("Players to trade in:")
            for player in option['players']:
                print(f"- {player['name']} ({player['position']})")
                print(f"  Price: ${player['price']:,}")
                print(f"  Average Points: {player['avg_points']:.1f}")
            print(f"Total Price: ${option['total_price']:,}")
            print(f"Total Average Points: {option['total_avg_points']:.1f}")
            print(f"Salary Remaining: ${option['salary_remaining']:,}")
            
    except FileNotFoundError:
        print("Error: Could not find NRL_stats.csv in the current directory")
    except Exception as e:
        print("An error occurred:", str(e))