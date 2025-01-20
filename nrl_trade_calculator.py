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
    total_base: int
    base_premium: int

def get_ranking_criteria() -> str:
    """Get user input for ranking criteria"""
    while True:
        print("\nSelect ranking criteria for trade suggestions:")
        print("1. Maximize Total Base")
        print("2. Maximize Base Premium")
        choice = input("Enter your choice (1 or 2): ")
        if choice in ['1', '2']:
            return choice
        print("Invalid choice. Please enter 1 or 2.")

def calculate_trade_options(
    data: pd.DataFrame,
    traded_out_players: List[str],
    ranking_criteria: str,
    max_options: int = 10
) -> List[Dict]:
    """
    Calculate possible trade combinations based on salary freed up from traded players.
    
    Args:
        data: DataFrame containing player data
        traded_out_players: List of player names to trade out
        ranking_criteria: '1' for Total Base or '2' for Base Premium
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
    
    # Filter available players by position needed
    available_players = data[
        ~data['Player'].isin(traded_out_players) & 
        (data['POS'].isin(positions_needed))
    ]
    
    # Generate all possible combinations of players by position
    valid_combinations = []
    
    # Get all possible position combinations that match what we need
    pos_combinations = list(combinations(positions_needed, len(positions_needed)))
    
    for pos_combo in pos_combinations:
        # Generate combinations of players
        for players in combinations(available_players.to_dict('records'), num_players_needed):
            # Check if combination matches required positions
            player_positions = [p['POS'] for p in players]
            if sorted(player_positions) != sorted(positions_needed):
                continue
                
            # Calculate totals
            total_price = sum(p['Price'] for p in players)
            total_base = sum(p['Total base'] for p in players)
            total_base_premium = sum(p['Base exceeds price premium'] for p in players)
            
            # Check if combination is within budget
            if total_price <= salary_freed:
                valid_combinations.append({
                    'players': [
                        {
                            'name': p['Player'],
                            'position': p['POS'],
                            'price': p['Price'],
                            'total_base': p['Total base'],
                            'base_premium': p['Base exceeds price premium']
                        } for p in players
                    ],
                    'total_price': total_price,
                    'total_base': total_base,
                    'total_base_premium': total_base_premium,
                    'salary_remaining': salary_freed - total_price
                })
    
    # Sort combinations based on selected criteria
    if ranking_criteria == '1':
        valid_combinations.sort(key=lambda x: x['total_base'], reverse=True)
    else:  # ranking_criteria == '2'
        valid_combinations.sort(key=lambda x: x['total_base_premium'], reverse=True)
    
    return valid_combinations[:max_options]

if __name__ == "__main__":
    try:
        # Read the CSV file
        data = pd.read_csv("NRL_stats.csv")
        print("Successfully loaded data with", len(data), "players")
        
        # Get ranking criteria from user
        ranking_criteria = get_ranking_criteria()
        
        # Example: Trading out Hughes and Grant
        traded_players = ["J. Hughes", "H. Grant"]
        
        print(f"\nCalculating trade options for trading out: {', '.join(traded_players)}")
        options = calculate_trade_options(data, traded_players, ranking_criteria)
        
        # Print results
        ranking_type = "Total Base" if ranking_criteria == '1' else "Base Premium"
        print(f"\nTop trade options ranked by {ranking_type}:")
        
        for i, option in enumerate(options, 1):
            print(f"\nOption {i}:")
            print("Players to trade in:")
            for player in option['players']:
                print(f"- {player['name']} ({player['position']})")
                print(f"  Price: ${player['price']:,}")
                print(f"  Total Base: {player['total_base']}")
                print(f"  Base Premium: {player['base_premium']}")
            print(f"Total Price: ${option['total_price']:,}")
            print(f"Combined Total Base: {option['total_base']}")
            print(f"Combined Base Premium: {option['total_base_premium']}")
            print(f"Salary Remaining: ${option['salary_remaining']:,}")
            
    except FileNotFoundError:
        print("Error: Could not find NRL_stats.csv in the current directory")
    except Exception as e:
        print("An error occurred:", str(e))