from models import CreateSession,PlFixtures,Players, Gameweeks, Teams, Managers, Fixtures, Table
from methods import updatePlFixtures, updateGameweekPlayers,updateFixturesWithTablePoints,produceTable,createTable,GetGameweek,createFPLClassicoTable,updatedPointshit, reefed
from methods import TripleCaptain
import requests
import time
from sqlalchemy import or_,desc
from datetime import datetime, timedelta
from dateutil import tz
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
import pandas
import numpy as np
import matplotlib.pyplot as plt
import six
from config import tablePath, classicoPath

def GetGameweek(session):
    gw = session.query(Gameweeks.id).filter_by(is_current=1).first()
    if gw is None:
        gw = session.query(Gameweeks.id).filter_by(is_next=1).first()
    return gw[0]

def updatePlFixtures(gw):
    session=CreateSession()
    r = requests.get(f"https://fantasy.premierleague.com/api/fixtures/?event={gw}")
    fixtureData = r.json()
    for games in fixtureData:
        j = session.query(PlFixtures).filter_by(away_team=games['team_a']).filter_by(home_team=games['team_h']).filter_by(gameweek=gw).first()
        if games['started']:
            j.started = 1
        if games['finished_provisional']:
            j.finished = 1
        session.add(j)
    session.commit()
    session.close()

def updateGameweekPlayers(gw):
    session=CreateSession()
    players = session.query(Teams.playerId).filter_by(gameweek=gw).all()
    players = {p[0] for p in players}
    urls = [f"https://fantasy.premierleague.com/api/element-summary/{i}/" for i in players]
    pool = ThreadPoolExecutor(len(urls))
    futures = [pool.submit(requests.get,url) for url in urls]
    results = [r.result() for r in as_completed(futures)]
    for r in results:
        done=True
        player = r.json() #this can be cleaned up but it works for now
        dgw = [p['element'] for p in player['history'] if p['round'] == gw]
        if len(dgw) > 1:
            dwg = True
        else:
            dgw = False
        for x in player['history']:
            if x['round'] == gw:
                for i in players:
                    if x['element'] == i:
                        if dgw:
                            done = not done
                            if not done:
                                GameOneScore = int(x['total_points'])
                            if done:
                                myscore = int(x['total_points']) + GameOneScore
                                #j = update(Teams).where(Teams.playerId==i).values(points=myscore)
                                j = session.query(Teams).filter_by(playerId=i).filter_by(gameweek=gw).all()
                                for entries in j:
                                    h = entries
                                    if reefed(session,entries.managerId,entries.playerId,entries.gameweek):
                                        h.points = - myscore
                                    else:
                                        h.points = myscore
                                    session.add(h)
                            
                        else:
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

def updatedPointshit(gw):
    session=CreateSession()
    m = session.query(Managers).all()
    for i in m:
        fplid = i.fplId
        r = requests.get(f"https://fantasy.premierleague.com/api/entry/{fplid}/event/{gw}/picks/")
        team = r.json()
        hit = team['entry_history']['event_transfers_cost']
        x = session.query(Fixtures).filter(Fixtures.managerId==i.id).filter(Fixtures.gameweek==gw).first()
        x.pointhit = hit
        session.add(x)
        session.commit()

    session.close()
    
    
def updateFixturesWithTablePoints(gw):
    session=CreateSession()
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
        ph = f.pointhit
        if ph is None:
            ph = 0
        actualscore = points - ph
        f.score = actualscore
        
       
        
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
        oph = session.query(Fixtures).filter_by(gameweek=gw).filter_by(managerId=f.opponentId).first()
        oph = oph.pointhit
        if oph is None:
            oph = 0
            
        pointsOpponent = pointsOpponent - oph
        

        if actualscore > pointsOpponent:
            f.points = 3
        elif actualscore == pointsOpponent:
            f.points = 1
        else:
            f.points = 0
            
        session.add(f)
        session.commit()
    session.close()

def produceTable():
    session=CreateSession()
    p = session.query(Table).delete()
    session.commit()
    managers = session.query(Managers).all()
    for m in managers:
        f = session.query(Fixtures).filter_by(managerId=m.id).all()
        score = sum([i.score for i in f if i.score is not None])
        points = sum([i.points for i in f if i.score is not None])
        tb = Table(managerId=m.id,
                    score=score,
                    points=points)
        session.add(tb)
    session.commit()
    t = session.query(Table).order_by(desc(Table.points)).order_by(desc(Table.score)).all()
    p = session.query(Table).delete()
    session.commit()
    x = 0
    for i in t:
        x += 1
        tb = Table(position=x,
                    managerId=i.managerId,
                    score=i.score,
                    points=i.points)
        session.add(tb)
    session.commit()
    session.close()


def createTable():
    session=CreateSession()
    t = session.query(Table,Managers).filter(Table.managerId == Managers.id).all()
    values = [(i[1].teamName,i[0].score,i[0].points) for i in t]
    session.close()
    df = pandas.DataFrame(values, columns = ['Team' , 'PlayerScore', 'Points'])
    df = df.sort_values(['Points','PlayerScore'], ascending=[False, False])
    df = df.reset_index()
    df.drop('index', axis=1, inplace=True)
    df['#'] = df.index +1
    df['#'] = df['#'].apply(lambda x: "{}{}".format(x, (' '*15) ))
    df = df[['#','Team', 'PlayerScore', 'Points']]
    render_mpl_table(df,tablePath)
    
def createFPLClassicoTable():
    session=CreateSession()
    t = session.query(Table,Managers).filter(Table.managerId == Managers.id).all()
    values = [(i[1].teamName,i[0].score) for i in t]
    session.close()
    df = pandas.DataFrame(values, columns = ['Team' , 'PlayerScore'])
    df = df.sort_values(['PlayerScore'], ascending=[False])
    df = df.reset_index()
    df.drop('index', axis=1, inplace=True)
    df['#'] = df.index +1
    df['#'] = df['#'].apply(lambda x: "{}{}".format(x, (' '*15) ))
    df = df[['#','Team', 'PlayerScore']]
    render_mpl_table(df,classicoPath)  

def render_mpl_table(data,filename, col_width=3.0, row_height=0.625, font_size=14,
                     header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
                     bbox=[0, 0, 1, 1], header_columns=0,
                     ax=None, **kwargs):
    if ax is None:
        size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        fig, ax = plt.subplots(figsize=size)
        ax.axis('off')

    mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)

    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    for k, cell in  six.iteritems(mpl_table._cells):
        cell.set_edgecolor(edge_color)
        if k[0] == 0 or k[1] < header_columns:
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor(header_color)
        else:
            cell.set_facecolor(row_colors[k[0]%len(row_colors) ])
    fig.savefig(filename)
    return ax

session=CreateSession()
gw = session.query(Gameweeks.id).filter_by(is_current=1).first()
session.close()

def GetActualGameweek():
    r = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/")
    events = r.json()['events']
    for i in events:
        if i['is_current']:
            return i['id']

actualgw = GetActualGameweek()

for i in range(gw[0],actualgw +1):
    updatePlFixtures(i)
    updateGameweekPlayers(i)
    updatedPointshit(i)
    updateFixturesWithTablePoints(i)
    produceTable()
    createTable()
    createFPLClassicoTable()