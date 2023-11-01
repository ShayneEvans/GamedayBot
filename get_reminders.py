import psycopg2
import bot
from datetime import datetime
import os

#This function is executed every 12 hours via cron job on Ubuntu
def set_reminders_every_2_hours():
    conn_reminders = psycopg2.connect(
        database= os.environ.get('GamedayBot_database'),
        user= os.environ.get('GamedayBot_user'),
        password= os.environ.get('GamedayBot_password'),
        host= os.environ.get('GamedayBot_host'),
        port= os.environ.get('GamedayBot_port')
    )
    cur_reminders = conn_reminders.cursor()

    delete_old_nba_games_query = "DELETE FROM nba_games WHERE start_time <= NOW()"
    delete_old_nfl_games_query = "DELETE FROM nfl_games WHERE start_time <= NOW()"
    delete_old_nhl_games_query = "DELETE FROM nhl_games WHERE start_time <= NOW()"
    delete_old_cs2_games_query = "DELETE FROM cs2_games WHERE start_time <= NOW()"
    cur_reminders.execute(delete_old_nba_games_query)
    cur_reminders.execute(delete_old_nfl_games_query)
    cur_reminders.execute(delete_old_nhl_games_query)
    cur_reminders.execute(delete_old_cs2_games_query)
    conn_reminders.commit()

    id_query = "SELECT * FROM users"
    cur_reminders.execute(id_query)
    id_query_result = cur_reminders.fetchall()

    # Getting all upcoming games for each league
    nba_upcoming_games = "SELECT * FROM nba_games WHERE start_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
    nfl_upcoming_games = "SELECT * FROM nfl_games WHERE start_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
    nhl_upcoming_games = "SELECT * FROM nhl_games WHERE start_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
    cs2_upcoming_games = "SELECT * FROM cs2_games WHERE start_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
    cur_reminders.execute(nba_upcoming_games)
    nba_upcoming_games_query_result = cur_reminders.fetchall()
    cur_reminders.execute(nfl_upcoming_games)
    nfl_upcoming_games_query_result = cur_reminders.fetchall()
    cur_reminders.execute(nhl_upcoming_games)
    nhl_upcoming_games_query_result = cur_reminders.fetchall()
    cur_reminders.execute(cs2_upcoming_games)
    cs2_upcoming_games_query_result = cur_reminders.fetchall()

    # Goes through each user and
    for user in id_query_result:
        # These will not be None if user follows any teams will be updated in code below
        followed_nba_teams = None
        followed_nfl_teams = None
        followed_nhl_teams = None
        followed_cs2_teams = None

        if user[1] is not None:
            followed_nba_teams = list(user[1].split(','))

        if user[3] is not None:
            followed_nfl_teams = list(user[3].split(','))

        if user[5] is not None:
            followed_nhl_teams = list(user[5].split(','))

        if user[7] is not None:
            followed_cs2_teams = list(user[7].split(','))

        # If user follows nba teams
        if followed_nba_teams is not None:
            for game in nba_upcoming_games_query_result:
                # If home team or visiting team in followed nba teams insert a reminder for that game, duplicate games are avoided with a check for the count
                if game[1] in followed_nba_teams or game[2] in followed_nba_teams:
                    game_remind_time_dt, game_remind_time_string = bot.get_game_reminder_time(game[0], user[2])
                    insert_statement = "INSERT INTO reminders (user_id, remind_time, visiting_team, home_team, league, minutes_from_start_time) VALUES (%s, %s, %s, %s, %s, %s)"
                    values = (user[0], game_remind_time_string, game[1], game[2], 'NBA', user[2])
                    # Checks if a reminder has been set for this upcoming game, an insert will not take place if true
                    check_if_exists = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
                    cur_reminders.execute(check_if_exists, (user[0], game[1], game[2],))
                    if cur_reminders.fetchone()[0] == 0:
                        check_if_exists_swapped = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL" 
                        cur_reminders.execute(check_if_exists_swapped, (user[0], game[2], game[1],))
                        if cur_reminders.fetchone()[0] == 0:
                            date_now = datetime.now()
                            if(date_now < game_remind_time_dt):
                                cur_reminders.execute(insert_statement, values)
                                conn_reminders.commit()
                                print(f'NBA Games added to reminders')
                            else:
                                print("Insert failed, duplicate entry or update to remind time needed")

        # If user follows nfl teams
        if followed_nfl_teams is not None:
            for game in nfl_upcoming_games_query_result:
                # If home team or visiting team in followed nfl teams insert a reminder for that game, duplicate games are avoided with a check for the count
                if game[1] in followed_nfl_teams or game[2] in followed_nfl_teams:
                    game_remind_time_dt, game_remind_time_string = bot.get_game_reminder_time(game[0], user[4])
                    insert_statement = "INSERT INTO reminders (user_id, remind_time, visiting_team, home_team, league, minutes_from_start_time) VALUES (%s, %s, %s, %s, %s, %s)"
                    values = (user[0], game_remind_time_string, game[1], game[2], 'NFL', user[4])
                    #Checks if a reminder has been set for this upcoming game, an insert will not take place if true
                    check_if_exists = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
                    cur_reminders.execute(check_if_exists, (user[0], game[1], game[2],))
                    if cur_reminders.fetchone()[0] == 0:
                        check_if_exists_swapped = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
                        cur_reminders.execute(check_if_exists_swapped, (user[0], game[2], game[1],))
                        if cur_reminders.fetchone()[0] == 0:
                            date_now = datetime.now()
                            if(date_now < game_remind_time_dt):
                                cur_reminders.execute(insert_statement, values)
                                conn_reminders.commit()
                                print(f'NFL Games added to reminders')
                            else:
                                print("Insert failed, duplicate entry or update to remind time needed")

        # If user already follows nhl teams
        if followed_nhl_teams is not None:
            for game in nhl_upcoming_games_query_result:
                # If home team or visiting team in followed nhl teams insert a reminder for that game, duplicate games are avoided with a check for the count
                if game[1] in followed_nhl_teams or game[2] in followed_nhl_teams:
                    game_remind_time_dt, game_remind_time_string = bot.get_game_reminder_time(game[0], user[6])
                    insert_statement = "INSERT INTO reminders (user_id, remind_time, visiting_team, home_team, league, minutes_from_start_time) VALUES (%s, %s, %s, %s, %s, %s)"
                    values = (user[0], game_remind_time_string, game[1], game[2], 'NHL', user[6])
                    #Checks if a reminder has been set for this upcoming game, an insert will not take place if true
                    check_if_exists = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
                    cur_reminders.execute(check_if_exists, (user[0], game[1], game[2],))
                    if cur_reminders.fetchone()[0] == 0:
                        check_if_exists_swapped = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
                        cur_reminders.execute(check_if_exists_swapped, (user[0], game[2], game[1],))
                        if cur_reminders.fetchone()[0] == 0:
                            date_now = datetime.now()
                            if(date_now < game_remind_time_dt):
                                cur_reminders.execute(insert_statement, values)
                                conn_reminders.commit()
                                print(f'NHL Games added to reminders')
                            else:
                                print("Insert failed, duplicate entry or update to remind time needed")

        # If user already follows cs2 teams
        if followed_cs2_teams is not None:
            for game in cs2_upcoming_games_query_result:
                # If home team or visiting team in followed cs2 teams insert a reminder for that game, duplicate games are avoided with a check for the count
                if game[1] in followed_cs2_teams or game[2] in followed_cs2_teams:
                    game_remind_time_dt, game_remind_time_string = bot.get_game_reminder_time(game[0], user[8])
                    insert_statement = "INSERT INTO reminders (user_id, remind_time, visiting_team, home_team, league, minutes_from_start_time) VALUES (%s, %s, %s, %s, %s, %s)"
                    values = (user[0], game_remind_time_string, game[1], game[2], 'cs2', user[8])
                    #Checks if a reminder has been set for this upcoming game, an insert will not take place if true
                    check_if_exists = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
                    cur_reminders.execute(check_if_exists, (user[0], game[1], game[2],))
                    if cur_reminders.fetchone()[0] == 0:
                        check_if_exists_swapped = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
                        cur_reminders.execute(check_if_exists_swapped, (user[0], game[2], game[1],))
                        if cur_reminders.fetchone()[0] == 0:
                            date_now = datetime.now()
                            if(date_now < game_remind_time_dt):
                                cur_reminders.execute(insert_statement, values)
                                conn_reminders.commit()
                                print(f'CS2 Games added to reminders')
                            else:
                                print("Insert failed, duplicate entry or update to remind time needed")


    cur_reminders.close()
    conn_reminders.close()

set_reminders_every_2_hours()