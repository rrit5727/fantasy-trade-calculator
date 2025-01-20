import pandas as pd
from typing import List, Dict, Tuple
from dataclasses import dataclass

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
    
    Args:
        data: DataFrame containing player data
        traded_out_players: List of player names to trade out
        max_options: Maximum number of trade combinations to return
    
    Returns:
        List of dictionaries containing possible trade combinations
    """
    # Clean price data and convert to integers
    data['Price'] = data['Price'].str.replace(',', '').str.replace(' ', '').str.replace('"', '').astype(int)
    
    # Calculate total salary freed up
    traded_players = data[data['Player'].isin(traded_out_players)]
    salary_freed = traded_players['Price'].sum()
    
    # Get positions needed to fill
    positions_needed = traded_players['POS'].tolist()
    
    # Filter available players
    available_players = data[
        ~data['Player'].isin(traded_out_players) & 
        (data['Price'] <= salary_freed)
    ]
    
    trade_options = []
    
    # Generate combinations for each position
    for pos in positions_needed:
        pos_options = available_players[
            (available_players['POS'] == pos) & 
            (available_players['Price'] <= salary_freed)
        ].sort_values('AVG', ascending=False)
        
        # Take top performing players within budget
        for _, player in pos_options.head(max_options).iterrows():
            trade_options.append({
                'position': pos,
                'player': player['Player'],
                'price': player['Price'],
                'avg_points': player['AVG'],
                'salary_remaining': salary_freed - player['Price']
            })
    
    # Sort options by average points
    trade_options.sort(key=lambda x: x['avg_points'], reverse=True)
    
    return trade_options[:max_options]

# # Example usage
# if __name__ == "__main__":
#     # Sample data (using the provided CSV)
#     data = pd.read_csv("NRL_stats.csv")
    
#     # Example: Trading out Hughes and Grant
#     traded_players = ["J. Hughes", "H. Grant"]
    
#     options = calculate_trade_options(data, traded_players)
    
#     # Print results
#     print(f"\nPossible trade options when trading out {', '.join(traded_players)}:")
#     for i, option in enumerate(options, 1):
#         print(f"\nOption {i}:")
#         print(f"Player: {option['player']}")
#         print(f"Position: {option['position']}")
#         print(f"Price: ${option['price']:,}")
#         print(f"Average Points: {option['avg_points']:.1f}")
#         print(f"Salary Remaining: ${option['salary_remaining']:,}")

if __name__ == "__main__":
    # Read the CSV file
    try:
        data = pd.read_csv("NRL_stats.csv")
        print("Successfully loaded data with", len(data), "players")

         # Print column names to verify them
        print("Column names in the dataset:", data.columns)
        
        # Example: Let's try trading out Hughes and Grant
        traded_players = ["J. Hughes", "H. Grant"]
        
        print(f"\nCalculating trade options for trading out: {', '.join(traded_players)}")
        options = calculate_trade_options(data, traded_players)
        
        # Print results
        for i, option in enumerate(options, 1):
            print(f"\nOption {i}:")
            print(f"Player: {option['player']}")
            print(f"Position: {option['position']}")
            print(f"Price: ${option['price']:,}")
            print(f"Average Points: {option['avg_points']:.1f}")
            print(f"Salary Remaining: ${option['salary_remaining']:,}")
            
    except FileNotFoundError:
        print("Error: Could not find NRL_stats.csv in the current directory")
    except Exception as e:
        print("An error occurred:", str(e))