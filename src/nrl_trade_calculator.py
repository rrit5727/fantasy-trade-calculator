import pandas as pd
from typing import List, Dict, Tuple
from dataclasses import dataclass
from itertools import combinations
from datetime import datetime

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
    
    # Ensure required columns exist
    required_columns = ['Round', 'Team']  # Added 'Team' to required columns
    for col in required_columns:
        if col not in df.columns and file_path != 'teamlists.csv':
            raise ValueError(f"Data must contain a '{col}' column")
    
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
    consolidated_data: pd.DataFrame,
    base_premium_threshold: int,
    weeks_threshold: int,
    position_requirement: str = None,
    max_age: int = None
) -> bool:
    """
    Check if a player meets the specified rule conditions.
    Exclude Mid/EDG players who are 29 years or older.
    """
    # Exclude Mid/EDG players who are 29 years or older
    if player_data['POS'] in ['MID', 'EDG'] and player_data['Age'] >= 29:
        return False
    
    # Check base premium threshold for current week
    meets_bpre = player_data['Base exceeds price premium'] >= base_premium_threshold
    
    # Check consecutive weeks requirement
    player_name = player_data['Player']
    player_history = consolidated_data[consolidated_data['Player'] == player_name].sort_values('Round')
    
    # Check if the player has met the threshold for the required consecutive weeks
    current_streak = 0
    for _, row in player_history.iterrows():
        if row['Base exceeds price premium'] >= base_premium_threshold:
            current_streak += 1
        else:
            current_streak = 0
        
        if current_streak >= weeks_threshold:
            break
    
    meets_weeks = current_streak >= weeks_threshold
    
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
    # Rule 1: BPRE >= 14 for last 3 weeks
    if check_rule_condition(player_data, consolidated_data, 14, 3):
        return 1
        
    # Rule 2: BPRE >= 21 for last 2 weeks
    if check_rule_condition(player_data, consolidated_data, 21, 2):
        return 2
        
    # Rule 3: 2 week Average BPRE >= 26
    if calculate_average_bpre(player_data['Player'], consolidated_data, 2) >= 26:
        return 3
        
    # Rule 4: BPRE >= 12 for last 3 weeks
    if check_rule_condition(player_data, consolidated_data, 12, 3):
        return 4
        
    # Rule 5: BPRE >= 19 for last 2 weeks
    if check_rule_condition(player_data, consolidated_data, 19, 2):
        return 5
        
    # Rule 6: 2 week Average BPRE >= 24
    if calculate_average_bpre(player_data['Player'], consolidated_data, 2) >= 24:
        return 6
        
    # Rule 7: BPRE >= 10 for last 3 weeks
    if check_rule_condition(player_data, consolidated_data, 10, 3):
        return 7
        
    # Rule 8: BPRE >= 17 for last 2 weeks
    if check_rule_condition(player_data, consolidated_data, 17, 2):
        return 8
        
    # Rule 9: 2 week Average BPRE >= 22
    if calculate_average_bpre(player_data['Player'], consolidated_data, 2) >= 22:
        return 9
        
    # Rule 10: BPRE >= 8 for last 3 weeks
    if check_rule_condition(player_data, consolidated_data, 8, 3):
        return 10
        
    # Rule 11: BPRE >= 15 for last 2 weeks
    if check_rule_condition(player_data, consolidated_data, 15, 2):
        return 11
        
    # Rule 12: 2 week Average BPRE >= 20
    if calculate_average_bpre(player_data['Player'], consolidated_data, 2) >= 20:
        return 12
        
    # Rule 13: BPRE >= 6 for last 3 weeks
    if check_rule_condition(player_data, consolidated_data, 6, 3):
        return 13
        
    # Rule 14: BPRE >= 13 for last 2 weeks
    if check_rule_condition(player_data, consolidated_data, 13, 2):
        return 14
        
    # Rule 15: 2 week Average BPRE >= 18
    if calculate_average_bpre(player_data['Player'], consolidated_data, 2) >= 18:
        return 15
        
    # Rule 16: BPRE >= 10 for last 2 weeks
    if check_rule_condition(player_data, consolidated_data, 10, 2):
        return 16
        
    # Rule 17: 2 week Average BPRE >= 15
    if calculate_average_bpre(player_data['Player'], consolidated_data, 2) >= 15:
        return 17
        
    # Rule 18: BPRE >= 8 for last 2 weeks
    if check_rule_condition(player_data, consolidated_data, 8, 2):
        return 18
        
    # Rule 19: 2 week Average BPRE >= 13
    if calculate_average_bpre(player_data['Player'], consolidated_data, 2) >= 13:
        return 19
        
    # Rule 20: BPRE >= 6 for last 2 weeks
    if check_rule_condition(player_data, consolidated_data, 6, 2):
        return 20
        
    # Rule 21: 2 week Average BPRE >= 11
    if calculate_average_bpre(player_data['Player'], consolidated_data, 2) >= 11:
        return 21
        
    # Rule 22: BPRE >= 2 for last 3 weeks
    if check_rule_condition(player_data, consolidated_data, 2, 3):
        return 22
        
    # Rule 23: BPRE >= 4 for last 2 weeks
    if check_rule_condition(player_data, consolidated_data, 4, 2):
        return 23
        
    # Rule 24: 2 week Average BPRE >= 9
    if calculate_average_bpre(player_data['Player'], consolidated_data, 2) >= 9:
        return 24
        
    # Default - lowest priority
    return 25

