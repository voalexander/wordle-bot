from turtle import color
import configuration
import data
import discord
import re
import random
import math
import matplotlib.pyplot as plt
import numpy as np
import asyncio
import aiocron
import datetime
from datetime import date

intents = discord.Intents.default()
intents.members = True
intents.messages = True
client = discord.Client(intents=intents)

database = data.Client()

compliments = ["nice", "good stuff", "legend", "good shit", "excellent"]
insults = ["nice.", "lol", "LOSER", "lmao", ":^) nice one", "havin a rough day?"]
roleColors = {
    6 :   discord.Color.from_rgb(43, 28, 26), # poo brown
    5 :   discord.Color.from_rgb(73, 48, 45), # brighter poo brown
    4.5 : discord.Color.from_rgb(155, 103, 60), # just brown
    4.0 : discord.Color.dark_blue(),
    3.5 : discord.Color.red(),
    3.0 : discord.Color.gold(),
    2.5 : discord.Color.teal(),
    0 : discord.Color.magenta()
}

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    nightly.start()

@client.event
async def on_guild_join(guild):
    print("New server.\nGetting message history")
    await get_score_history(guild)
    await update_all_roles(guild)
    sort_scores(guild)

@client.event
async def on_message(message):

    if message.author == client.user:
        return

    if message.content == "!wb members":
        await message.channel.send(message.guild.members)

    if message.content == "!wb me":
        stats = database.get_player_stats(message.author.id)
        player = message.author.nick if message.author.nick is not None else message.author.name
        stats_string = f"{player}'s average number of guesses is {round(stats[0], 4)}. They've played {stats[1]} " \
                       f"games and won {stats[2]} games, making their win rate {round(stats[3] * 100, 4)}%."
        await message.channel.send(stats_string)
        await message.channel.send(file=getGraph(message.author.id))

    if message.content == "!wb average":
        await message.channel.send(rankings_by_average(message, 10))

    if message.content == "!wb rate":
        await message.channel.send(rankings_by_win_rate(message, 10))

    if message.content == "!wb games":
        await message.channel.send(rankings_by_games_played(message, 10))

    if message.content == "!wb deletemydata":
        await message.channel.send("I'm lazy to update this. Your data and shameful history is mine forever.")

    if message.content == "!wb updateData":
        updateCnt = await get_score_history(message.guild)
        await message.channel.send("Scanned history.\n" + str(updateCnt) + " scores added.")
        if updateCnt != 0:
            await update_all_roles(message.guild)
            await message.channel.send("Updated roles.")
        numSorted = sort_scores(message.guild)
        await message.channel.send("Sorted " + str(numSorted) + " records")
    
    if message.content == "!wb updateRoles":
        await update_all_roles(message.guild)
        await message.channel.send("Updated roles.")

    if message.content == "!wb help" or message.content == "!wb":
        help_string = "`!wb help` to see this message\n" \
                      "`!wb me` to see your stats\n" \
                      "`!wb average` to see server rankings by average number of guesses\n" \
                      "`!wb rate` to see server rankings by win rate\n" \
                      "`!wb games` to see server rankings by games played\n" \
                      "`!wb deletemydata` to remove all your scores from wordle-bot (warning: this is not reversible!)"
        await message.channel.send(help_string)

    if re.match(r"Wordle [0-9]+ [1-6|X]/6", message.content) is not None:
        # extract the Wordle number from message
        wordle = message.content.splitlines()[0].split(" ")[1]
        # extract the score from message
        score = message.content.splitlines()[0].split(" ")[2][0]
        if score == "X":
            score = "7"
        score = int(score)

        result = database.add_score(message.author.id, wordle, score)
        if result:
            scores = database.get_player_stats(message.author.id)
            await update_role(message.guild, message.author, scores)

        if not result:
            await message.channel.send("You've already submitted a score for this Wordle.")
            return

        if score == 1:
            await message.channel.send("...sus")
        elif score == 2:
            await message.channel.send(compliments[random.randint(0,len(compliments)-1)])
        elif score == 6:
            await message.channel.send(insults[random.randint(0,len(insults)-1)])
        elif score not in [3,4,5]:
            await message.channel.send(insults[random.randint(0,len(insults)-1)])

async def get_score_history(guild) -> int:
    scoreHistCnt = 0
    for channel in guild.text_channels:
        async for message in channel.history(limit=10000):
            if re.match(r"Wordle [0-9]+ [1-6|X]/6", message.content) is not None:
                # extract the Wordle number from message
                wordle = message.content.splitlines()[0].split(" ")[1]
                # extract the score from message
                score = message.content.splitlines()[0].split(" ")[2][0]
                if score == "X":
                    score = "7"
                score = int(score)

                if database.add_score(message.author.id, wordle, score):
                    print("Added {0};{1} for {2}".format(wordle, score, message.author))
                    scoreHistCnt += 1
    return scoreHistCnt

