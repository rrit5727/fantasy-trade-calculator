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

def assign_priority_level(player_data: pd.Series, consolidated_data: pd.DataFrame) -> int:
    """
    Assign priority level based on the updated rules.
    """
    # Rule 1: BPRE >= 30 for 2 consecutive weeks
    if check_rule_condition(player_data, 30, 2):
        return 1
        
    # Rule 2: BPRE >= 20 for 3 consecutive weeks
    if check_rule_condition(player_data, 20, 3):
        return 2
        
    # Rule 3: 3-week average BPRE >= 20
    if calculate_average_bpre(player_data['Player'], consolidated_data, 3) >= 20:
        return 3
        
    # Rule 4: BPRE >= 25 for 2 consecutive weeks
    if check_rule_condition(player_data, 25, 2):
        return 4
        
    # Rule 5: BPRE >= 15 for 3 consecutive weeks
    if check_rule_condition(player_data, 15, 3):
        return 5
        
    # Rule 6: 3-week average BPRE >= 15
    if calculate_average_bpre(player_data['Player'], consolidated_data, 3) >= 15:
        return 6
        
    # Rule 7: BPRE >= 10 for 3 consecutive weeks
    if check_rule_condition(player_data, 10, 3):
        return 7
        
    # Rule 8: BPRE >= 20 for 2 consecutive weeks (duplicate rule, can be removed)
    if check_rule_condition(player_data, 20, 2):
        return 8
        
    # Rule 9: 3-week average BPRE >= 10
    if calculate_average_bpre(player_data['Player'], consolidated_data, 3) >= 10:
        return 9
        
    # Rule 10: BPRE >= 15 for 2 consecutive weeks
    if check_rule_condition(player_data, 15, 2):
        return 10
        
    # Rule 11: BPRE >= 7 for 3 consecutive weeks
    if check_rule_condition(player_data, 7, 3):
        return 11
        
    # Rule 12: BPRE > 0 for 4 consecutive weeks
    if check_consistent_performance(player_data['Player'], consolidated_data, 0, 4) >= 4:
        return 12
        
    # Rule 13: BPRE >= 5 for 3 consecutive weeks
    if check_rule_condition(player_data, 5, 3):
        return 13
        
    # Rule 14: BPRE > 0 for 3 consecutive weeks
    if check_consistent_performance(player_data['Player'], consolidated_data, 0, 3) >= 3:
        return 14
        
    # Rule 15: BPRE >= 10 for 2 consecutive weeks
    if check_rule_condition(player_data, 10, 2):
        return 15

    # Default - lowest priority
    return 16

def calculate_average_bpre(
    player_name: str,
    consolidated_data: pd.DataFrame,
    lookback_weeks: int = 3
) -> float:
    """
    Calculate average BPRE for a player over their recent weeks.
    """
    player_data = consolidated_data[consolidated_data['Player'] == player_name].sort_values('Round', ascending=False)
    recent_data = player_data.head(lookback_weeks)
    if recent_data.empty:
        return 0.0
    return recent_data['Base exceeds price premium'].mean()

def calculate_average_base(
    player_name: str,
    consolidated_data: pd.DataFrame,
    lookback_weeks: int = 3
) -> float:
    """
    Calculate average Total base for a player over their recent weeks.
    """
    player_data = consolidated_data[consolidated_data['Player'] == player_name].sort_values('Round', ascending=False)
    recent_data = player_data.head(lookback_weeks)
    if recent_data.empty:
        return 0.0
    return recent_data['Total base'].mean()