def calculate_average_bpre(
    player_name: str,
    consolidated_data: pd.DataFrame,
    lookback_weeks: int = 3
) -> float:
    """
    Calculate average BPRE for a player over their recent weeks.
    Only calculate the average if the player has played in at least `lookback_weeks` rounds.
    Exclude Mid/EDG players who are 29 years or older.
    """
    player_data = consolidated_data[consolidated_data['Player'] == player_name].sort_values('Round', ascending=False)
    
    # Exclude Mid/EDG players who are 29 years or older
    if not player_data.empty:
        if player_data.iloc[0]['POS'] in ['MID', 'EDG'] and player_data.iloc[0]['Age'] >= 29:
            return 0.0  # Exclude these players
    
    recent_data = player_data.head(lookback_weeks)
    
    # Only calculate the average if the player has played in at least `lookback_weeks` rounds
    if len(recent_data) < lookback_weeks:
        return 0.0  # Return 0 if the player hasn't played enough rounds
    
    return int(recent_data['Base exceeds price premium'].mean())

def calculate_average_base(
    player_name: str,
    consolidated_data: pd.DataFrame,
    lookback_weeks: int = 3,
    min_games: int = 2  # New parameter to specify minimum games required
) -> float:
    """
    Calculate average Total base for a player over their recent weeks.
    Only calculate the average if the player has played in at least `min_games` rounds.
    
    Parameters:
    player_name (str): Name of the player
    consolidated_data (pd.DataFrame): DataFrame containing all player data
    lookback_weeks (int): Number of weeks to look back for calculating average
    min_games (int): Minimum number of games required to calculate average
    
    Returns:
    float: Average base value, or 0.0 if minimum games requirement not met
    """
    player_data = consolidated_data[consolidated_data['Player'] == player_name].sort_values('Round', ascending=False)
    recent_data = player_data.head(lookback_weeks)
    
    # Check if player has played minimum required games
    if len(recent_data) >= min_games:
        return int(recent_data['Total base'].mean())
    return 0.0

def print_players_by_rule_level(available_players: pd.DataFrame, consolidated_data: pd.DataFrame, maximize_base: bool = False) -> None:
    """
    Print players that satisfy each rule level, with their relevant stats.
    """
    print("\n=== Players Satisfying Each Rule Level ===\n")
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

    for level in range(1, 25):  # Exclude rule 25
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
                # Get the player's BPRE for each round in the last 3 rounds
                player_data = consolidated_data[consolidated_data['Player'] == player['Player']].sort_values('Round')
                bpre_by_round = player_data[['Round', 'Base exceeds price premium']].dropna()
                bpre_values = ", ".join([f"round {int(row['Round'])} BPRE: {int(row['Base exceeds price premium'])}" for _, row in bpre_by_round.iterrows()])
                
                print(
                    f"Player: {player['Player']:<20} "
                    f"Team: {player['Team']:<4} "  # Added Team to output
                    f"Position: {player['POS']:<5} "
                    f"Age: {player['Age']:<3} "
                    f"Current BPRE: {int(player['Base exceeds price premium']):>5} "
                    f"Avg BPRE: {int(player['avg_bpre']):>5} "
                    f"Base: {int(player['Total base']):>5} "
                    f"Price: ${player['Price']:,}"
                )
                print(f"BPRE by Round: {bpre_values}")

