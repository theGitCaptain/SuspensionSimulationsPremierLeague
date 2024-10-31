import mysql.connector
import numpy as np

SIMULATIONS_PER_COMBINATION = 1000

GAMES_IN_SEASON = 38
SEASON = '2024/25'

TIME_DECAY = 0.85 # For benched weights

HOST = ''
USER = ''
PASSWORD = ''
DATABASE = ''

def connect_to_db():
    connection = mysql.connector.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE
    )
    return connection

def calculate_weights(decay, amount):
    weights = [decay ** i for i in range(amount)]
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]
    return normalized_weights

def fetch_teams(connection):
    query = """
    SELECT DISTINCT(home_team_id) AS team_ids FROM fixtures WHERE season = %s
    UNION
    SELECT DISTINCT(away_team_id) AS team_Ids FROM fixtures WHERE season = %s
    """

    cursor = connection.cursor()
    cursor.execute(query, (SEASON, SEASON))
    team_ids = cursor.fetchall()
    cursor.close()

    team_ids = [team_id[0] for team_id in team_ids]

    return team_ids

def find_teams_games_played(connection, team_id):
    query = """
    SELECT COUNT(*) FROM fixtures
    WHERE season = %s
    AND played = 1
    AND (home_team_id = %s OR away_team_id = %s);
    """

    cursor = connection.cursor()
    cursor.execute(query, (SEASON, team_id, team_id))
    games_played_team = cursor.fetchone()[0]
    cursor.close()

    return games_played_team

def fetch_players_from_team(connection, team_id):
    query = """
    SELECT player_id
    FROM players
    WHERE team_id = %s
    AND status != 'u'
    """

    cursor = connection.cursor()
    cursor.execute(query, (team_id,))
    player_ids = cursor.fetchall()
    cursor.close()

    player_ids = [player_id[0] for player_id in player_ids]

    return player_ids

def fetch_players_gwdata(connection, player_id):
    query = """
    SELECT g.yellow_cards, g.minutes, g.benched
    FROM gwdata g
    JOIN fixtures f
    ON g.fixture_id = f.fixture_id
    WHERE player_id = %s
    ORDER BY f.date ASC;
    """

    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (player_id,))
    game_info = cursor.fetchall()
    cursor.close()

    return game_info

def yc_prob_and_suspension_info(gwdata, team_games_played):

    current_yellows = 0
    games_played = 0
    suspension_count = 0

    total_games = len(gwdata)

    # The weights are initially ordered from highest to lowest, but we loop through games from oldest to newest
    bench_weights = calculate_weights(TIME_DECAY, total_games)

    bench_weights.reverse()
    benched_chance = 0

    for i, gw in enumerate(gwdata):
        yellow_card = gw['yellow_cards']
        minutes = gw['minutes']
        benched = gw['benched']

        if suspension_count > 0:
            suspension_count -= 1

        if minutes > 0:
            games_played += 1

        # Calculating the chance of the player being benched where we weigh more recent games more
        if benched == True:
            benched_chance += benched * bench_weights[i]
    
        current_yellows += yellow_card

        if yellow_card:
            if current_yellows == 5 and team_games_played <= 19:
                suspension_count = 1
            elif current_yellows == 10 and team_games_played <= 32:
                suspension_count = 2
            elif current_yellows == 15:
                suspension_count = 3
            elif current_yellows == 20:
                # Uncertain what happens at this point, but it will be a suspension. Has never happened though
                suspension_count = GAMES_IN_SEASON

    # Minimum cap at 5 to avoid getting 100% if a player has a very small sample size
    yc_prob_raw = current_yellows / max(5, games_played)

    play_chance = 1 - benched_chance

    yc_prob = round(yc_prob_raw * play_chance, 3)

    return suspension_count, current_yellows, yc_prob

def simulate_yellows(suspension_count, team_games_played, current_yellows, yc_prob, games_in_season):
    yellows = current_yellows
    remaining_games = games_in_season - team_games_played
    
    game_suspensions = np.zeros(remaining_games)

    for game in range(remaining_games):
        if suspension_count > 0:
            suspension_count -= 1
            game_suspensions[game] += 1
        else:
            yellow_card = np.random.rand() < yc_prob
            if yellow_card:
                yellows += 1
                if yellows == 5 and (team_games_played + game + 1) <= 19:
                    suspension_count = 1
                elif yellows == 10 and (team_games_played + game + 1) <= 32:
                    suspension_count = 2
                elif yellows == 15:
                    suspension_count = 3
                elif yellows == 20:
                    suspension_count = games_in_season

    return game_suspensions

def insert_into_suspensions_table(connection, suspension_count, team_games_played, current_yellows, yc_prob, game_no, suspensions, simulations):
    query = """
    INSERT INTO suspension_chances (suspension_count, team_games_played, current_yellows, yc_prob, game_no, times_suspended, simulations)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        times_suspended = times_suspended + VALUES(times_suspended),
        simulations = simulations + VALUES(simulations)
    """
    
    cursor = connection.cursor()
    cursor.execute(query, (suspension_count, team_games_played, current_yellows, yc_prob, game_no, suspensions, simulations))
    connection.commit()
    cursor.close()

def main():
    connection = connect_to_db()
    unique_combinations = set()

    team_ids = fetch_teams(connection)
    for team_id in team_ids:
        team_games_played = find_teams_games_played(connection, team_id)
        player_ids = fetch_players_from_team(connection, team_id)

        for player_id in player_ids:
            gwdata = fetch_players_gwdata(connection, player_id)
            suspension_count, current_yellows, yc_prob= yc_prob_and_suspension_info(gwdata, team_games_played)
            
            unique_combinations.add((suspension_count, current_yellows, yc_prob, team_games_played))

    for combination in unique_combinations:
        suspension_count, current_yellows, yc_prob, team_games_played = combination
        remaining_games = GAMES_IN_SEASON - team_games_played
        
        cumulative_suspensions = {game_no: 0 for game_no in range(1, remaining_games + 1)}
        
        for _ in range(SIMULATIONS_PER_COMBINATION):    
            game_suspensions = simulate_yellows(suspension_count, team_games_played, current_yellows, yc_prob, GAMES_IN_SEASON)
            
            for game_no, suspensions in enumerate(game_suspensions, start=1):
                cumulative_suspensions[game_no] += suspensions

        # Insert results into the database
        for game_no, suspensions in cumulative_suspensions.items():
            insert_into_suspensions_table(connection, suspension_count, team_games_played, current_yellows, yc_prob, game_no, suspensions, SIMULATIONS_PER_COMBINATION)
        
        print(f"Inserted into table for combination: {combination}")

    
    connection.close()

if __name__ == "__main__":
    main()