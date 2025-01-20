import pandas as pd
from typing import List, Dict
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
    consecutive_good_weeks: int

def load_data(file_path: str) -> pd.DataFrame:
    """
    Load data from a single file containing multiple rounds.
    
    Args:
        file_path: Path to CSV or Excel file with 'Round' column
    
    Returns:
        DataFrame containing data from all rounds
    """
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
        
    # Clean numeric columns with safe type conversion
    numeric_columns = ['Base exceeds price premium', 'Total base', 'Price']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = (df[col].astype(str)
                      .str.replace(',', '')
                      .str.replace(' ', '')
                      .str.replace('"', ''))
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Ensure Round column exists
    if 'Round' not in df.columns:
        raise ValueError("Data must contain a 'Round' column")
    
    return df

def get_rounds_data(df: pd.DataFrame) -> List[pd.DataFrame]:
    """
    Split consolidated data into list of DataFrames by round.
    
    Args:
        df: DataFrame containing all rounds with 'Round' column
    
    Returns:
        List of DataFrames, one per round
    """
    rounds = sorted(df['Round'].unique())
    return [df[df['Round'] == round_num].copy() for round_num in rounds]

def check_consistent_performance(
    player_name: str,
    consolidated_data: pd.DataFrame,
    min_base_premium: int = 5,
    required_consecutive_weeks: int = 2
) -> int:
    """
    Check how many consecutive weeks a player has maintained good performance.
    
    Args:
        player_name: Name of the player to check
        consolidated_data: DataFrame containing all rounds with 'Round' column
        min_base_premium: Minimum base premium required for "good" performance
        required_consecutive_weeks: Number of consecutive weeks required
        
    Returns:
        Number of consecutive weeks
    """
    player_data = consolidated_data[consolidated_data['Player'] == player_name].sort_values('Round')
    
    if player_data.empty:
        return 0
        
    consecutive_weeks = 0
    current_streak = 0
    
    for _, row in player_data.iterrows():
        if row['Base exceeds price premium'] >= min_base_premium:
            current_streak += 1
        else:
            current_streak = 0
            
        consecutive_weeks = max(consecutive_weeks, current_streak)
    
    return consecutive_weeks

def calculate_trade_options(
    consolidated_data: pd.DataFrame,
    traded_out_players: List[str],
    min_base_premium: int = 10,
    required_consecutive_weeks: int = 2,
    max_options: int = 10
) -> List[Dict]:
    """
    Calculate possible trade combinations based on consolidated data.
    
    Args:
        consolidated_data: DataFrame containing all rounds with 'Round' column
        traded_out_players: List of player names to trade out
        min_base_premium: Minimum base premium required for "good" performance
        required_consecutive_weeks: Number of consecutive weeks required
        max_options: Maximum number of trade combinations to return
    
    Returns:
        List of dictionaries containing possible trade combinations
    """
    # Use the most recent round for current prices and positions
    latest_round = consolidated_data['Round'].max()
    current_round_data = consolidated_data[consolidated_data['Round'] == latest_round].copy()
    
    # Calculate total salary freed up and get traded out players' info
    traded_players = current_round_data[current_round_data['Player'].isin(traded_out_players)]
    if traded_players.empty:
        print("\nError: None of the traded out players were found in the data")
        return []
        
    salary_freed = traded_players['Price'].sum()
    num_players_needed = len(traded_out_players)
    
    # Get all available players (excluding traded out players)
    available_players = current_round_data[~current_round_data['Player'].isin(traded_out_players)].copy()
    
    # Calculate consistency for each available player
    consistency_data = {
        player: check_consistent_performance(
            player, consolidated_data, min_base_premium, required_consecutive_weeks
        )
        for player in available_players['Player']
    }
    
    # Add consistency data
    available_players.loc[:, 'consecutive_good_weeks'] = available_players['Player'].map(consistency_data)
    
    # Filter out players who don't meet the consecutive weeks requirement
    available_players = available_players[
        available_players['consecutive_good_weeks'] >= required_consecutive_weeks
    ]
    
    print(f"\nPlayers meeting consistency requirement ({required_consecutive_weeks} weeks with {min_base_premium}+ base premium):")
    for _, player in available_players.iterrows():
        print(f"- {player['Player']} ({player['POS']}) - {player['consecutive_good_weeks']} consecutive weeks")
    
    if available_players.empty:
        return []
    
    # Generate trade combinations
    valid_combinations = []
    
    # Get all possible combinations of positions needed
    all_positions = traded_players['POS'].tolist()
    pos_combinations = list(combinations(all_positions, len(all_positions)))
    
    for pos_combo in pos_combinations:
        for players in combinations(available_players.to_dict('records'), num_players_needed):
            # Calculate totals
            total_price = sum(p['Price'] for p in players)
            total_base = sum(p['Total base'] for p in players)
            total_base_premium = sum(p['Base exceeds price premium'] for p in players)
            
            if total_price <= salary_freed:
                valid_combinations.append({
                    'players': [
                        {
                            'name': p['Player'],
                            'position': p['POS'],
                            'price': p['Price'],
                            'total_base': p['Total base'],
                            'base_premium': p['Base exceeds price premium'],
                            'consecutive_good_weeks': p['consecutive_good_weeks']
                        } for p in players
                    ],
                    'total_price': total_price,
                    'total_base': total_base,
                    'total_base_premium': total_base_premium,
                    'salary_remaining': salary_freed - total_price
                })
    
    # Sort combinations by total base premium
    valid_combinations.sort(key=lambda x: x['total_base_premium'], reverse=True)
    
    return valid_combinations[:max_options]

if __name__ == "__main__":
    try:
        # Example file path - modify according to your setup
        file_path = "NRL_stats.xlsx"
        
        # Load consolidated data
        consolidated_data = load_data(file_path)
        print(f"Successfully loaded data for {consolidated_data['Round'].nunique()} rounds")
        
        # Example: Trading out Hughes and Grant
        traded_players = ["J. Hughes", "H. Grant"]
        
        print(f"\nCalculating trade options for trading out: {', '.join(traded_players)}")
        
        options = calculate_trade_options(
            consolidated_data,
            traded_players,
            min_base_premium=5,
            required_consecutive_weeks=3  # Changed to 1 for testing with limited rounds
        )
        
        if options:
            # Print results
            for i, option in enumerate(options, 1):
                print(f"\nOption {i}:")
                print("Players to trade in:") 
                for player in option['players']:
                    print(f"- {player['name']} ({player['position']})")
                    print(f"  Price: ${player['price']:,}")
                    print(f"  Current Base Premium: {player['base_premium']}")
                    print(f"  Consecutive Weeks above threshold: {player['consecutive_good_weeks']}")
                print(f"Total Price: ${option['total_price']:,}")
                print(f"Combined Base Premium: {option['total_base_premium']}")
                print(f"Salary Remaining: ${option['salary_remaining']:,}")
            
    except FileNotFoundError:
        print("Error: Could not find data file in the current directory")
    except ValueError as e:
        print("Error:", str(e))
    except Exception as e:
        print("An error occurred:", str(e))