def generate_comprehensive_trade_options(
    priority_groups, 
    salary_freed, 
    maximize_base=False, 
    hybrid_approach=False, 
    max_options=10,
    trade_type='likeForLike',
    traded_out_positions=None,
    num_players_needed=2
):
    """
    Generate trade combinations based on selected optimization strategy while ensuring
    position requirements are met for like-for-like trades.
    """
    valid_combinations = []
    used_players = set()
    
    if trade_type == 'likeForLike' and traded_out_positions:
        # For like-for-like trades, filter players by position first
        position_filtered_groups = {}
        for level in priority_groups:
            position_filtered_groups[level] = [
                player for player in priority_groups[level]
                if player['POS'] in traded_out_positions
            ]
    else:
        position_filtered_groups = priority_groups
        
    if maximize_base:
        # Flatten and sort all players by base stats
        flat_players = []
        for level in sorted(position_filtered_groups.keys()):
            flat_players.extend(position_filtered_groups[level])
        flat_players.sort(key=lambda x: (x['avg_base'], x['avg_bpre']), reverse=True)
        
        # Generate combinations
        if num_players_needed == 1:
            for player in flat_players:
                if player['Player'] in used_players:
                    continue
                
                if player['Price'] <= salary_freed:
                    combo = create_combination([player], player['Price'], salary_freed)
                    valid_combinations.append(combo)
                    used_players.add(player['Player'])
                    if len(valid_combinations) >= max_options:
                        break
        else:
            if trade_type == 'likeForLike' and traded_out_positions:
                for i in range(len(flat_players)):
                    if flat_players[i]['Player'] in used_players:
                        continue
                        
                    for j in range(i + 1, len(flat_players)):
                        if flat_players[j]['Player'] in used_players:
                            continue
                            
                        first_player = flat_players[i]
                        second_player = flat_players[j]
                        
                        # Check if positions match traded out positions
                        positions = {first_player['POS'], second_player['POS']}
                        if positions != set(traded_out_positions):
                            continue
                            
                        total_price = first_player['Price'] + second_player['Price']
                        if total_price <= salary_freed:
                            combo = create_combination([first_player, second_player], total_price, salary_freed)
                            valid_combinations.append(combo)
                            used_players.add(first_player['Player'])
                            used_players.add(second_player['Player'])
                            break
            else:
                # Original logic for non-like-for-like trades
                for i in range(len(flat_players)):
                    if flat_players[i]['Player'] in used_players:
                        continue
                        
                    for j in range(i + 1, len(flat_players)):
                        if flat_players[j]['Player'] in used_players:
                            continue
                            
                        first_player = flat_players[i]
                        second_player = flat_players[j]
                        total_price = first_player['Price'] + second_player['Price']
                        
                        if total_price <= salary_freed:
                            combo = create_combination([first_player, second_player], total_price, salary_freed)
                            valid_combinations.append(combo)
                            used_players.add(first_player['Player'])
                            used_players.add(second_player['Player'])
                            break
                        
    elif hybrid_approach:
        value_players = []
        for level in sorted(position_filtered_groups.keys()):
            level_players = position_filtered_groups[level]
            level_players.sort(key=lambda x: x['avg_bpre'], reverse=True)
            value_players.extend(level_players)
        
        base_players = []
        for level in sorted(position_filtered_groups.keys()):
            base_players.extend(position_filtered_groups[level])
        base_players.sort(key=lambda x: x['avg_base'], reverse=True)
        
        if num_players_needed == 1:
            for player in value_players:
                if player['Player'] in used_players:
                    continue
                
                if player['Price'] <= salary_freed:
                    combo = create_combination([player], player['Price'], salary_freed)
                    valid_combinations.append(combo)
                    used_players.add(player['Player'])
                    if len(valid_combinations) >= max_options:
                        break
        else:
            if trade_type == 'likeForLike' and traded_out_positions:
                for value_player in value_players:
                    if value_player['Player'] in used_players:
                        continue
                        
                    remaining_salary = salary_freed - value_player['Price']
                    needed_position = [pos for pos in traded_out_positions if pos != value_player['POS']][0]
                    
                    for base_player in base_players:
                        if (base_player['Player'] not in used_players and 
                            base_player['Player'] != value_player['Player'] and 
                            base_player['POS'] == needed_position and
                            base_player['Price'] <= remaining_salary):
                            
                            combo = create_combination([value_player, base_player], 
                                                    value_player['Price'] + base_player['Price'],
                                                    salary_freed)
                            valid_combinations.append(combo)
                            used_players.add(value_player['Player'])
                            used_players.add(base_player['Player'])
                            break
            else:
                # Original hybrid approach logic
                for value_player in value_players:
                    if value_player['Player'] in used_players:
                        continue
                        
                    remaining_salary = salary_freed - value_player['Price']
                    
                    for base_player in base_players:
                        if (base_player['Player'] not in used_players and 
                            base_player['Player'] != value_player['Player'] and 
                            base_player['Price'] <= remaining_salary):
                            
                            combo = create_combination([value_player, base_player],
                                                    value_player['Price'] + base_player['Price'],
                                                    salary_freed)
                            valid_combinations.append(combo)
                            used_players.add(value_player['Player'])
                            used_players.add(base_player['Player'])
                            break
    else:  # maximize_value - strict rule level ordering
        priority_levels = sorted(position_filtered_groups.keys())
        
        for level in priority_levels:
            players_in_level = position_filtered_groups[level]
            players_in_level.sort(key=lambda x: x['avg_bpre'], reverse=True)
            
            if num_players_needed == 1:
                for player in players_in_level:
                    if player['Player'] in used_players:
                        continue
                    
                    if player['Price'] <= salary_freed:
                        combo = create_combination([player], player['Price'], salary_freed)
                        valid_combinations.append(combo)
                        used_players.add(player['Player'])
                        if len(valid_combinations) >= max_options:
                            break
            else:
                if trade_type == 'likeForLike' and traded_out_positions:
                    for i, first_player in enumerate(players_in_level):
                        if first_player['Player'] in used_players:
                            continue
                            
                        valid_combo_found = False
                        needed_position = [pos for pos in traded_out_positions if pos != first_player['POS']]
                        
                        # Try pairing with other players from same level with matching position
                        for j in range(i + 1, len(players_in_level)):
                            second_player = players_in_level[j]
                            if (second_player['Player'] not in used_players and 
                                second_player['POS'] in needed_position):
                                
                                total_price = first_player['Price'] + second_player['Price']
                                if total_price <= salary_freed:
                                    combo = create_combination([first_player, second_player],
                                                            total_price, salary_freed)
                                    valid_combinations.append(combo)
                                    used_players.add(first_player['Player'])
                                    used_players.add(second_player['Player'])
                                    valid_combo_found = True
                                    break
                        
                        if not valid_combo_found and first_player['Player'] not in used_players:
                            # Try next levels if no valid combination found in current level
                            for next_level in priority_levels[priority_levels.index(level)+1:]:
                                for second_player in position_filtered_groups[next_level]:
                                    if (second_player['Player'] not in used_players and 
                                        second_player['POS'] in needed_position):
                                        
                                        total_price = first_player['Price'] + second_player['Price']
                                        if total_price <= salary_freed:
                                            combo = create_combination([first_player, second_player],
                                                                    total_price, salary_freed)
                                            valid_combinations.append(combo)
                                            used_players.add(first_player['Player'])
                                            used_players.add(second_player['Player'])
                                            valid_combo_found = True
                                            break
                                
                                if valid_combo_found:
                                    break
                else:
                    # Original maximize_value logic
                    for i, first_player in enumerate(players_in_level):
                        if first_player['Player'] in used_players:
                            continue
                            
                        valid_combo_found = False
                        
                        for j in range(i + 1, len(players_in_level)):
                            second_player = players_in_level[j]
                            if second_player['Player'] in used_players:
                                continue
                                
                            total_price = first_player['Price'] + second_player['Price']
                            if total_price <= salary_freed:
                                combo = create_combination([first_player, second_player],
                                                        total_price, salary_freed)
                                valid_combinations.append(combo)
                                used_players.add(first_player['Player'])
                                used_players.add(second_player['Player'])
                                valid_combo_found = True
                                break
                        
                        if not valid_combo_found and first_player['Player'] not in used_players:
                            for next_level in priority_levels[priority_levels.index(level)+1:]:
                                for second_player in position_filtered_groups[next_level]:
                                    if second_player['Player'] not in used_players:
                                        total_price = first_player['Price'] + second_player['Price']
                                        if total_price <= salary_freed:
                                            combo = create_combination([first_player, second_player],
                                                                    total_price, salary_freed)
                                            valid_combinations.append(combo)
                                            used_players.add(first_player['Player'])
                                            used_players.add(second_player['Player'])
                                            valid_combo_found = True
                                            break
                                if valid_combo_found:
                                    break
    
    return valid_combinations[:max_options]