def sort_scores(guild):
    numSorted = 0
    for member in guild.members:
        numSorted += database.sortScores(member.id)
    return numSorted

def avgToTier(avg):
    if avg == 7:
        avg = 6
    prev = 0
    for key in reversed(roleColors):
        if avg <= key and avg >= prev:
            return key
        prev = key
    return 6

def getGraph(id):
    z = np.linspace(1,6,100)
    stats = database.findPlayer(id)
    x = []
    rawY = []
    keys = list(stats["scores"].keys())
    cnt=0
    for key in keys:
        rawY.append(stats["scores"][key])
        x.append(cnt)
        cnt+=1
    x = np.array(x)
    rawY = np.array(rawY)
    y = []
    total = 0
    for yVal in rawY:
        total += yVal
        if len(y) != 0:
            y.append(total / (len(y) + 1))
        else:
            y.append(total)
    y = np.array(y)
    plt.style.use('dark_background')
    plt.plot(x,y)
    plt.title("Average Over " + str(stats["count"]) + " Games")
    plt.grid(True)
    plt.ylabel("Average Number of Guesses")
    plt.xlabel("Number of Games")
    plt.savefig("tmp.png")
    plt.clf()
    return discord.File(open("tmp.png", "rb"))

async def update_role(guild, member, scores):
    # Remove existing roles
    for role in member.roles:
        if len(role.members) == 1:
            try:
                await role.delete()
            except:
                pass
    await member.edit(roles=[])

    existRoles = await guild.fetch_roles()
    existRolesKey = {}
    for role in existRoles:
        existRolesKey[role.name]=role
    avgTitle = "Avg: " + str(round_down(scores[0]))
    gamesTitle = "Games: " + str(scores[1])
    wrTitle = "Winrate: " + str(round(scores[3] * 100, 2)) + "%"

    if avgTitle not in existRolesKey:
        newRoleAvg = await guild.create_role(name=avgTitle, color=roleColors[avgToTier(scores[0])])
    else:
        newRoleAvg = existRolesKey[avgTitle]

    if gamesTitle not in existRolesKey:
        newRoleGames = await guild.create_role(name=gamesTitle)
    else:
        newRoleGames = existRolesKey[gamesTitle]

    if wrTitle not in existRolesKey:
        newRoleWR = await guild.create_role(name=wrTitle)
    else:
        newRoleWR = existRolesKey[wrTitle]

    await member.edit(roles=[newRoleAvg, newRoleGames, newRoleWR])
    await updateInactiveMember(guild, member)

    return

async def update_all_roles(guild) -> None:
    scores = []
    for member in guild.members:
        score = database.get_player_stats(member.id)
        if score[0] == 0:
            continue
        scores.append((member.id, score))
        await update_role(guild, member, score)
    return

@aiocron.crontab('0 */24 * * *')
async def nightly():
    print(date.today())
    for guild in client.guilds:
        existRoles = await guild.fetch_roles()
        existRolesKey = {}
        inactiveRoleName = "Inactive Loser"
        for role in existRoles:
            existRolesKey[role.name]=role.id
        if inactiveRoleName not in existRolesKey:
            inactiveRole = await guild.create_role(name=inactiveRoleName, color=discord.Color.from_rgb(74, 65, 42))
        else:
            inactiveRole = guild.get_role(existRolesKey[inactiveRoleName])
        for member in guild.members:
            data = database.get_player_stats(member.id)
            if data[4] is not None:
                await updateInactiveMember(guild, member)

    return

async def updateInactiveMember(guild, member):
    existRoles = await guild.fetch_roles()
    existRolesKey = {}
    inactiveRoleName = "Inactive Loser"
    for role in existRoles:
        existRolesKey[role.name]=role.id
    if inactiveRoleName not in existRolesKey:
        inactiveRole = await guild.create_role(name=inactiveRoleName, color=discord.Color.from_rgb(74, 65, 42))
    else:
        inactiveRole = guild.get_role(existRolesKey[inactiveRoleName])
    if isMemberActive(member)==False:
        if inactiveRole not in member.roles:
            allRoles = await guild.fetch_roles()
            numRoles = len(allRoles)
            await inactiveRole.edit(position=numRoles-2)
            await member.add_roles(inactiveRole)
            print(member.name + " is inactive")
    else:
        if inactiveRole in member.roles:
            await member.remove_roles(inactiveRole)
            print(member.name + " is no longer inactive")

def isMemberActive(member) -> bool:
    currWordle = getCurrentWordle()
    data = database.get_player_stats(member.id)
    if next(reversed(data[4])) >= currWordle:
        return True
    return ((getCurrentWordle() - next(reversed(data[4]))) <= 4)