def print_players_by_rule_level(available_players: pd.DataFrame, consolidated_data: pd.DataFrame, maximize_base: bool = False) -> None:
    """
    Print players that satisfy each rule level, with their relevant stats.
    If maximize_base is True, print top players by average base instead.
    """
    if maximize_base:
        print("\n=== Top Players by Average Base Stats ===\n")
        print("-" * 80)
        
        # Get all players who have played in any of the last 3 rounds
        last_three_rounds = sorted(consolidated_data['Round'].unique())[-3:]
        recent_players_data = consolidated_data[consolidated_data['Round'].isin(last_three_rounds)]
        all_players = recent_players_data['Player'].unique()
        
        # Calculate average base for all players
        player_stats = []
        for player in all_players:
            avg_base = calculate_average_base(player, consolidated_data)
            player_recent = consolidated_data[consolidated_data['Player'] == player].sort_values('Round', ascending=False).iloc[0]
            player_stats.append({
                'Player': player,
                'POS': player_recent['POS'],
                'Age': player_recent['Age'],
                'Current Base': player_recent['Total base'],
                'avg_base': avg_base,
                'Price': player_recent['Price']
            })
        
        # Convert to DataFrame and sort by average base
        stats_df = pd.DataFrame(player_stats)
        top_players = stats_df.nlargest(10, 'avg_base')
        
        for _, player in top_players.iterrows():
            print(
                f"Player: {player['Player']:<20} "
                f"Position: {player['POS']:<5} "
                f"Age: {player['Age']:<3} "
                f"Current Base: {player['Current Base']:>5.1f} "
                f"Avg Base: {player['avg_base']:>5.1f} "
                f"Price: ${player['Price']:,}"
            )
        return

    # Original rule-based output
    print("\n=== Players Satisfying Each Rule Level ===\n")
    rule_descriptions = {
        1: "BPRE >= 30 for 2 consecutive weeks",
        2: "BPRE >= 20 for 3 consecutive weeks",
        3: "3-week average BPRE >= 20",
        4: "BPRE >= 25 for 2 consecutive weeks",
        5: "BPRE >= 15 for 3 consecutive weeks",
        6: "3-week average BPRE >= 15",
        7: "BPRE >= 10 for 3 consecutive weeks",
        8: "BPRE >= 20 for 2 consecutive weeks (duplicate rule, can be removed)",
        9: "3-week average BPRE >= 10",
        10: "BPRE >= 15 for 2 consecutive weeks",
        11: "BPRE >= 7 for 3 consecutive weeks",
        12: "BPRE > 0 for 4 consecutive weeks",
        13: "BPRE >= 5 for 3 consecutive weeks",
        14: "BPRE > 0 for 3 consecutive weeks",
        15: "BPRE >= 10 for 2 consecutive weeks",
        16: "Default - lowest priority"
    }

    for level in range(1, 16):
        level_players = available_players[available_players['priority_level'] == level]
        
        if not level_players.empty:
            print(f"\nRule Level {level}: {rule_descriptions[level]}")
            print("-" * 80)
            
            # Calculate average BPRE for each player and add it to the DataFrame
            level_players = level_players.copy()
            level_players['avg_bpre'] = level_players['Player'].apply(
                lambda x: calculate_average_bpre(x, consolidated_data)
            )
            
            # Sort players by average BPRE within the rule level
            level_players_sorted = level_players.sort_values(
                by=['avg_bpre', 'Base exceeds price premium'],
                ascending=[False, False]
            )
            
            for _, player in level_players_sorted.iterrows():
                print(
                    f"Player: {player['Player']:<20} "
                    f"Position: {player['POS']:<5} "
                    f"Age: {player['Age']:<3} "
                    f"Current BPRE: {player['Base exceeds price premium']:>5.1f} "
                    f"Avg BPRE: {player['avg_bpre']:>5.1f} "
                    f"Base: {player['Total base']:>5.1f} "
                    f"Price: ${player['Price']:,} "
                    f"Consecutive Weeks: {player['consecutive_good_weeks']}"
                )

