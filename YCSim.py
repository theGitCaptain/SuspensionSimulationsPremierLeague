import random
import mysql.connector

GAMES_IN_SEASON = 38
SEASON = '2024/25'

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
    SELECT g.yellow_cards, g.minutes
    FROM gwdata g
    JOIN fixtures f
    ON g.fixture_id = f.fixture_id
    WHERE player_id = %s
    ORDER BY f.date DESC;
    """

    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (player_id,))
    game_info = cursor.fetchall()
    cursor.close()

    return game_info

def simulate_yellows(suspension_count, team_games_played, current_yellows, yc_prob, games_in_season):
    
    yellows = current_yellows
    remaining_games = games_in_season - team_games_played

    for game in range(1, remaining_games + 1):
        print(f"Game {game} (Gameweek {team_games_played + 1}):")
        print(f"Current Yellows: {yellows}")

        if suspension_count > 0:
            suspended = True
            suspension_count -= 1
            received_yellow = "Did not play due to suspension"
        else:
            suspended = False
            yellow_card = random.random() < yc_prob

            if yellow_card:
                received_yellow = True
                yellows += 1

                if yellows == 5 and team_games_played <= 19:
                    suspension_count = 1
                elif yellows == 10 and team_games_played <= 32:
                    suspension_count = 2
                elif yellows == 15:
                    suspension_count = 3
                elif yellows == 20:
                    suspension_count = games_in_season
            else:
                received_yellow = False

        team_games_played += 1

        print(f"Suspended: {suspended}")
        print()
        print(f"Received yellow this game: {received_yellow}")
        print()
        print()
        print()

def main():
    connection = connect_to_db()

    team_ids = fetch_teams(connection)
    for team_id in team_ids[:1]:
        team_games_played = find_teams_games_played(connection, team_id)

        player_ids = fetch_players_from_team(connection, team_id)

        for player_id in player_ids[:10]:
            print(f"Player {player_id}:")
            gwdata = fetch_players_gwdata(connection, player_id)
            for gw in gwdata:
                print(gw)
        



    # simulate_yellows(0, 9, 4, 0.44, GAMES_IN_SEASON)
    
    connection.close()

if __name__ == "__main__":
    main()