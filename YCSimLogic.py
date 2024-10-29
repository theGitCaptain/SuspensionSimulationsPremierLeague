import random

GAMES_IN_SEASON = 38

suspension_served = False
yellows = 4
yc_prob = 0.44
team_games_played = 9
remaining_games = GAMES_IN_SEASON - team_games_played

if yellows == 5 and team_games_played <= 19 and suspension_served == False:
    suspension_count = 1
elif yellows == 10 and team_games_played <= 32 and suspension_served == False:
    suspension_count = 2
elif yellows == 15 and suspension_served == False:
    suspension_count = 3
elif yellows == 20 and suspension_served == False:
    suspension_count = GAMES_IN_SEASON
else:
    suspension_count = 0

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
                suspension_count = GAMES_IN_SEASON
        else:
            received_yellow = False

    team_games_played += 1

    print(f"Suspended: {suspended}")
    print()
    print(f"Received yellow this game: {received_yellow}")
    print()
    print()
    print()