def calculate_trade_options(
    consolidated_data: pd.DataFrame,
    traded_out_players: List[str],
    maximize_base: bool = False,
    hybrid_approach: bool = False,
    max_options: int = 10,
    allowed_positions: List[str] = None,
    trade_type: str = 'likeForLike'
) -> List[Dict]:
    """
    Calculate possible trade combinations based on consolidated data and prioritized rules.
    If maximize_base is True, prioritize players with highest base stats instead of BPRE.
    """
    latest_round = consolidated_data['Round'].max()
    last_three_rounds = sorted(consolidated_data['Round'].unique())[-3:]
    
    # Get number of players needed based on traded out players
    num_players_needed = len(traded_out_players)
    
    # Calculate total salary freed up from traded out players
    salary_freed = 0
    for player in traded_out_players:
        player_data = consolidated_data[consolidated_data['Player'] == player].sort_values('Round', ascending=False)
        if not player_data.empty:
            salary_freed += player_data.iloc[0]['Price']
        else:
            print(f"Warning: Could not find price data for {player}")
    
    print(f"Total salary freed up: ${salary_freed:,}")
    
    # Get all players who have played in any of the last 3 rounds
    recent_players_data = consolidated_data[consolidated_data['Round'].isin(last_three_rounds)]
    available_players = (recent_players_data[~recent_players_data['Player'].isin(traded_out_players)]
                        .groupby('Player').last().reset_index())
    
    # Initialize consecutive_good_weeks column
    available_players['consecutive_good_weeks'] = 0
    
    # Calculate consistency for each player
    for idx, player in available_players.iterrows():
        consecutive_weeks = check_consistent_performance(
            player['Player'], 
            consolidated_data
        )
        available_players.at[idx, 'consecutive_good_weeks'] = consecutive_weeks
    
    # Calculate averages using all available games in last 3 rounds
    available_players['avg_bpre'] = available_players['Player'].apply(
        lambda x: calculate_average_bpre(x, consolidated_data)
    )
    
    available_players['avg_base'] = available_players['Player'].apply(
        lambda x: calculate_average_base(x, consolidated_data)
    )

    # Now calculate priority levels
    available_players['priority_level'] = available_players.apply(lambda row: assign_priority_level(row, consolidated_data), axis=1)

    # Print players by rule level
    print_players_by_rule_level(available_players, consolidated_data)

    # Group players by priority level
    priority_groups = {}
    for _, player in available_players.iterrows():
        level = player['priority_level']
        if level not in priority_groups:
            priority_groups[level] = []
        priority_groups[level].append(player)

    # Generate comprehensive trade options
    def generate_comprehensive_trade_options(priority_groups):
        valid_combinations = []
        used_players = set()
        
        # Flatten all priority groups into a single sorted list
        all_priority_levels = sorted(priority_groups.keys())
        flat_players = []
        for level in all_priority_levels:
            flat_players.extend(priority_groups[level])
        
        # Iterate through players across all priority levels
        for i in range(0, len(flat_players), 2):
            # Ensure we have at least two players
            if i + 1 >= len(flat_players):
                break
            
            first_player = flat_players[i]
            second_player = flat_players[i + 1]
            
            # Skip if players have already been used
            if first_player['Player'] in used_players or second_player['Player'] in used_players:
                continue
            
            total_price = first_player['Price'] + second_player['Price']
            if total_price <= salary_freed:
                combo_avg_bpre = (first_player['avg_bpre'] + second_player['avg_bpre']) / 2
                combo_priority = max(first_player['priority_level'], second_player['priority_level'])
                
                valid_combinations.append({
                    'priority_level': combo_priority,
                    'players': [
                        {
                            'name': first_player['Player'],
                            'position': first_player['POS'],
                            'price': first_player['Price'],
                            'total_base': first_player['Total base'],
                            'base_premium': first_player['Base exceeds price premium'],
                            'consecutive_good_weeks': first_player['consecutive_good_weeks'],
                            'priority_level': first_player['priority_level'],
                            'avg_bpre': first_player['avg_bpre']
                        },
                        {
                            'name': second_player['Player'],
                            'position': second_player['POS'],
                            'price': second_player['Price'],
                            'total_base': second_player['Total base'],
                            'base_premium': second_player['Base exceeds price premium'],
                            'consecutive_good_weeks': second_player['consecutive_good_weeks'],
                            'priority_level': second_player['priority_level'],
                            'avg_bpre': second_player['avg_bpre']
                        }
                    ],
                    'total_price': total_price,
                    'total_base': first_player['Total base'] + second_player['Total base'],
                    'total_base_premium': (first_player['Base exceeds price premium'] + second_player['Base exceeds price premium']),
                    'salary_remaining': salary_freed - total_price,
                    'total_avg_base': first_player['avg_base'] + second_player['avg_base']
                })
                
                # Mark players as used
                used_players.add(first_player['Player'])
                used_players.add(second_player['Player'])
        
        return valid_combinations

    # Replace the trade option generation section with the new function
    options = generate_comprehensive_trade_options(priority_groups)
    
    # Limit to max_options
    return options[:max_options]