def create_combination(players, total_price, salary_freed):
    """Helper function to create a trade combination dictionary"""
    return {
        'players': [create_player_dict(player) for player in players],
        'total_price': total_price,
        'total_base': sum(player['Total base'] for player in players),
        'total_base_premium': sum(player['Base exceeds price premium'] for player in players),
        'salary_remaining': salary_freed - total_price,
        'total_avg_base': sum(player['avg_base'] for player in players),
        'combo_avg_bpre': sum(player['avg_bpre'] for player in players) / len(players)
    }

def create_player_dict(player):
    """Helper function to create consistent player dictionaries"""
    return {
        'name': player['Player'],
        'team': player['Team'],  # Added team to player dictionary
        'position': player['POS'],
        'price': player['Price'],
        'total_base': player['Total base'],
        'base_premium': player['Base exceeds price premium'],
        'consecutive_good_weeks': player['consecutive_good_weeks'],
        'priority_level': player['priority_level'],
        'avg_bpre': player['avg_bpre'],
        'avg_base': player['avg_base']
    }

def get_traded_out_positions(traded_out_players: List[str], consolidated_data: pd.DataFrame) -> List[str]:
    """
    Get the positions of the players being traded out.
    
    Parameters:
    traded_out_players (List[str]): List of player names being traded out
    consolidated_data (pd.DataFrame): Full dataset containing player information
    
    Returns:
    List[str]: List of positions corresponding to traded out players
    """
    positions = []
    for player in traded_out_players:
        player_data = consolidated_data[consolidated_data['Player'] == player].sort_values('Round', ascending=False)
        if not player_data.empty:
            positions.append(player_data.iloc[0]['POS'])
    return positions

