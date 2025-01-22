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

    for level in range(1, 15):
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
    
    print(f"Total salary freed up: ${ salary_freed:,}")
    
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
    available_players['priority_level'] = available_players.apply(assign_priority_level, axis=1)

    # Get the positions of the traded out players
    traded_out_positions = [consolidated_data[consolidated_data['Player'] == player]['POS'].values[0] for player in traded_out_players]

    if trade_type == 'likeForLike':
        # Ensure that we only suggest players that match the positions of the traded out players
        available_players = available_players[available_players['POS'].isin(traded_out_positions)]
        
        # Generate combinations of players that match the number of traded out players
        position_count = {pos: traded_out_positions.count(pos) for pos in set(traded_out_positions)}
        
        valid_combinations = []
        
        # Create a list of players grouped by position
        players_by_position = {pos: available_players[available_players['POS'] == pos] for pos in position_count.keys()}
        
        # Generate combinations based on the required counts
        for pos, count in position_count.items():
            if len(players_by_position[pos]) < count:
                return []  # Not enough players to match the required count
            
            # Get combinations of players for this position
            position_combinations = list(combinations(players_by_position[pos].to_dict('records'), count))
            valid_combinations.extend(position_combinations)

        # Now we need to filter valid_combinations to ensure they match the exact number of players
        final_combinations = []
        for combo in valid_combinations:
            if len(combo) == len(traded_out_players):
                final_combinations.append(combo)

        # Limit to max_options
        final_combinations = final_combinations[:max_options]

    elif trade_type == 'positionalSwap':
        # Filter available players based on allowed positions
        if allowed_positions:
            available_players = available_players[available_players['POS'].isin(allowed_positions)]
            if available_players.empty:
                raise ValueError(f"No players found for positions: {', '.join(allowed_positions)}")

    if hybrid_approach:
        # First get the best player based on BPRE rules
        bpre_sorted = available_players.sort_values(
            by=['priority_level', 'avg_bpre', 'Base exceeds price premium'],
            ascending=[True, False, False]
        )
        
        valid_combinations = []
        used_players = set()
        
        # Keep trying combinations until we have enough or run out of players
        while len(valid_combinations) < max_options:
            # Get the highest priority player that hasn't been used and is affordable
            available_first = bpre_sorted[
                (~bpre_sorted['Player'].isin(used_players)) & 
                (bpre_sorted['Price'] <= salary_freed)
            ]
            
            if available_first.empty:
                break
                
            first_player = available_first.iloc[0]
            remaining_salary = salary_freed - first_player['Price']
            
            # Sort remaining players by average base for second player
            base_sorted = available_players[
                (~available_players['Player'].isin(used_players)) & 
                (available_players['Price'] <= remaining_salary) & 
                (available_players.index != first_player.name)
            ].sort_values(by=['avg_base', 'Total base'], ascending=[False, False])
            
            if base_sorted.empty:
                used_players.add(first_player['Player'])
                continue
                
            second_player = base_sorted.iloc[0]
            
            valid_combinations.append({
                'players': [
                    {
                        'name': first_player['Player'],
                        'position': first_player['POS'],
                        'price': first_player['Price'],
                        'total_base': first_player['Total base'],
                        'base_premium': first_player['Base exceeds price premium'],
                        'consecutive_good_weeks': first_player['consecutive_good_weeks'],
                        'priority_level': first_player['priority_level'],
                        'avg_base': first_player['avg_base']
                    },
                    {
                        'name': second_player['Player'],
                        'position': second_player['POS'],
                        'price': second_player['Price'],
                        'total_base': second_player['Total base'],
                        'base_premium': second_player['Base exceeds price premium'],
                        'consecutive_good_weeks': second_player['consecutive_good_weeks'],
                        'priority_level': second_player['priority_level'],
                        'avg_base': second_player['avg_base']
                    }
                ],
                'total_price': first_player['Price'] + second_player['Price'],
                'total_base': first_player['Total base'] + second_player['Total base'],
                'total_base_premium': first_player['Base exceeds price premium'] + second_player['Base exceeds price premium'],
                'salary_remaining': salary_freed - (first_player['Price'] + second_player['Price']),
                'total_avg_base': first_player['avg_base'] + second_player['avg_base']
            })
            
            used_players.add(first_player['Player'])
            used_players.add(second_player['Player'])
            
        return valid_combinations
    
    if maximize_base:
        # Sort players by average base
        available_players['avg_base'] = available_players['Player'].apply(
            lambda x: calculate_average_base(x, consolidated_data)
        )
        available_players = available_players.sort_values(
            by=['avg_base', 'Total base'],
            ascending=[False, False]
        )

        valid_combinations = []
        used_players = set()  # Track used players

        # Keep trying combinations until we have enough or run out of players
        while len(valid_combinations) < max_options:
            # Get the highest average base player that hasn't been used and is affordable
            available_first = available_players[
                (~available_players['Player'].isin(used_players)) & 
                (available_players['Price'] <= salary_freed)
            ]
            
            if available_first.empty:
                break
                
            first_player = available_first.iloc[0]
            remaining_salary = salary_freed - first_player['Price']
            
            # Find second player options
            available_second = available_players[
                (~available_players['Player'].isin(used_players)) & 
                (available_players['Price'] <= remaining_salary) & 
                (available_players.index != first_player.name)
            ]
            
            if available_second.empty:
                used_players.add(first_player['Player'])
                continue
                
            second_player = available_second.iloc[0]
            
            valid_combinations.append({
                'players': [
                    {
                        'name': first_player['Player'],
                        'position': first_player['POS'],
                        'price': first_player['Price'],
                        'total_base': first_player['Total base'],
                        'base_premium': first_player['Base exceeds price premium'],
                        'consecutive_good_weeks': first_player['consecutive_good_weeks'],
                        'avg_base': first_player['avg_base']
                    },
                    {
                        'name': second_player['Player'],
                        'position': second_player['POS'],
                        'price': second_player['Price'],
                        'total_base': second_player['Total base'],
                        'base_premium': second_player['Base exceeds price premium'],
                        'consecutive_good_weeks': second_player['consecutive_good_weeks'],
                        'avg_base': second_player['avg_base']
                    }
                ],
                'total_price': first_player['Price'] + second_player['Price'],
                'total_base': first_player['Total base'] + second_player['Total base'],
                'total_base_premium': first_player['Base exceeds price premium'] + second_player['Base exceeds price premium'],
                'salary_remaining': salary_freed - (first_player['Price'] + second_player['Price']),
                'total_avg_base': first_player['avg_base'] + second_player['avg_base']
            })
            
            # Add both players to used set
            used_players.add(first_player['Player'])
            used_players.add(second_player['Player'])

        return valid_combinations
    else:
        # Original BPRE-based logic
        # Modify sorting based on strategy
        if maximize_base:
            available_players = available_players.sort_values(
                by=['avg_base', 'Total base'],
                ascending=[False, False]
            )
        else:
            # Keep existing BPRE-based sorting
            available_players = available_players.sort_values(
                by=['priority_level', 'avg_bpre', 'Base exceeds price premium'],
                ascending=[True, False, False]
            )
        
        # Print players by rule level with the consolidated_data parameter
        print_players_by_rule_level(available_players, consolidated_data, maximize_base)
        
        valid_combinations = []
        used_players = set()
        all_valid_positions = ['HOK', 'HLF', 'CTR', 'WFB', 'EDG', 'MID']
        pos_combinations = list(combinations(all_valid_positions, num_players_needed))
        
        # Group players by priority level and calculate average BPRE
        priority_groups = {}
        for _, player in available_players.iterrows():
            level = player['priority_level']
            if level not in priority_groups:
                priority_groups[level] = []
            
            avg_bpre = calculate_average_bpre(player['Player'], consolidated_data)
            player_dict = player.to_dict()
            player_dict['avg_bpre'] = avg_bpre
            priority_groups[level].append(player_dict)
        
        # Sort players within each priority group by average BPRE
        for level in priority_groups:
            priority_groups[level].sort(key=lambda x: x['avg_bpre'], reverse=True)
        
        # First try combinations within the same priority level
        for priority_level in sorted(priority_groups.keys()):
            if not priority_groups[priority_level]:
                continue
                
            # Get all valid combinations for this priority level
            all_level_combinations = []
            current_level_players = [p for p in priority_groups[priority_level] 
                                   if p['Player'] not in used_players]
            
            if len(current_level_players) >= num_players_needed:
                current_players_df = pd.DataFrame(current_level_players)
                
                # Generate ALL possible combinations within this priority level
                for players in combinations(current_players_df.to_dict('records'), num_players_needed):
                    total_price = sum(p['Price'] for p in players)
                    if total_price <= salary_freed:
                        combo_avg_bpre = sum(p['avg_bpre'] for p in players)
                        all_level_combinations.append({
                            'priority_level': priority_level,
                            'players': players,
                            'total_price': total_price,
                            'combo_avg_bpre': combo_avg_bpre,
                            'total_base_premium': sum(p['Base exceeds price premium'] for p in players)
                        })
            
            # Sort combinations by average BPRE
            all_level_combinations.sort(key=lambda x: x['combo_avg_bpre'], reverse=True)
            
            # Add ALL valid combinations from this priority level
            for combo in all_level_combinations:
                if len(valid_combinations) >= max_options:
                    break
                    
                # Skip if any player in this combination has been used
                if any(p['Player'] in used_players for p in combo['players']):
                    continue
                    
                valid_combinations.append({
                    'priority_level': combo['priority_level'],
                    'players': [
                        {
                            'name': p['Player'],
                            'position': p['POS'],
                            'price': p['Price'],
                            'total_base': p['Total base'],
                            'base_premium': p['Base exceeds price premium'],
                            'consecutive_good_weeks': p['consecutive_good_weeks'],
                            'priority_level': p['priority_level']
                        } for p in combo['players']
                    ],
                    'total_price': combo['total_price'],
                    'total_base': sum(p['Total base'] for p in combo['players']),
                    'total_base_premium': combo['total_base_premium'],
                    'salary_remaining': salary_freed - combo['total_price'],
                    'combo_avg_bpre': combo['combo_avg_bpre']
                })
                
                # Update used_players after adding a combination
                for player in combo['players']:
                    used_players.add(player['Player'])

        # If we still need more combinations, try mixing priority levels
        if len(valid_combinations) < max_options:
            for priority_level in sorted(priority_groups.keys()):
                current_and_higher_priority_players = []
                # Include all players of current priority level and higher
                for level in sorted(priority_groups.keys()):
                    if level <= priority_level:
                        current_and_higher_priority_players.extend(priority_groups[level])
                
                # Filter out already used players
                current_and_higher_priority_players = [
                    p for p in current_and_higher_priority_players 
                    if p['Player'] not in used_players
                ]
                
                if not current_and_higher_priority_players:
                    continue
                    
                current_players_df = pd.DataFrame(current_and_higher_priority_players)
                
                for pos_combo in pos_combinations:
                    eligible_players = current_players_df[current_players_df['POS'].isin(pos_combo)]
                    
                    for players in combinations(eligible_players.to_dict('records'), num_players_needed):
                        if any(p['Player'] in used_players for p in players):
                            continue
                            
                        total_price = sum(p['Price'] for p in players)
                        if total_price <= salary_freed:
                            combo_avg_bpre = sum(p['avg_bpre'] for p in players)
                            combo_priority = max(p['priority_level'] for p in players)
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
                                'salary_remaining': salary_freed - total_price,
                                'combo_avg_bpre': combo_avg_bpre
                            })
                            
                            for p in players:
                                used_players.add(p['Player'])
                            
                            if len(valid_combinations) >= max_options:
                                break
                
                    if len(valid_combinations) >= max_options:
                        break
                
                if len(valid_combinations) >= max_options:
                    break
        
        # Modify the sorting of valid_combinations based on strategy
        if maximize_base:
            valid_combinations.sort(key=lambda x: (
                sum(calculate_average_base(p['name'], consolidated_data) for p in x['players']),
                -x['total_base']
            ))
        else:
            # Keep existing BPRE-based sorting
            valid_combinations.sort(key=lambda x: (
                x['priority_level'], 
                -x['combo_avg_bpre'],
                -x['total_base_premium']
            ))
        
        return valid_combinations[:max_options]

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
        
        
        
        print(f"\nCalculating trade options for trading out: {', '.join(traded_players)}")
        print(f"Strategy: {'Maximizing base stats' if maximize_base else 'Maximizing value (BPRE)' if not hybrid_approach else 'Hybrid approach (BPRE + Base stats)'}")
        if allowed_positions:
            print(f"Considering only positions: {', '.join(allowed_positions)}")
        else:
            print("Considering all positions")
        
        options = calculate_trade_options(
            consolidated_data,
            traded_players,
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
