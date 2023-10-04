# GamedayBot Discord Bot
[Invite to your Discord Server](https://discord.com/oauth2/authorize?client_id=1067222434845053008&permissions=2147543040&scope=bot)

# Examples
![nba_nextgame](https://user-images.githubusercontent.com/70344759/236567369-ce1850ad-434d-4d98-92a5-1278d1470b4d.PNG)
![nba reminder](https://user-images.githubusercontent.com/70344759/236567374-1b5d848a-36cf-449c-86cc-0db6f66eb2bb.PNG)
![nhl set reminders](https://user-images.githubusercontent.com/70344759/236569047-8770bab9-ef1a-4861-949f-fd0cebb73693.PNG)

# Description
Discord Bot used to check upcoming NBA, NFL, and NHL games as well as set reminders for user selected teams. Bot has the following slash commands:
- nba_nextgame: Returns a graphic of selected NBA team upcoming game.
- nba_remindme: User can set a reminder for team(s) in the NBA.
- nba_remove_reminders: User can remove reminders for any team in NBA.
- nfl_nextgame: Returns a graphic of selected NFL team upcoming game.
- nfl_remindme: User can set a reminder for team(s) in the NFL.
- nfl_remove_reminders: User can remove reminders for any team in NFL.
- nhl_nextgame: Returns a graphic of selected NHL team upcoming game.
- nhl_remindme: User can set a reminder for team(s) in the NHL.
- nhl_remove_reminders: User can remove reminders for any team in NHL.
- remove_all_reminders: Remove reminders for any or all of the leagues at once.

# Future Improvements:
- Add better database failure recovery
- Add set_timezone command for user
- Make reminder more clear
- Add cogs
- Add more sports (currently supported: NBA, NHL, NFL)
- More testing

## Technologies Used

### Backend
- **Python**: Version 3.11
- **psycopg2~=2.9.5**: A PostgreSQL adapter for Python.
- **PostgreSQL**: A powerful open-source relational database system.
- **cron**: Used to schedule python scripts to obtain upcoming NBA, NFL, and NHL games and set reminders in the database.

### Hosting
- **Raspberry Pi 3**: Used for hosting the application.

### Libraries
- **discord~=2.1.0**: Used for Discord integration of slash commands and setting and receiving reminder messages.
- **DateTime~=5.0**: Used to format dates from the different APIs into one 
- **Pillow~=9.4.0**: Used to create reminder graphics that are messaged to user.
- **python-dateutil~=2.8.2**: Used to parse and convert all dates to a specific format.
- **requests~=2.28.2**: Used for making HTTP requests to fetch data from NBA, NFL, and NHL APIs.