def get_locked_out_players(simulate_datetime: str, consolidated_data: pd.DataFrame) -> set:
    """
    Get the set of players who are locked out based on the simulated date/time.
    """
    if not simulate_datetime:
        return set()
    
    # Parse the simulated date/time
    simulate_dt = datetime.strptime(simulate_datetime, '%Y-%m-%dT%H:%M')
    
    # Define the fixtures
    fixtures = [
        ("2025-03-02 11:00", ["CAN", "WAR"]),
        ("2025-03-02 15:30", ["PEN", "CRO"]),
        ("2025-03-06 20:00", ["SYD", "BRI"]),
        ("2025-03-07 18:00", ["WST", "NEW"]),
        ("2025-03-07 20:05", ["DOL", "SOU"]),
        ("2025-03-08 17:30", ["SGI", "CBY"]),
        ("2025-03-08 19:35", ["MAN", "NQL"]),
        ("2025-03-09 16:05", ["MEL", "SOU"]),
    ]
    
    locked_out_teams = set()
    for fixture_time, teams in fixtures:
        fixture_dt = datetime.strptime(fixture_time, '%Y-%m-%d %H:%M')
        if fixture_dt <= simulate_dt:
            locked_out_teams.update(teams)
    
    # Use the Team column from the main data instead of teamlists.csv
    locked_out_players = set()
    latest_round_data = consolidated_data.sort_values('Round').groupby('Player').last().reset_index()
    
    for team in locked_out_teams:
        team_players = latest_round_data[latest_round_data['Team'] == team]['Player'].tolist()
        locked_out_players.update(team_players)
    
    return locked_out_players

