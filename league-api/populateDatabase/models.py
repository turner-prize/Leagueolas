import os 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import Column, Integer, String, ForeignKey,create_engine
from sqlalchemy.orm import sessionmaker, Session,relationship
import requests
import datetime
from dateutil import tz
from collections import namedtuple

def CreateSession():
        engine = create_engine(f"sqlite:///C:/Users/Turner_prize/Desktop/league-site/league-api/league.db")#,echo=True)
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        return Session()

Base = declarative_base()

class Gameweeks(Base):
    __tablename__ = 'gameweeks'
    id = Column(Integer,primary_key=True)
    name = Column(String(50))
    deadline = Column(String(50))
    is_current = Column(String(50))
    is_next = Column(String(50))
    gameweek_start = Column(String(50))
    gameweek_end = Column(String(50))

class Players(Base):
    __tablename__ = 'players'
    jfpl = Column(Integer,primary_key=True)
    event_points = Column(Integer)
    first_name = Column(String(50))
    second_name = Column(String(50))
    team = Column(Integer)
    team_code = Column(Integer)
    goals_scored = Column(Integer)
    assists = Column(Integer)
    goals_conceded = Column(Integer)
    pen_saved = Column(Integer)
    pen_missed = Column(Integer)
    yellow_cards = Column(Integer)
    red_cards = Column(Integer)
    saves = Column(Integer)
    element_type = Column(Integer)

class PlFixtures(Base):
    __tablename__ = 'plFixtures'
    id = Column(Integer,primary_key=True)
    kickoff_time = Column(String(50))
    gameweek = Column(Integer)
    away_team = Column(Integer)
    home_team = Column(Integer)
    started = Column(String(50))
    finished = Column(String(50))

class PlTeams(Base):
    __tablename__ = 'plTeams'
    id = Column(Integer,primary_key=True)
    name = Column(String(50))
    shortname = Column(Integer)

def populateGameweeks():
    r = requests.get("https://fantasy.premierleague.com/api/bootstrap-static")
    bootstrapData = r.json()
    gameweekData = bootstrapData['events']
    session=CreateSession()
    for i in gameweekData:
        gw = Gameweeks( id=i['id'],
                        name=i['name'],
                        deadline=i['deadline_time'],
                        is_current=i['is_current'],
                        is_next=i['is_next'],
                        gameweek_start='test',
                        gameweek_end='test')
        session.add(gw)
        session.commit()
    session.close()

def populatePlayers():
    r = requests.get("https://fantasy.premierleague.com/api/bootstrap-static")
    bootstrapData = r.json()
    playerData = bootstrapData['elements']
    session=CreateSession()
    for i in playerData:
        plyr = Players( jfpl = i['id'],
                        event_points = i['event_points'],
                        first_name = i['first_name'],
                        second_name = i['second_name'],
                        team = i['team'],
                        team_code = i['team_code'],
                        goals_scored = i['goals_scored'],
                        assists = i['assists'],
                        goals_conceded = i['goals_conceded'],
                        pen_saved = i['penalties_saved'],
                        pen_missed = i['penalties_missed'],
                        yellow_cards = i['yellow_cards'],
                        red_cards = i['red_cards'],
                        saves = i['saves'],
                        element_type = i['element_type'])
        session.add(plyr)
        session.commit()
    session.close()

def populatePlFixtures():
    r = requests.get("https://fantasy.premierleague.com/api/fixtures/?event=1")
    fixtureData = r.json()
    session=CreateSession()
    for i in fixtureData:
        fxtr = PlFixtures(  id = i['id'],
                            kickoff_time = i['kickoff_time'],
                            gameweek = i['event'],
                            away_team = i['team_a'],
                            home_team = i['team_h'],
                            started = i['started'],
                            finished = i['finished'])
        session.add(fxtr)
        session.commit()
    session.close()

def populatePlTeams():
    r = requests.get("https://fantasy.premierleague.com/api/bootstrap-static")
    bootstrapData = r.json()
    plTeamsData = bootstrapData['teams']
    session=CreateSession()
    for i in plTeamsData:
        tm = PlTeams(  id = i['id'],
                            name = i['name'],
                            shortname = i['short_name'])
        session.add(tm)
        session.commit()
    session.close()

def createCronJobs():
    session=CreateSession()
    q = session.query(PlFixtures.kickoff_time) \
            .distinct(PlFixtures.kickoff_time) \
            .order_by(PlFixtures.kickoff_time) \
            .all()
    dtRanges=[]
    for i in q:
        #timezone is UTC from database, need to change to current TZ
        dt = datetime.datetime.strptime(i.kickoff_time,'%Y-%m-%dT%H:%M:%SZ')
        dt=dt.replace(tzinfo=tz.gettz('UTC'))
        KickoffTime=dt.astimezone(tz.tzlocal())
        GameEndTime=KickoffTime + datetime.timedelta(hours=2)
        rng = (KickoffTime,GameEndTime)
        dtRanges.append(rng)
    session.close()
    return LoopIt(dtRanges)

def LoopIt(rng):
    Range = namedtuple('Range', ['start', 'end'])
    for i,val in enumerate(rng):
        try:
            r1 = Range(start=val[0], end=val[1])
            r2 = Range(start=rng[i+1][0], end=rng[i+1][1])
            latest_start = max(r1.start, r2.start)
            earliest_end = min(r1.end, r2.end)
            delta = (earliest_end - latest_start).days + 1
            overlap = max(0, delta)
            if overlap==0:
                pass
            else:
                newRng = (val[0],rng[i+1][1])
                rng[i] = newRng
                rng.pop(i+1)
                LoopIt(rng)
        except IndexError:
            pass
    return rng