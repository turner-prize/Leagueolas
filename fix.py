from models import Gameweeks, CreateSession, Managers, Teams,Players,DraftedPlayers, Fixtures, PlFixtures, Table
from sqlalchemy import update, Integer, desc
from sqlalchemy.orm import aliased,sessionmaker
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas
import numpy as np
import matplotlib.pyplot as plt
import six
import os
import telegram
from btoken import BotToken

def TripleCaptain(session,managerId,gw):
    TC = session.query(Managers).filter_by(id=managerId).filter_by(TC=gw).first()
    return TC

def BenchBoost(session,managerId,gw):
    BB = session.query(Managers).filter_by(id=managerId).filter_by(BB=gw).first()
    return BB

def updatePlFixtures():
    session=CreateSession()
    gw = 23
    r = requests.get(f"https://fantasy.premierleague.com/api/fixtures/?event={gw}")
    fixtureData = r.json()
    for games in fixtureData:
        j = session.query(PlFixtures).filter_by(away_team=games['team_a']).filter_by(gameweek=gw).first()
        if games['started']:
            j.started = 1
        if games['finished_provisional']:
            j.finished = 1
        session.add(j)
    session.commit()
    session.close()
    
def reefed(session,managerId,playerId,gw):
    reefed = session.query(Teams.reefed).filter_by(managerId=managerId).filter_by(playerId=playerId).filter_by(gameweek=gw).first()
    return reefed[0]
    
def updateGameweekPlayers():
    session=CreateSession()
    gw = 23
    players = session.query(Teams.playerId).filter_by(gameweek=gw).all()
    players = {p[0] for p in players}
    urls = [f"https://fantasy.premierleague.com/api/element-summary/{i}/" for i in players]
    pool = ThreadPoolExecutor(len(urls))
    futures = [pool.submit(requests.get,url) for url in urls]
    results = [r.result() for r in as_completed(futures)]
    for r in results:
        player = r.json() #this can be cleaned up but it works for now
        for x in player['history']:
            if x['round'] == gw:
                for i in players:
                    if x['element'] == i:
                        playerName = session.query(Players.web_name).filter_by(jfpl=i).first()
                        myscore = int(x['total_points'])
                        #j = update(Teams).where(Teams.playerId==i).values(points=myscore)
                        j = session.query(Teams).filter_by(playerId=i).filter_by(gameweek=gw).all()
                        for entries in j:
                            h = entries
                            if reefed(session,entries.managerId,entries.playerId,entries.gameweek):
                                h.points = - myscore
                            else:
                                h.points = myscore
                            session.add(h)
    session.commit()
    session.close()
    
def updateTeamsFinalBench():
    session=CreateSession()
    m = session.query(Managers).all()
    gw = 23
    for i in m:
        fplid = i.fplId
        r = requests.get(f"https://fantasy.premierleague.com/api/entry/{fplid}/event/{gw}/picks/")
        team = r.json()
        for p in team['picks']:
            if p['is_captain']:
                cap = 1
            else:
                cap = 0
            if not BenchBoost(session,i.id,gw):
                if p['position']> 11:
                    bench = 1
                else:
                    bench = 0
            else:
                bench = 0
            plyr = session.query(Teams).filter_by(playerId=p['element']).filter_by(managerId=i.id).filter_by(gameweek=gw).first()
            plyr.is_bench = bench
            session.add(plyr)
    session.commit()
    session.close()
    
def updateViceCaptain():
    session=CreateSession()
    m = session.query(Managers).all()
    gw = 23
    for i in m:
        fplid = i.fplId
        r = requests.get(f"https://fantasy.premierleague.com/api/entry/{fplid}/event/{gw}/picks/")
        team = r.json()
        for p in team['picks']:
            if not BenchBoost(session,i.id,gw):
                if p['is_captain'] and p['multiplier'] in[0,1] :
                    for q in team['picks']:
                        if q['is_vice_captain']:
                            plyr = session.query(Teams).filter_by(playerId=q['element']).filter_by(managerId=i.id).filter_by(gameweek=gw).first()
                            plyr.is_captain = 1
                            session.add(plyr)
    session.commit()
    session.close()
    
def updateFixturesWithTablePoints():
    session=CreateSession()
    gw = 23
    fixtures = session.query(Fixtures).filter_by(gameweek=gw).all()
    for f in fixtures:
        scores = session.query(Teams).filter_by(managerId=f.managerId).filter_by(gameweek=gw).filter_by(is_bench=0).all()
        scoreList = []
        for i in scores:
            if i.is_captain==1:
                if TripleCaptain(session,f.managerId,gw):
                    scoreList.append(i.points * 3)
                else:
                    scoreList.append(i.points * 2)
            else:
                scoreList.append(i.points)
        points = sum(scoreList)
        scoresOpponent = session.query(Teams).filter_by(managerId=f.opponentId).filter_by(gameweek=gw).filter_by(is_bench=0).all()
        scoreOpponentList = []
        for i in scoresOpponent:
            if i.is_captain==1:
                if TripleCaptain(session,f.managerId,gw):
                    scoreOpponentList.append(i.points * 3)
                else:
                    scoreOpponentList.append(i.points * 2)
            else:
                scoreOpponentList.append(i.points)
        pointsOpponent = sum(scoreOpponentList)
        
        f.score = points
        if points > pointsOpponent:
            f.points = 3
        elif points == pointsOpponent:
            f.points = 1
        else:
            f.points = 0
        session.add(f)
        session.commit()
    session.close()
    
    
    
updatePlFixtures()
updateGameweekPlayers()
updateTeamsFinalBench()
updateViceCaptain()
updateFixturesWithTablePoints()