def calculate_trade_options(
    consolidated_data: pd.DataFrame,
    traded_out_players: List[str],
    maximize_base: bool = False,
    hybrid_approach: bool = False,
    max_options: int = 10,
    allowed_positions: List[str] = None,
    trade_type: str = 'likeForLike',
    min_games: int = 2,  # New parameter
    team_list: List[str] = None,  # Parameter to receive team list restriction
    simulate_datetime: str = None,
    apply_lockout: bool = False
) -> List[Dict]:
    # Get locked out players if lockout restriction is applied
    locked_out_players = set()
    if apply_lockout:
        locked_out_players = get_locked_out_players(simulate_datetime, consolidated_data)
    
    # Get positions of traded out players for like-for-like trades
    traded_out_positions = (get_traded_out_positions(traded_out_players, consolidated_data) 
                          if trade_type == 'likeForLike' 
                          else None)
    
    # Use allowed_positions only for positional swap trades
    positions_to_use = (allowed_positions if trade_type == 'positionalSwap' 
                       else None)
    
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
    
    # Apply team list restriction first if enabled
    if team_list:
        available_players = available_players[available_players['Player'].isin(team_list)]
        if available_players.empty:
            print("Warning: No players available after applying team list restriction")
            return []
    
    # Apply lockout restriction if enabled
    if apply_lockout:
        available_players = available_players[~available_players['Player'].isin(locked_out_players)]
        if available_players.empty:
            print("Warning: No players available after applying lockout restriction")
            return []
    
    # Then filter players by allowed positions if specified
    if positions_to_use:
        available_players = available_players[available_players['POS'].isin(positions_to_use)]
    
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
        lambda x: calculate_average_base(x, consolidated_data, min_games=min_games)
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
    options = generate_comprehensive_trade_options(
        priority_groups,
        salary_freed,
        maximize_base,
        hybrid_approach,
        max_options,
        trade_type,
        traded_out_positions,
        num_players_needed
    )
    
    # Limit to max_options
    return options[:max_options]

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
        cumulative_data = consolidated_data[consolidated_data['Round'] <= round_num]
        player_data = cumulative_data[cumulative_data['Player'] == player_name]
        
        if player_data.empty:
            print(f"Round {round_num}: No data for player {player_name}")
            continue
        
        priority_level = assign_priority_level(player_data.iloc[-1], cumulative_data)
        rule_description = rule_descriptions.get(priority_level, "Unknown rule")
        print(f"Rule levels passed as at round {round_num}: Rule Level Satisfied: {priority_level} - {rule_description}")

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
                print(f"Current base: {current_base:.0f}")
                print(f"Average base over last 3 rounds: {avg_base:.0f}\n")
        
        traded_out_players = ["Player1", "Player2"]  # Example players to trade out
        
        # Get lockout and simulation date/time preferences
        apply_lockout = input("Apply lockout restriction? (yes/no): ").strip().lower() == 'yes'
        simulate_datetime = None
        if apply_lockout:
            simulate_datetime = input("Enter simulated date/time (YYYY-MM-DDTHH:MM): ").strip()
        
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
            allowed_positions=allowed_positions,
            simulate_datetime=simulate_datetime,
            apply_lockout=apply_lockout
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
                        print(f"  Average Base: {player['avg_base']:.0f}")
                    else:
                        print(f"- {player['name']} ({player['position']})")
                        print(f"  Price: ${player['price']:,}")
                        print(f"  Current Base Premium: {player['base_premium']}")
                        print(f"  Consecutive Weeks above threshold: {player['consecutive_good_weeks']}")
                
                print(f"Total Price: ${option['total_price']:,}")
                if maximize_base:
                    print(f"Combined Average Base: {option['total_avg_base']:.0f}")
                else:
                    print(f"Combined Base Premium: {option['total_base_premium']}")
                print(f"Salary Remaining: ${option['salary_remaining']:,}")
            
    except FileNotFoundError:
        print("Error: Could not find data file in the current directory")
    except ValueError as e:
        print("Error:", str(e))
    except Exception as e:
        print("An error occurred:", str(e))