def getCurrentWordle() -> int:
    return int((date.today()-date(2021, 6, 19)).days)

def rankings_by_average(message, n: int) -> str:
    """Return string formatted leaderboard ordered by average guesses where message is the message data from the
    triggering Discord message and n is the max number of rankings to return.
    """
    members = [(member if member is not None else member.name, member.id)
               for member in message.guild.members]
    scores = []
    scoresInactive = []
    for member in message.guild.members:
        data = database.get_player_stats(member.id)
        if data[4] is not None:
            if isMemberActive(member):
                score = database.get_player_stats(member.id)
                if score[0] == 0:
                    continue
                scores.append((member.name, score))
            else:
                score = database.get_player_stats(member.id)
                if score[0] == 0:
                    continue
                scoresInactive.append((member.name, score))
    scores.sort(key=lambda x: x[1][0])
    scoresInactive.sort(key=lambda x: x[1][0])

    scoreboard=""
    if len(scores) > 0:
        scoreboard += "Rankings by average number of guesses:"
        i = 0
        while i != len(scores):
            scoreboard += f"\n{i + 1}. {scores[i][0]} ({round(scores[i][1][0], 4)})"
            i += 1
    if len(scoresInactive) > 0:
        scoreboard += "Inactive loser average number of guesses rankings:"
        i = 0
        while i != len(scoresInactive):
            scoreboard += f"\n{i + 1}. {scoresInactive[i][0]} ({round(scoresInactive[i][1][0], 4)})"
            i += 1
    

    return scoreboard

def rankings_by_win_rate(message, n: int) -> str:
    """Return string formatted leaderboard ordered by win rate where message is the message data from the
    triggering Discord message and n is the max number of rankings to return.
    """
    members = [(member if member is not None else member.name, member.id)
               for member in message.guild.members]
    scores = []
    scoresInactive = []
    for member in message.guild.members:
        data = database.get_player_stats(member.id)
        if data[4] is not None:
            if isMemberActive(member):
                score = database.get_player_stats(member.id)
                if score[0] == 0:
                    continue
                scores.append((member.name, score))
            else:
                score = database.get_player_stats(member.id)
                if score[0] == 0:
                    continue
                scoresInactive.append((member.name, score))
    scores.sort(key=lambda x: x[1][3], reverse=True)
    scoresInactive.sort(key=lambda x: x[1][3], reverse=True)

    scoreboard=""
    if len(scores) > 0:
        scoreboard += "Rankings by win rate:"
        i = 0
        while i != len(scores):
            scoreboard += f"\n{i + 1}. {scores[i][0]} ({round(scores[i][1][3] * 100, 4)}%)"
            i += 1
    if len(scoresInactive) > 0:
        scoreboard += "Inactive loser win rate rankings:"
        i = 0
        while i != len(scoresInactive):
            scoreboard += f"\n{i + 1}. {scoresInactive[i][0]} ({round(scoresInactive[i][1][3] * 100, 4)}%)"
            i += 1
    return scoreboard

def rankings_by_games_played(message, n: int) -> str:
    """Return string formatted leaderboard ordered by number of games played where message is the message data from the
    triggering Discord message and n is the max number of rankings to return.
    """
    members = [(member if member is not None else member.name, member.id)
               for member in message.guild.members]
    scores = []
    scoresInactive = []
    for member in message.guild.members:
        data = database.get_player_stats(member.id)
        if data[4] is not None:
            if isMemberActive(member):
                score = database.get_player_stats(member.id)
                if score[0] == 0:
                    continue
                scores.append((member.name, score))
            else:
                score = database.get_player_stats(member.id)
                if score[0] == 0:
                    continue
                scoresInactive.append((member.name, score))
    scores.sort(key=lambda x: x[1][1], reverse=True)
    scoresInactive.sort(key=lambda x: x[1][1], reverse=True)

    scoreboard=""
    if len(scores) > 0:
        scoreboard += "Rankings by games played:"
        i = 0
        while i != len(scores):
            scoreboard += f"\n{i + 1}. {scores[i][0]} ({scores[i][1][1]})"
            i += 1
    if len(scoresInactive) > 0:
        scoreboard += "Inactive loser games played rankings:"
        i = 0
        while i != len(scoresInactive):
            scoreboard += f"\n{i + 1}. {scoresInactive[i][0]} ({scoresInactive[i][1][1]})"
            i += 1

    return scoreboard

def round_down(number:float, decimals:int=2):
    """
    Returns a value rounded down to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.floor(number)

    factor = 10 ** decimals
    return math.floor(number * factor) / factor

if __name__ == "__main__":
    config = configuration.Config()
    client.run(config.token)
