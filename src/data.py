from typing import Dict, Tuple, List
import sqlite3 as sl


class Client:
    """Data access interface for MongoDB database for use with wordle-bot.

    The database has collections this collection:

    players:
        - _id
        - scores (Dictionary with Wordle number keys and score values)
        - count (number of scores)
        - win_count (number of scores that are not 7, for average computation)
        - average
    """

    def __init__(self):
        """Initialize a new Client connected to the local MongoDB instance."""
        self.sql = sl.connect("wordle.db")
        self.checkAndCreateTable()

    def checkAndCreateTable(self) -> None:
        listOfTables = self.sql.execute(
        """SELECT name FROM sqlite_master WHERE type='table' AND name='PLAYER'""").fetchall()
        
        if listOfTables == []:
            with self.sql:
                self.sql.execute("""
                    CREATE TABLE PLAYER (
                        pid INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        scores TEXT,
                        count INTEGER,
                        win_count INTEGER,
                        average FLOAT,
                        win_rate FLOAT
                    );
                """)
        else:
            print('Table found!')
        return None
    
    def findPlayer(self,pid) -> Dict:
        pData = self.sql.execute("SELECT * FROM PLAYER WHERE pid == " + str(pid))
        player = None
        for data in pData:
            player = self.parsePlayer(data)
        return player

    def parsePlayer(self,playerData) -> Dict:
        playerScore = {}
        scores = playerData[1].split("|")
        for score in scores:
            if score is not "":
                score = score.split(";")
                playerScore[score[0]] = score[1]
        player = {
            "pid": playerData[0],
            "scores": playerScore,
            "count": playerData[2],
            "win_count": playerData[3],
            "average": playerData[4],
            "win_rate": playerData[5]
        }
        return player

    def createOrUpdatePlayer(self,player) -> Dict:
        sql = "INSERT OR REPLACE INTO PLAYER (pid, scores, count, win_count, average, win_rate) values(?, ?, ?, ?, ?, ?)"
        playerScoreStr = ""
        for score in player["scores"]:
            playerScoreStr += "{0};{1}|".format(score, player["scores"][score])
        data = [(
            player["pid"],
            playerScoreStr,
            player["count"],
            player["win_count"],
            player["average"],
            player["win_rate"]
            )]
        self.sql.executemany(sql,data)
        self.sql.commit()
        return None

    def add_score(self, pid: int, wordle: str, score: int) -> bool:
        """Adds a score to the relevant player in the database. If a score already exists, return False."""
        player = self.findPlayer(pid)
        if player is not None and wordle in player["scores"]:
            return False

        if player is None:
            # make a new one!
            player = {
                "pid": pid,
                "scores": {},
                "count": 0,
                "win_count": 0,
                "average": 0,
                "win_rate": 0
            }

        player["scores"][wordle] = score
        player["count"] += 1
        player["win_count"] = player["win_count"] if score == 7 else player["win_count"] + 1
        player["average"] = player["average"] + (score - player["average"]) / (player["count"])
        player["win_rate"] = player["win_count"] / player["count"]

        self.createOrUpdatePlayer(player)

        return True

    def get_player_stats(self, pid: int) -> Tuple[float, int, int, float]:
        """Return the stats of the player with provided id, given as a tuple in the form
        (average, count, win_count, win_rate).
        """
        player = self.findPlayer(pid)

        if player is None:
            return 0.0, 0, 0, 0

        return player["average"], player["count"], player["win_count"], player["win_rate"]

    def delete_player(self, pid: int) -> bool:
        """Return True iff the player with pid was successfully deleted."""
        result = self.db.players.delete_one({"_id": pid})
        if result.deleted_count != 0:
            return True
        return False
