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
    consecutive_good_weeks: int
    age: int

def load_data(file_path: str) -> pd.DataFrame:
    """
    Load data from a single file containing multiple rounds.
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

def check_rule_condition(
    player_data: pd.Series,
    base_premium_threshold: int,
    weeks_threshold: int,
    position_requirement: str = None,
    max_age: int = None
) -> bool:
    """
    Check if a player meets the specified rule conditions.
    """
    # Check base premium threshold for current week
    meets_bpre = player_data['Base exceeds price premium'] >= base_premium_threshold
    
    # Check consecutive weeks requirement
    meets_weeks = True if weeks_threshold <= 1 else player_data['consecutive_good_weeks'] >= weeks_threshold
    
    if position_requirement:
        positions = position_requirement.split('|')
        meets_position = player_data['POS'] in positions
    else:
        meets_position = True
        
    if max_age is not None:
        meets_age = player_data['Age'] <= max_age
    else:
        meets_age = True
        
    return meets_bpre and meets_weeks and meets_position and meets_age

def assign_priority_level(player_data: pd.Series) -> int:
    """
    Assign priority level based on hierarchical rules.
    """
    # Rule 1: BPRE > 8 for 3 weeks
    if check_rule_condition(player_data, 8, 3):
        return 1
        
    # Rule 2: BPRE > 13 for 2 consecutive weeks
    if check_rule_condition(player_data, 13, 2):
        return 2
        
    # Rule 3: BPRE > 6 for 3 weeks (except mids age over 29)
    if check_rule_condition(player_data, 6, 3, None, 29):
        return 3
        
    # Rule 4: HLF, CTR or WFB has BPRE > 5 for 3 weeks
    if check_rule_condition(player_data, 5, 3, "HLF|CTR|WFB"):
        return 4
        
    # Rule 5: Mid BPRE > 7 for 3 weeks (except mids over 29)
    if check_rule_condition(player_data, 7, 3, "MID", 29):
        return 5
        
    # Rule 6: HLF BPRE > 10 for 2 weeks
    if check_rule_condition(player_data, 10, 2, "HLF"):
        return 6
        
    # Rule 7: CTR or WFB has BPRE > 8 for 2 weeks
    if check_rule_condition(player_data, 8, 2, "CTR|WFB"):
        return 7
        
    # Rule 8: MID has BPRE > 10 for 2 weeks (except mids over 29)
    if check_rule_condition(player_data, 10, 2, "MID", 29):
        return 8
        
    # Rule 9: HLF BPRE > 7 for 2 weeks
    if check_rule_condition(player_data, 7, 2, "HLF"):
        return 9
        
    # Rule 10: HOK BPRE > 10 for 2 weeks
    if check_rule_condition(player_data, 10, 2, "HOK"):
        return 10
        
    # Rule 11: CTR or WFB has BPRE > 5 for 2 weeks
    if check_rule_condition(player_data, 5, 2, "CTR|WFB"):
        return 11
        
    # Rule 12: HLF BPRE > 5 for 2 weeks
    if check_rule_condition(player_data, 5, 2, "HLF"):
        return 12
        
    # Rule 13: Mid has BPRE > 7 for 2 weeks
    if check_rule_condition(player_data, 7, 2, "MID"):
        return 13
        
    # Rule 14: Any position that has BPRE > 5 for 2 weeks
    if check_rule_condition(player_data, 5, 2):
        return 14
        
    # Rule 15: Default - lowest priority
    return 15

def print_players_by_rule_level(available_players: pd.DataFrame) -> None:
    """
    Print players that satisfy each rule level, with their relevant stats.
    """
    rule_descriptions = {
        1: "BPRE > 8 for 3 weeks - immediate buy",
        2: "BPRE > 13 for 2 consecutive weeks - immediate buy",
        3: "BPRE > 6 for 3 weeks (except mids age over 29)",
        4: "HLF, CTR or WFB has BPRE > 5 for 3 weeks",
        5: "Mid BPRE > 7 for 3 weeks (except mids over 29)",
        6: "HLF BPRE > 10 for 2 weeks",
        7: "CTR or WFB has BPRE > 8 for 2 weeks",
        8: "MID has BPRE > 10 for 2 weeks (except mids over 29)",
        9: "HLF BPRE > 7 for 2 weeks",
        10: "HOK BPRE > 10 for 2 weeks",
        11: "CTR or WFB has BPRE > 5 for 2 weeks",
        12: "HLF BPRE > 5 for 2 weeks",
        13: "Mid has BPRE > 7 for 2 weeks",
        14: "Any position that has BPRE > 5 for 2 weeks",
        15: "Otherwise rank player that has highest BPRE for most recent week"
    }

    print("\n=== Players Satisfying Each Rule Level ===\n")
    
    for level in range(1, 16):
        level_players = available_players[available_players['priority_level'] == level]
        
        if not level_players.empty:
            print(f"\nRule Level {level}: {rule_descriptions[level]}")
            print("-" * 80)
            
            # Sort players by BPRE and base stat within the rule level
            level_players_sorted = level_players.sort_values(
                by=['Base exceeds price premium', 'Total base'],
                ascending=[False, False]
            )
            
            for _, player in level_players_sorted.iterrows():
                print(
                    f"Player: {player['Player']:<20} "
                    f"Position: {player['POS']:<5} "
                    f"Age: {player['Age']:<3} "
                    f"BPRE: {player['Base exceeds price premium']:>5.1f} "
                    f"Base: {player['Total base']:>5.1f} "
                    f"Price: ${player['Price']:,} "
                    f"Consecutive Weeks: {player['consecutive_good_weeks']}"
                )

def calculate_trade_options(
    consolidated_data: pd.DataFrame,
    traded_out_players: List[str],
    max_options: int = 10
) -> List[Dict]:
    """
    Calculate possible trade combinations based on consolidated data and prioritized rules.
    """
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
    
    # Initialize consecutive_good_weeks column
    available_players['consecutive_good_weeks'] = 0
    
    # Calculate consistency for each player
    for idx, player in available_players.iterrows():
        consecutive_weeks = check_consistent_performance(
            player['Player'], 
            consolidated_data
        )
        available_players.at[idx, 'consecutive_good_weeks'] = consecutive_weeks
    
    # Now calculate priority levels
    available_players['priority_level'] = available_players.apply(assign_priority_level, axis=1)
    
    # Print players by rule level
    print_players_by_rule_level(available_players)
    
    # Sort players by priority level, then by BPRE and base stat within each level
    available_players = available_players.sort_values(
        by=['priority_level', 'Base exceeds price premium', 'Total base'],
        ascending=[True, False, False]
    )
    
    print("\n=== Trade Combinations ===\n")
    
    # Generate trade combinations
    valid_combinations = []
    
    # Get all possible combinations of positions needed
    all_positions = traded_players['POS'].tolist()
    pos_combinations = list(combinations(all_positions, len(all_positions)))
    
    for pos_combo in pos_combinations:
        eligible_players = available_players[available_players['POS'].isin(pos_combo)]
        
        for players in combinations(eligible_players.to_dict('records'), num_players_needed):
            total_price = sum(p['Price'] for p in players)
            if total_price <= salary_freed:
                combo_priority = min(p['priority_level'] for p in players)  # Best priority level
                valid_combinations.append({
                    'priority_level': combo_priority,
                    'players': [
                        {
                            'name': p['Player'],
                            'position': p['POS'],
                            'price': p['Price'],
                            'total_base': p['Total base'],
                            'base_premium': p['Base exceeds price premium'],
                            'consecutive_good_weeks': p['consecutive_good_weeks'],
                            'priority_level': p['priority_level']
                        } for p in players
                    ],
                    'total_price': total_price,
                    'total_base': sum(p['Total base'] for p in players),
                    'total_base_premium': sum(p['Base exceeds price premium'] for p in players),
                    'salary_remaining': salary_freed - total_price
                })
    
    # Sort combinations by priority level, then by total base premium
    valid_combinations.sort(key=lambda x: (x['priority_level'], -x['total_base_premium']))
    
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
            max_options=10
        )
        
        if options:
            print("\n=== Recommended Trade Combinations ===\n")
            for i, option in enumerate(options, 1):
                print(f"\nOption {i} (Priority Level {option['priority_level']}):")
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