if __name__ == "__main__":
    try:
        # Example file path - modify according to your setup
        file_path = "NRL_stats.xlsx"
        
        # Load consolidated data
        consolidated_data = load_data(file_path)
        print(f"Successfully loaded data for {consolidated_data['Round'].nunique()} rounds")
        
        # Get user preference for optimization strategy first
        while True:
            strategy = input("\nDo you want to:\n1. Maximize value (BPRE)\n2. Maximize base stats\n3. Hybrid approach (BPRE + Base stats)\nEnter 1, 2, or 3: ")
            if strategy in ['1', '2', '3']:
                break
            print("Invalid input. Please enter 1, 2, or 3.")

        maximize_base = (strategy == '2')
        hybrid_approach = (strategy == '3')

        # Then get position preferences
        valid_positions = ['HOK', 'HLF', 'CTR', 'WFB', 'EDG', 'MID']
        while True:
            print("\nSelect positions to consider:")
            print("0. All positions")
            for i, pos in enumerate(valid_positions, 1):
                print(f"{i}. {pos}")
            
            try:
                pos1 = int(input("\nSelect first position (0-6): "))
                if pos1 < 0 or pos1 > 6:
                    raise ValueError
                
                if pos1 == 0:
                    allowed_positions = None
                    break
                
                pos2 = int(input("Select second position (1-6, or same as first position): "))
                if pos2 < 1 or pos2 > 6:
                    raise ValueError
                
                allowed_positions = [valid_positions[pos1-1]]
                if pos1 != pos2:
                    allowed_positions.append(valid_positions[pos2-1])
                break
            except ValueError:
                print("Invalid input. Please enter valid numbers.")

        # Add P. Haas stats check for option 2
        if maximize_base:
            player_name = "P. Haas"
            avg_base = calculate_average_base(player_name, consolidated_data)
            latest_round = consolidated_data['Round'].max()
            latest_data = consolidated_data[
                (consolidated_data['Round'] == latest_round) & 
                (consolidated_data['Player'] == player_name)
            ]
            if not latest_data.empty:
                current_base = latest_data.iloc[0]['Total base']
                print(f"\n{player_name}'s stats:")
                print(f"Current base: {current_base:.1f}")
                print(f"Average base over last 3 rounds: {avg_base:.1f}\n")
        
        
        
        print(f"\nCalculating trade options for trading out: {', '.join(traded_out_players)}")
        print(f"Strategy: {'Maximizing base stats' if maximize_base else 'Maximizing value (BPRE)' if not hybrid_approach else 'Hybrid approach (BPRE + Base stats)'}")
        if allowed_positions:
            print(f"Considering only positions: {', '.join(allowed_positions)}")
        else:
            print("Considering all positions")
        
        options = calculate_trade_options(
            consolidated_data,
            traded_out_players,
            maximize_base=maximize_base,
            hybrid_approach=hybrid_approach,
            max_options=10,
            allowed_positions=allowed_positions
        )
        
        if options:
            print("\n=== Recommended Trade Combinations ===\n")
            for i, option in enumerate(options, 1):
                print(f"\nOption {i}")
                print("Players to trade in:")
                for player in option['players']:
                    if maximize_base:
                        print(f"- {player['name']} ({player['position']})")
                        print(f"  Price: ${player['price']:,}")
                        print(f"  Current Base: {player['total_base']}")
                        print(f"  Average Base: {player['avg_base']:.1f}")
                    else:
                        print(f"- {player['name']} ({player['position']})")
                        print(f"  Price: ${player['price']:,}")
                        print(f"  Current Base Premium: {player['base_premium']}")
                        print(f"  Consecutive Weeks above threshold: {player['consecutive_good_weeks']}")
                
                print(f"Total Price: ${option['total_price']:,}")
                if maximize_base:
                    print(f"Combined Average Base: {option['total_avg_base']:.1f}")
                else:
                    print(f"Combined Base Premium: {option['total_base_premium']}")
                print(f"Salary Remaining: ${option['salary_remaining']:,}")
            
    except FileNotFoundError:
        print("Error: Could not find data file in the current directory")
    except ValueError as e:
        print("Error:", str(e))
    except Exception as e:
        print("An error occurred:", str(e))