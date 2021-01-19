#Need to Start the jan cup on the right week.
#Setting up LMS at the same time. Need it to figure out how many teams are in the league, and therefore what week we should start on initialisation of each season.
#   On that, it would be good on the setup to get confirmation of when things happen etc once the initialisation is run

from sqlalchemy.sql import func
from sqlalchemy import or_,desc
from models import CreateSession, Gameweeks, Fixtures, Teams, Managers,Players,PlFixtures,DraftedPlayers, PlTeams, JanCupFixtures
import commands

def JanCup():
    session = CreateSession()
    gw = GetJanCupWeek(session)
    if gw > 0 and gw <=5:
        if gw == 1 or gw == 2:
            x = JanCupQualification(session)
            session.close()
            return x
        else:
            x =  JanCupScores(session,gw)
            session.close()
            return x
    
def updateJanCup():
    session = CreateSession()
    gw = GetJanCupWeek(session)
    if gw == 3:
        UpdateSemis()
    elif gw == 4:
        UpdateFinal
    session.close()


def UpdateFinal():
    session = CreateSession()
    fixtures = session.query(JanCupFixtures).filter_by(isSemiFinal=1).all()      
    ScoreString = ''
    for f in fixtures:
        score1 = getScore(session,f.managerId)
        score2 = getScore(session,f.opponentId)

        if score1 > score2:
            x = f.managerId
        else:
            x = f.managerId
            
        insertFinalFixture(session,x)
    session.close()
    print('complete')

def insertFinalFixture(session,manager):
    x = session.query(JanCupFixtures).filter_by(isFinal=1).all()
    if len(x) == 0: #if 0 then the first part of the fixture exists, just need to add the opponent
        f = JanCupFixtures(managerId=manager,isQuarterFinal=0,isSemiFinal=0,isFinal=1,semiFinalDraw=0)
        session.add(f)
    else:
        f = session.query(JanCupFixtures).filter_by(isFinal=1).first()
        f.opponentId = manager
        session.add(f)
    session.commit()

def UpdateSemis():
    session = CreateSession()
    fixtures = session.query(JanCupFixtures).filter_by(isQuarterFinal=1).all()      
    ScoreString = ''
    for f in fixtures:
        score1 = getScore(session,f.managerId)
        score2 = getScore(session,f.opponentId)

        if score1 > score2:
            x = f.managerId
        else:
            x = f.managerId
            
        insertSemiFixture(session,x,f.semiFinalDraw)
    session.close()

def insertSemiFixture(session,manager,drawNumber):
    x = session.query(JanCupFixtures).filter_by(isSemiFinal=1).filter_by(semiFinalDraw=drawNumber).all()
    if len(x) == 0: #if 0 then the first part of the fixture exists, just need to add the opponent
        f = JanCupFixtures(managerId=manager,isQuarterFinal=0,isSemiFinal=1,isFinal=0,semiFinalDraw=drawNumber)
        session.add(f)
    else:
        f = session.query(JanCupFixtures).filter_by(isSemiFinal=1).filter_by(semiFinalDraw=drawNumber).first()
        f.opponentId = manager
        session.add(f)
    session.commit()
    

def getScore(session,id):
    gw = session.query(Gameweeks.id).filter_by(is_current=1).first()
    gw=gw.id
    scores = session.query(Teams).filter_by(managerId=id).filter_by(gameweek=gw).filter_by(is_bench=0).all()
    for i in scores:
        if i.is_captain==1:
            if TripleCaptain(session,id,gw):
                i.points = (i.points * 3)
            else:
                i.points = (i.points * 2)
    scoreList = [x.points for x in scores]
    points = sum(scoreList)
    pointhit = session.query(Fixtures).filter_by(managerId=id).filter_by(gameweek=gw).first()
    if pointhit.pointhit:
        points = points - pointhit.pointhit
    return points

def TripleCaptain(session,managerId,gw):
    TC = session.query(Managers).filter_by(id=managerId).filter_by(TC=gw).first()
    return TC

def JanCupScores(session,jcgw):
    gw = session.query(Gameweeks.id).filter_by(is_current=1).first()
    gw = gw.id
    if jcgw == 3:
        fixtures = session.query(JanCupFixtures).filter_by(isQuarterFinal=1).all()
    if jcgw == 4:
        fixtures = session.query(JanCupFixtures).filter_by(isSemiFinal=1).all()        
    if jcgw == 5:
        fixtures = session.query(JanCupFixtures).filter_by(isFinal=1).all()        
    fx = []
    ScoreString = ''
    for f in fixtures:
        manager1 = session.query(Managers).filter_by(id=f.managerId).first()
        if manager1.id in fx:
            continue
        else:
            ss1 = commands.getScoreString(session,f.managerId,gw)
            ss2 = commands.getScoreString(session,f.opponentId,gw)
            
            fx.append(f.managerId)
            fx.append(f.opponentId)
            ScoreString = ScoreString + '\n' + f'{ss1} \nvs\n{ss2}\n---'
    return ScoreString

  
def JanCupQualification(session):
    
    JcWeek1 = session.query(Gameweeks.id).filter_by(janCupStart=1).first()
    JcWeek1 = JcWeek1.id
    JcWeek2 = JcWeek1 + 1 

    scores = session.query(func.sum(Fixtures.score),Managers.name) \
                    .filter(or_(Fixtures.gameweek==JcWeek1,Fixtures.gameweek==JcWeek2)) \
                    .filter(Fixtures.managerId==Managers.id)
    scores=scores.group_by(Managers.name)
    scores = scores.all()
    scores = sorted(scores, key=lambda tup: tup[0])
    scores.insert(4,"--------")
    scores2=''
    for i in scores:
        if not i == scores[0]:
            scores2 = f'{i[1]} - {i[0]} \n{scores2}'
        else:
            scores2 = f'{i[1]} - {i[0]}'
    session.close()
    return scores2
    

def GetJanCupWeek(session):
    gw = session.query(Gameweeks.id).filter_by(is_current=1).first()
    JCStartWeek = session.query(Gameweeks.id).filter_by(janCupStart=1).first()
    return (gw.id - JCStartWeek.id) +1