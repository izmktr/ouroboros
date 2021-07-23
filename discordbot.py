# tokenkeycode.py というファイル名で以下の行を保存する 
# TOKEN = 'xxxxxxxxxxxxxxxxxxxxxxxx.yyyyyy.zzzzzzzzzzzzzzzzzzzzzzzzzzz'

inputchannel = '凸報告'
outputchannel = '状況報告'

BossName = [
    'ゴブリングレート',
    'ライライ',
    'シードレイク',
    'スピリットホーン',
    'カルキノス',
]

#最大攻撃数
MAX_SORITE = 3

BATTLESTART = '06/25'
BATTLEEND = '06/29'
LevelUpLap = [4, 11, 31, 41]
BossHpData = [
    [   [600, 1.2], [800, 1.2], [1000, 1.3], [1200, 1.4], [1500, 1.5]   ],
    [   [600, 1.6], [800, 1.6], [1000, 1.8], [1200, 1.9], [1500, 2.0],  ],
    [   [700, 2.0], [900, 2.0], [1300, 2.4], [1500, 2.4], [2000, 2.6],  ],
    [   [1700, 3.5], [1800, 3.5], [2000, 3.7], [2100, 3.8], [2300, 4.0], ],
    [   [8500, 3.5], [9000, 3.5], [9500, 3.7], [10000, 3.8], [11000, 4.0], ],
]

GachaLotData = [
    [0.7, 0.0, 1.8, 18, 100], # 通常
    [0.7, 0.0, 1.8, 18, 100], # 限定
    [0.7, 0.0, 1.8, 18, 100], # プライズ
    [1.4, 0.0, 3.6, 18, 100], # 通常(2倍)
    [0.7, 0.9, 3.4, 18, 100], # プリフェス
]

ERRFILE = 'error.log'
SETTINGFILE = 'setting.json'

BossLapScore = []
for l in BossHpData:
    lapscore = 0
    for _i in l:
        lapscore += _i[0] * _i[1]
        _i.append(_i[0] * _i[1])
    BossLapScore.append(lapscore)

from re import match, split
from sre_constants import MARK
from types import MemberDescriptorType
import tokenkeycode

import asyncio
import discord
from discord.ext import tasks
import datetime 
import json
import glob
import os
import re
import codecs
import random
from typing import List, Dict, Any, Optional, Tuple
from io import StringIO
from typing import Sequence, TypeVar, Callable
from functools import cmp_to_key

T = TypeVar('T') 

BOSSNUMBER = len(BossName)
MA_LAP = 3

# 接続に必要なオブジェクトを生成
intents = discord.Intents.default()  # デフォルトのIntentsオブジェクトを生成
intents.typing = False  # typingを受け取らないように
intents.members = True  # membersを受け取る
client = discord.Client(intents=intents)

clanhash: Dict[int, 'Clan'] = {}

def sign(n : int):
    if n < 0 : return -1
    if 0 < n : return 1
    return 0

class GlobalStrage:
    @staticmethod
    def SerializeList(data):
        result = []
        for d in data:
            result.append(d.Serialize())
        return result

    @staticmethod
    def Load():
        global BossName
        global BATTLESTART
        global BATTLEEND

        with open(SETTINGFILE) as a:
            mdic =  json.load(a)

            if 'BossName' in mdic:
                BossName = mdic['BossName']

            if 'BATTLESTART' in mdic:
                BATTLESTART = mdic['BATTLESTART']
                start = datetime.datetime.strptime(BATTLESTART, '%m/%d')
                BATTLEPRESTART = (start + datetime.timedelta(days = -1)).strftime('%m/%d')

            if 'BATTLEEND' in mdic:
                BATTLEEND = mdic['BATTLEEND']

    @staticmethod
    def Save():
        dic = {
            'BossName' : BossName,
            'BATTLESTART' : BATTLESTART,
            'BATTLEEND' : BATTLEEND,
        }

        with open(SETTINGFILE, 'w') as a:
            json.dump(dic, a , indent=4)

#クランスコア計算ロジック

class ScoreCalcResult:
    def __init__(self, lap, level, bindex, hprate, modscore):
        self.lap = lap
        self.level = level
        self.bossindex = bindex
        self.hprate = hprate
        self.modscore = modscore

class ClanScore:
    @staticmethod
    def Calc(score) -> Optional[ScoreCalcResult]:
        total = 0
        level = 0
        while level < len(LevelUpLap):
            prevlap = (LevelUpLap[level - 1] if 0 < level else 1)
            blap = LevelUpLap[level] - prevlap
            if score < total + blap * BossLapScore[level]:
                break
            total += blap * BossLapScore[level]
            level += 1
        
        lap = (score - total) // BossLapScore[level] + (LevelUpLap[level - 1] if 0 < level else 1)
        modscore = (score - total) % BossLapScore[level]

        totalscore = 0
        bindex = 0
        while bindex < BOSSNUMBER:
            nowbossscore = BossHpData[level][bindex][2]

            if modscore < totalscore + nowbossscore:
                hprate = int(100 - (modscore - totalscore) * 100 // nowbossscore)
                return ScoreCalcResult(lap, level, bindex, hprate,  modscore)
            totalscore += nowbossscore
            bindex += 1

        return None

alphamatch = re.compile('^[a-z]+')
def Command(str, cmd):
    if isinstance(cmd, list):
        for c in cmd:
            ret = Command(str, c)
            if ret is not None:
                return ret
        return None

    if alphamatch.match(cmd):
        result = alphamatch.match(str)
        if result is None:
            return None

        if result.group(0) == cmd:
            return str[len(cmd):].strip()
    else:
        length = len(cmd)
        if str[:length] == cmd:
            return str[length:].strip()
    
    return None

class AttackHistory():
    keyarray = [
        'sortie',
        'messageid',
        'boss',
        'overtime',
        'defeat',
        'sortiecount',
        'updatetime'
    ]

    def __init__(self, messageid, sortie, boss, overtime, defeat, sortiecount):
        self.sortie = sortie                #何凸目か
        self.messageid = messageid          #凸に使ったメッセージID
        self.boss = boss                    #凸したボス
        self.overtime = overtime            #持ち越し秒数
        self.defeat = defeat                #敵を討伐したか
        self.sortiecount = sortiecount      #便宜上凸数(討伐or持ち越し凸なら0.5)
        self.updatetime = ''                #最終更新時間

    def TimeStamping(self):
        self.updatetime = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    @staticmethod
    def Desrialize(dic):
        history = AttackHistory(0, 0, 0, 0, False, 0)
        for key in AttackHistory.keyarray:
            if key in dic:
                history.__dict__[key] = dic[key]
        return history

    def Serialize(self):
        dic = {}
        for key in AttackHistory.keyarray:
            dic[key] = self.__dict__[key]
        return dic

class MessageReaction():
    def __init__(self, member) -> None:
        self.member = member
        self.addreaction = None
        self.removereaction = None
        self.deletereaction = None

class ClanMember():
    def __init__(self, id):
        self.id = id
        self.name = ''
        self.mention = ''
        self.taskkill = 0
        self.history : List[AttackHistory] = []
        self.attacktime = [None] * MAX_SORITE

        self.sortie = -1
        self.boss = 0
        self.attackmessage: Optional[discord.Message] = None
        self.reportlimit = None

        self.lastactive = datetime.datetime.now() + datetime.timedelta(days = -1)

    def CreateHistory(self, messageid, sortie, boss, overtime, defeat, sotiecount):
        h = AttackHistory(messageid, sortie, boss, overtime, defeat, sotiecount)
        h.TimeStamping()
        self.history.append(h)

    def Attack(self, bossindex : int, sortie : int):
        self.sortie = sortie
        self.reportlimit = datetime.datetime.now() + datetime.timedelta(minutes = 30)
        self.boss = bossindex
        self.History

    def IsAttack(self):
        return self.sortie != -1

    def IsOverkill(self):
        if not self.IsAttack(): return False
        time = self.attacktime[self.sortie]
        return time is not None and 0 < self.attacktime[self.sortie]

    #未凸数
    def FirstSoriteNum(self):
        return len([m for m in self.attacktime if m is None])

    #指定したLapで凸した回数
    def LapCount(self, lap : int):
        count = 0.0

        for h in self.history:
            if h.boss < (lap + 1) * BOSSNUMBER:
                count += h.sortiecount
        if MAX_SORITE <= count:
            return MAX_SORITE
        return count

    def DecoName(self, opt : str) -> str:
        s = ''
        for c in opt:
            if c == 'n': 
                s += self.name
            elif c == 't': 
                if self.taskkill: s += 'tk'
            elif c == 'T': 
                if self.taskkill: s += '[tk]'
            elif c == 'o':
                s += self.AttackTag()
            elif c == 'O':
                s += '[' + self.AttackTag() + ']'
            else: s += c

        return s

    #便宜上凸数
    def SortieCount(self):
        return MAX_SORITE - self.FirstSoriteNum()
    
    def AttackCharactor(self, at : Optional[int]):
        if at is None : return 'o'
        if at == 0 : return 'x'
        return '%d' % (at // 10)

    def AttackTag(self):
        return ''.join([self.AttackCharactor(m) for m in self.attacktime])
    
    def Finish(self, messageid, defeat = False, sortiecount = 1.0):
        if self.sortie < 0: return
        self.CreateHistory(messageid, self.sortie, self.boss, 0, defeat, sortiecount)
        self.attacktime[self.sortie] = 0
        self.sortie = -1
        self.reportlimit = None
    
    def Cancel(self):
        self.sortie = -1
        self.reportlimit = None

    def Overkill(self, messageid, overtime):
        if self.sortie < 0: return
        self.CreateHistory(messageid, self.sortie, self.boss, overtime, True, 0.5)
        self.attacktime[self.sortie] = overtime
        self.sortie = -1
        self.reportlimit = None

    def Overtime(self, sortie):
        return self.attacktime[sortie]

    def MessageChcck(self, messageid):
        for h in self.history:
            if h.messageid == messageid:
                return True
        return False

    def Reset(self):
        self.sortie = -1
        self.reportlimit = None
        self.taskkill = 0
        self.history.clear()
        self.attacktime = [None] * MAX_SORITE

    def History(self):
        str = ''
        for h in self.history:
            str += '%d凸目 %d周目:%s' % (h.sortie + 1,
            h.boss // BOSSNUMBER + 1, 
            BossName[h.boss % BOSSNUMBER])

            if h.defeat:
                str += ' %d秒' % (h.overtime)

            str += '\n'

        if str == '' : str = '履歴がありません'
        return str

    selializemember = [
        'name', 
        'taskkill', 
        'attacktime', 
        ]

    def Serialize(self):
        ret = {}

        for key, value in self.__dict__.items():
            if key in self.selializemember:
                ret[key] = value
        
        ret['history'] = [m.Serialize() for m in self.history]
        return ret

    def Deserialize(self, dic):
        for key, value in dic.items():
            if key == 'history':
                self.__dict__[key] = [AttackHistory.Desrialize(m) for m in value]
            else:
                self.__dict__[key] = value

    def Revert(self, messageid):
        if len(self.history) == 0: return None

        ret = [m for m in self.history if m.messageid == messageid]
        if 0 < len(ret):
            self.history.remove(ret[0])
            self.Attack(ret[0].boss, ret[0].sortie)
            self.CreateAttackTime()
            return ret[0]
        return None

    def CalcAttackTime(self, sortie : int):
        history = [m for m in self.history if m.sortie == sortie]
        if len(history) == 0: return None
        return min([h.overtime for h in history])

    def CreateAttackTime(self):
        self.attacktime = [self.CalcAttackTime(i) for i in range(MAX_SORITE)]

    def DayFinish(self):
        for t in self.attacktime:
            if t is None or 0 < t: return False
        
        return True
    
    def UpdateActive(self):
        self.lastactive = datetime.datetime.now()

class DamageControlMember:

    def __init__(self, member : ClanMember, damage : int, message : str = '', mark = 0) -> None:
        self.member : ClanMember = member
        self.damage = damage
        self.status = 0
        self.message = message
        self.mark = mark

class DamageControl():

    def __init__(self, clanmembers : Dict[int, ClanMember], bossindex : int):
        self.active = False
        self.lastmessage = None
        self.channel = None
        self.remainhp = 0
        self.bossindex = bossindex
        self.members : Dict[ClanMember, DamageControlMember] = {}
        self.outputlock = 0
        self.clanmembers : Dict[int, ClanMember]= clanmembers

    def SetChannel(self, channel):
        self.channel = channel

    def SetBossHp(self, bosshp):
        self.remainhp = bosshp

    def RemainHp(self, hp : int):
        self.active = True
        self.remainhp = hp

    async def TryDisplay(self):
        if 0 < len(self.members):
             await self.SendResult()

    def Damage(self, member : ClanMember, damage : int, message : str = '', mark = 0):
        self.active = True
        self.members[member] = DamageControlMember(member, damage, message, mark)

    def MemberSweep(self):
        if len([m for m in self.members.values() if m.status == 0]) == 0:
            self.members.clear()

    async def Remove(self, member : ClanMember):
        if member in self.members:
            del self.members[member]
            self.MemberSweep()

    async def Injure(self, member : ClanMember):
        if member in self.members:
            m = self.members[member]
            self.remainhp -= m.damage
            if self.remainhp < 0 : self.remainhp = 0
            
            m.damage = 0
            m.status = 1

            self.MemberSweep()

    def IsAutoExecutive(self):
        if self.channel is None: return False
        if self.active: return False
        if 0 < self.remainhp: return False
        return True

    def IsAttackMember(self, member : ClanMember):
        return member.IsAttack() and member.boss % BOSSNUMBER == self.bossindex

    def IsSetRemainHp(self, clan : 'Clan', member : ClanMember):
        if self.IsAttackMember(member): return True
        
        for dc in clan.damagecontrol:
            if dc != self and dc.channel == self.channel: return False
        return True

    def messageanlyze(self, clan : 'Clan', member : ClanMember, message):
        # 残りHP計算
        m = re.match('([@＠])([\s　]*)(\d+)', message.content)
        if m:
            if self.IsSetRemainHp(clan, member):
                remainhp = int(m.group(3))
                self.RemainHp(remainhp)
                return True
            else:
                clan.TemporaryMessage(self.channel, 'ボスが確定しません')
                return False
        
        if member.IsAttack() and member.boss % BOSSNUMBER == self.bossindex:
            m = re.match('(\d+[s秒])([\s　]*)(\d+)([^\d]*.*)', message.content)
            if m:
                damage = int(m.group(3))
                comment = str.strip(m.group(1) + m.group(4))
                self.Damage(member, damage, comment)
                return True

            m = re.match('(\d\d\d+)([^\d]*.*)', message.content)
            if m:
                damage = int(m.group(1))
                comment = str.strip(m.group(2))
                self.Damage(member, damage, comment)
                return True

            m = re.match('([xX])([\s　]*)([\d]*)([^\d]*.*)', message.content)
            if m:
                damage = int(m.group(3)) if 0 < len(m.group(3)) else 0
                comment = m.group(4)
                self.Damage(member, damage, comment, 1)
                return True
        return False

    async def on_message(self, clan : 'Clan', member : ClanMember, message):
        ret = self.messageanlyze(clan, member, message)

        if ret:
            await self.SendResult()

    @staticmethod
    def OverTime(remainhp : int, damage : int, overkill : bool):
        if overkill: return 0

        max = 90
        bonus = 20

        if damage <= 0: return 0

        d = max + 1 - (max * remainhp // damage) + bonus
        if max < d: return max
        return d

    def DefeatInfomation(self, slist : List[DamageControlMember], dcm : DamageControlMember, limit = 3):
        result = []
        thp = self.remainhp - dcm.damage

        i = 0

        found = False
        moverkill = dcm.member.IsOverkill()
        for s in slist:
            if dcm == s:
                found = True
                continue
                
            if thp <= s.damage:
                if s.member.IsOverkill() and (not found or not moverkill) : continue

                result.append( (s.member.name, self.OverTime(thp, s.damage, s.member.IsOverkill() )) )
                i += 1
                if limit <= i: break

        return result

    def DefeatCount(self, damagelist : List[DamageControlMember]):
        defeatcount = 1
        dsum = 0
        for n in damagelist:
            dsum += n.damage
            if self.remainhp <= dsum:
                break
            if 0 < n.damage and n.status == 0:
                defeatcount += 1
        
        return defeatcount

    def Status(self):
        mes = ''

        def Compare(a : DamageControlMember, b : DamageControlMember):
            ao = a.member.IsOverkill()
            bo = b.member.IsOverkill()

            if ao == bo: return sign(b.damage - a.damage)
            return sign(bo - ao)

        damagelist : List[DamageControlMember] = sorted([value for value in self.members.values()], key=cmp_to_key(Compare)) 
        totaldamage = sum([n.damage for n in damagelist])

        attackmember = set([m for m in self.clanmembers.values() if m.IsAttack()])

        mes += '%s HP %d' % (BossName[self.bossindex] , self.remainhp)
        if 0 < totaldamage and totaldamage < self.remainhp:
            mes += '  不足分 %d' % (self.remainhp - totaldamage)
        else:
            defeatcount = self.DefeatCount(damagelist)
            if 3 <= defeatcount:
                last = damagelist[defeatcount - 1]
                namelist = []

                remainhp = self.remainhp
                for m in damagelist:
                    remainhp -= m.damage
                    if 0 < remainhp:
                        namelist.append(m.member.name + '[%d]' % remainhp)
                
                namelist.append(last.member.name)

                mes += '\n' + '→'.join(namelist)
                prevdamage = sum([damagelist[i].damage for i in range(defeatcount - 1) ])
                mes += ' %d秒' % self.OverTime(self.remainhp - prevdamage, last.damage, last.member.IsOverkill() )

        for m in damagelist:
            if m.status == 0:
                attackmember.discard(m.member)

                mes += '\n%s %s%d' % (m.member.DecoName('nOT'), '' if m.mark == 0 else '×', m.damage)
                if self.remainhp <= m.damage:
                    if m.member.IsOverkill():
                        mes += ' 持越'
                    else:
                        mes += ' %d秒' % (self.OverTime(self.remainhp, m.damage, False))
                    
                    if m.message != '':
                        mes += ' ' + m.message

                else :
                    dinfo = self.DefeatInfomation(damagelist, m)
                    if 0 < len(dinfo):
                        mes += ''. join(['  →%s %d秒' % (d[0], d[1]) for d in dinfo])
                    else:
                        mes += '  残り %d' % (self.remainhp - m.damage)
        
        finishmember = [m.member.DecoName('nOT') for m in damagelist if m.status != 0]

        if 0 < len(finishmember):
            mes += '\n通過済み %s' % (' '.join(finishmember))

        if 0 < len(attackmember):
            mes += '\n未報告 %s' % (' '.join([m.DecoName('nOT') for m in attackmember]))
        return mes

    async def SendResult(self):
        if self.active:
            await self.SendMessage(self.Status())

    async def SendFinish(self, message):
        if self.active and self.lastmessage is not None:
            await self.SendMessage(message)

        self.active = False
        self.lastmessage = None
        self.remainhp = 0
        self.members.clear()

    async def SendMessage(self, mes):
        if self.outputlock == 1: return
        try:
            while self.outputlock != 0:
                await asyncio.sleep(1)

            if self.lastmessage is not None:
                self.outputlock = 1
                try:
                    await self.lastmessage.delete()
                except (discord.errors.NotFound, discord.errors.Forbidden):
                    pass
                self.lastmessage = None

            try:
                self.outputlock = 2
                self.lastmessage = await self.channel.send(mes)
            except discord.errors.Forbidden:
                self.channel = None
        finally:
            self.outputlock = 0

class ReserveUnit:
    def __init__(self, boss: int, member: ClanMember, comment : Optional[str]):
       self.boss = boss
       self.member = member
       self.comment = comment

    def SetComment(self, comment):
        self.comment = comment

    @staticmethod
    def Deserialize(dic : Dict,  members : Dict[int, ClanMember]):
        if 'boss' not in dic: return None
        boss = dic['boss']

        if 'member' not in dic: return None
        mid = dic['member']
        if mid not in members: return None
        member = members[mid]

        if 'comment' not in dic: return None
        comment = dic['comment']

        return ReserveUnit(boss, member, comment)

    def Serialize(self):
        return {
            'boss' : self.boss,
            'comment' : self.comment,
            'member' : self.member.id,
        }

class Clan():
    numbermarks = [
        "\N{DIGIT ZERO}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT SIX}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT SEVEN}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT EIGHT}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT NINE}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
    ]

    emojis = [
        u"\u2705",
        "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT SIX}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT SEVEN}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT EIGHT}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        "\N{DIGIT NINE}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        u"\u274C",
    ]

    emojisoverkill = [
        u"\u2705",
        "\N{DIGIT ZERO}\N{COMBINING ENCLOSING KEYCAP}", # type: ignore
        u"\u274C",
    ]
    taskkillmark = u"\u2757"

    def __init__(self, channelid : int):
        self.members: Dict[int, ClanMember] = {}
        self.channelid = channelid
        self.lastmessage : Optional[discord.Message] = None
        self.stampcheck :Dict[str, Any] = {}
        self.bosscount = [0] * BOSSNUMBER
        self.lapAttackCount = []
        self.bossAttackCount = []
        self.defeatTime = []
        self.namedelimiter = ''
        self.reservelist : List[ReserveUnit] = []

        self.guild : discord.Guild = None
        self.inputchannel = None
        self.outputchannel = None

        self.damagecontrol = [DamageControl(self.members, bidx) for bidx in range(5)]

        self.admin = False

        self.outputlock = 0
        self.lapplayer = 0

        self.messagereaction : Dict[int, MessageReaction] = {}

        self.dicehistory = [10, 30, 50, 70, 90]

        self.commandlist = self.FuncMap()

        self.damagechannel = [0] * BOSSNUMBER

    def Save(self, clanid : int):
        dic = {
            'members': {},
            'bosscount' : self.bosscount,
            'channelid' : self.channelid,
            'lapAttackCount' : self.lapAttackCount,
            'bossAttackCount' : self.bossAttackCount,
            'defeatTime' : self.defeatTime,
 
            'namedelimiter' : self.namedelimiter,
            'admin' : self.admin,
            'reservelist': [m.Serialize() for m in self.reservelist],
            'damagecannel' : [(0 if m.channel is None else m.channel.id) for m in self.damagecontrol]
        }

        for mid, member in self.members.items():
            dic['members'][mid] = member.Serialize()

        with open('clandata/%d.json' % (clanid) , 'w') as a:
            json.dump(dic, a , indent=4)

    @staticmethod
    def Load(clanid : int):
        with open('clandata/%d.json' % (clanid)) as a:
            mdic =  json.load(a)

            clan = Clan(mdic['channelid'])
            clan.bosscount = mdic['bosscount']
            clan.namedelimiter = mdic['namedelimiter'] if 'namedelimiter' in mdic else None

            if 'lapAttackCount' in mdic:
                clan.lapAttackCount = mdic['lapAttackCount']

            if 'bossAttackCount' in mdic:
                clan.bossAttackCount = mdic['bossAttackCount']

            if 'defeatTime' in mdic:
                clan.defeatTime = mdic['defeatTime']

            if 'admin' in mdic:
                clan.admin = mdic['admin']

            for mid, dicmember in mdic['members'].items():
                member = ClanMember(int(mid))
                member.Deserialize(dicmember)
                clan.members[int(mid)] = member

            if 'reservelist' in mdic:
                for x in mdic['reservelist']:
                    reunit = ReserveUnit.Deserialize(x, clan.members)
                    if reunit is not None:
                        clan.reservelist.append(reunit)

            if 'damagecannel' in mdic:
                clan.damagechannel = mdic['damagecannel']

            return clan

    def FuncMap(self):
        return [
            (['a', '凸'], self.Attack),
            (['c', '持'], self.ContinuesAttack),
            (['cancel'], self.Cancel),
            (['reload'], self.Reload),
            (['taskkill', 'タスキル'], self.TaskKill),
#            (['memo', 'メモ'], self.Memo),
            (['defeat'], self.Defeat),
            (['undefeat'], self.Undefeat),
            (['setboss'], self.SetBoss),
            (['unreserve', '予約取り消し', '予約取消'], self.Unreserve),
            (['reserve', '予約'], self.Reserve),
            (['unplace', '配置取り消し', '配置取消'], self.Unplace),
            (['place', '配置'], self.Place),
#            (['recruit', '募集'], self.Recruit),
            (['refresh'], self.Refresh),
            (['memberlist'], self.MemberList),
            (['channellist'], self.ChannelList),
            (['namedelimiter'], self.NameDelimiter),
            (['memberinitialize'], self.MemberInitialize),
            (['setmemberrole'], self.SetMemberRole),
            (['dice', 'サイコロ', 'ダイス'], self.Dice),
            (['damagechannel'], self.DamageChannel),
#            (['role'], self.Role),
            (['reset'], self.MemberReset),
            (['history'], self.History),
#            (['overtime', '持ち越し時間'], self.OverTime),
#            (['defeatlog'], self.DefeatLog),
#            (['attacklog'], self.AttackLog),
            (['score'], self.Score),
            (['settingreload'], self.SettingReload),
            (['memberdelete'], self.MemberDelete),
            (['dailyreset'], self.DailyReset),
            (['monthlyreset'], self.MonthlyReset),
            (['bossname'], self.BossName),
            (['term'], self.Term),
            (['remain','残り'], self.Remain),
#            (['damage','ダメ','ダメージ'], self.Damage),
#            (['pd'], self.PhantomDamage),
#            (['dtest'], self.DamageTest),
#            (['clanattack'], self.AllClanAttack),
#            (['clanreport'], self.AllClanReport),
            (['active', 'アクティブ'], self.ActiveMember),
            (['servermessage'], self.ServerMessage),
            (['serverleave'], self.ServerLeave),
            (['zeroserverleave'], self.ZeroServerLeave),
            (['inputerror'], self.InputError),
            (['gcmd'], self.GuildCommand),
        ]

    def SetGuild(self, guild):
        self.guild = guild

        for i, dc in enumerate(clan.damagechannel):
            if 0 < dc:
                for ch in guild.channels:
                    if dc == ch.id:
                        clan.damagecontrol[i].SetChannel(ch)
                        clan.damagecontrol[i].SetBossHp(BossHpData[clan.BossLevel(i) - 1][i][0])
                        break

    def GetMember(self, author) -> ClanMember:
        member = self.members.get(author.id)
        if member is None:
            member = ClanMember(author.id)
            self.members[author.id] = member
        member.name = self.DelimiterErase(author.display_name)
        member.mention = author.mention
        return member

    @staticmethod
    async def SendMessage(channel, message : str):
        post = await channel.send(message)
        await asyncio.sleep(60)
        await post.delete()

    def TemporaryMessage(self, channel, message : str):
        asyncio.ensure_future(self.SendMessage(channel, message))

    def IsInput(self, channel_id):
        if self.inputchannel is None: return False
        return self.inputchannel.id == channel_id

    def FindMember(self, name) -> Optional[ClanMember]:
        for member in self.members.values():
            if member.name == name:
                return member
        return None

    def DeleteMember(self, name) -> Optional[ClanMember]:
        for id, member in self.members.items():
            if member.name == name:
                del self.members[id]
                return member
        return None

    def FullReset(self):
        self.Reset()
        self.bosscount = [0] * BOSSNUMBER
        self.defeatTime.clear()

    def Reset(self):
        self.lastmessage = None
        self.stampcheck.clear()
        self.messagereaction.clear()
        self.reservelist.clear()

        for member in self.members.values():
            member.Reset()


    def AddStamp(self, messageid):
        if messageid in self.stampcheck:
            self.stampcheck['messageid'] += 1
        else:
            self.stampcheck['messageid'] = 1
        return self.stampcheck['messageid']

    def RemoveStamp(self, messageid):
        if messageid in self.stampcheck:
            self.stampcheck['messageid'] -= 1
        else:
            self.stampcheck['messageid'] = 0
        return self.stampcheck['messageid']
    
    async def AddReaction(self, message, overkill):
        reactemojis = self.emojis if not overkill else self.emojisoverkill

        for emoji in reactemojis:
            await message.add_reaction(emoji)

    async def RemoveReaction(self, message, overkill : bool, me):
        reactemojis = self.emojis if not overkill else self.emojisoverkill

        for emoji in reactemojis:
            try:
                await message.remove_reaction(emoji, me)
            except (discord.errors.NotFound, discord.errors.Forbidden):
                break

    async def RemoveReactionNotCancel(self, message, overkill : bool, me):
        reactemojis = self.emojis if not overkill else self.emojisoverkill

        for emoji in reactemojis:
            if emoji != u"\u274C":
                try:
                    await message.remove_reaction(emoji, me)
                except (discord.errors.NotFound, discord.errors.Forbidden):
                    break

    async def MemberRefresh(self):
        if self.guild is None: return

        mes = ''
        mlist = []
        deletemember = []

        if len([m for m in self.guild.members if not m.bot]) < 40:
            for member in self.guild.members:
                if not member.bot:
                    mlist.append(member.id)
                    if self.members.get(member.id) is None:
                        self.GetMember(member)
                        mes += member.name + "を追加しました\n"

            for id, member in self.members.items():
                if id not in mlist:
                    deletemember.append(id)
                    mes += member.name + "を削除しました\n"
        else :
            mes += '人数が多すぎるので、自動調整は行なえません'

        for id in deletemember:
            del self.members[id]

        self.SetInputChannel()
        if self.inputchannel is not None:
            self.TemporaryMessage(self.inputchannel, mes)
    
    def CheckOptionNone(self, opt):
        if 0 < len(opt): 
            raise ValueError
        return True

    def CheckInputChannel(self, message):
        if self.inputchannel is None or message.channel.name != inputchannel:
            return True
            
        return False

    def CheckNotAdministrator(self, message):
        if message.author.guild_permissions.administrator:
            return False
        return True

    def CheckNotMasterAdministrator(self, clan, message):
        if clan.Admin:
            return False
        if message.author.guild_permissions.administrator:
            return False
        return True

    def AttackNum(self, bossindex):
        return len([m for m in self.members.values() if m.IsAttack() and m.boss == bossindex])

    def CreateNotice(self, lap, bidx):
        pickuplap = [None] * BOSSNUMBER
        message = []

        pickuplap[bidx] = self.bosscount[bidx]

        if lap is not None:
            if lap + 1 in LevelUpLap:
                pickuplap = [lap + 1] * BOSSNUMBER
            else:
                for bidx in range(BOSSNUMBER):
                    if self.bosscount[bidx] == lap + 1 and lap + 2 not in LevelUpLap:
                        pickuplap[bidx] = lap + 1

        for bidx in range(BOSSNUMBER):
            if pickuplap[bidx] is not None:
                boss = pickuplap[bidx] * BOSSNUMBER + bidx
                mention = [m.member.mention for m in self.reservelist if m.boss == boss]

                if 0 < len(mention):
                    message.append('%s %sがやってきました' % (' '.join(mention), BossName[bidx]))

        if 0 < len(message):
            return '\n'.join(message)

        return None

    def IsAttackableBoss(self, bidx : int):
        minlap = self.MinLap()
        lapsub = self.bosscount[bidx] - minlap
        if 2 <= lapsub: return False
        if lapsub == 1 and minlap + 2 in LevelUpLap: return False
        return True

    async def AttackCheck(self, message, member : ClanMember, bidx : int):
        if self.CheckInputChannel(message):
            self.TemporaryMessage(message.channel, '%s のチャンネルで発言してください' % inputchannel)
            return True

        if not self.IsAttackableBoss(bidx):
            self.TemporaryMessage(message.channel, '攻撃できないボスです')
            return True

        if member.IsAttack():
            self.TemporaryMessage(message.channel, 'すでに凸があります 前の凸を無効にするにはcancelと入力してください')
            return True

        return False

    def CreateAttackReaction(self, atmember : ClanMember, message, boss : int, sortie : int, overtime : int):
        react = MessageReaction(atmember)

        async def addreaction(member : ClanMember, payload):
            if member != atmember:
                return False

            idx = self.emojiindex(payload.emoji.name)
            if idx is None:
                return False

            v = self.AddStamp(payload.message_id)
            if v != 1:
                Outlog(ERRFILE, "self.AddStamp" + " " + v)
                return False

            if idx == 0:
                member.Finish(payload.message_id)
                self.RemoveReserve(lambda m: m.member == member and m.boss == boss)

                await self.damagecontrol[boss % BOSSNUMBER].Injure(member)
                await self.damagecontrol[boss % BOSSNUMBER].SendResult()
            
            if 1 <= idx and idx <= 8:
                if 0 < overtime:
                    member.Finish(payload.message_id, True, 0.5)
                else:
                    member.Overkill(payload.message_id, (idx + 1) * 10)

                bidx = boss % BOSSNUMBER
                await self.damagecontrol[bidx].SendFinish('%s の討伐お疲れさまです' % (BossName[bidx]))

                newlap = self.DefeatBoss(bidx)

                mention = self.CreateNotice(newlap, bidx)

                if mention is not None:
                    await message.channel.send(mention)

                for m in self.members.values():
                    if m.IsAttack() and m.boss == boss:
                        m.reportlimit = datetime.datetime.now() + datetime.timedelta(minutes = 5)
            
            if idx == 9:
                member.Cancel()
                await self.damagecontrol[boss % BOSSNUMBER].Remove(member)
                await self.damagecontrol[boss % BOSSNUMBER].SendResult()

            await self.RemoveReaction(message, 0 < overtime, message.guild.me)
            return True

        react.addreaction = addreaction

        async def removereaction(member : ClanMember, payload):
            if member != atmember:
                return False

            idx = self.emojiindex(payload.emoji.name)
            if idx is None:
                return False

            v = self.RemoveStamp(payload.message_id)
            if v != 0:
                return False

            if member.attackmessage is not None and member.attackmessage.id == payload.message_id:
                if idx == 9:
                    member.Attack(boss, sortie)
                    await self.AddReaction(message, 0 < overtime)
                    return True

                data = member.Revert(payload.message_id)
                if data is not None:
                    member.Attack(data.boss, data.sortie)
                    if data.defeat:
                        bossidx = data.boss % BOSSNUMBER
                        self.UndefeatBoss(bossidx)
                        self.TemporaryMessage(self.inputchannel, '巻き戻しました\nボスが違うときは、defeat/undefeat/setbossで調整してください')
                    
                    await self.AddReaction(message, 0 < overtime)

                    return True
                else:
                    self.TemporaryMessage(self.inputchannel, '巻き戻しに失敗しました')

        react.removereaction = removereaction

        return react

    async def Attack(self, message, member : ClanMember, opt):
        try:
            bidx = int(opt) - 1
            if bidx < 0 or BOSSNUMBER <= bidx:
                raise ValueError
        except ValueError:
            self.TemporaryMessage(message.channel, '凸5 のように発言してください')
            return False

        error = await self.AttackCheck(message, member, bidx)
        if error:
            return False

        if member.FirstSoriteNum() == 0:
            self.TemporaryMessage(message.channel, '新規凸がありません')
            return False

        boss = self.bosscount[bidx] * BOSSNUMBER + bidx

        member.Attack(boss, member.SortieCount())
        if member.attackmessage is not None:
            self.messagereaction.pop(member.attackmessage.id, None)
        member.attackmessage = message

        self.messagereaction[message.id] = self.CreateAttackReaction(member, message, boss, member.SortieCount(), 0)

        if member.taskkill != 0:
            await message.add_reaction(self.taskkillmark)

        await self.AddReaction(message, False)

        return True


    async def ContinuesAttack(self, message, member : ClanMember, opt):
        if opt == '':
            overlist = [(idx + 1, time) for idx, time in enumerate(member.attacktime) if time is not None and 0 < time]

            if 0 < len(overlist):
                self.TemporaryMessage(message.channel, '\n'.join([('%d: %d秒' % (m[0], m[1])) for m in overlist]))
            else:
                self.TemporaryMessage(message.channel, '持ち越しが有りません')
            return False

        try:
            num = int(opt)
            bidx = num // 10 - 1
            sortie = num % 10 - 1 
            if bidx < 0 or BOSSNUMBER <= bidx or sortie < 0 or MAX_SORITE <= sortie:
                raise ValueError
        except ValueError:
            self.TemporaryMessage(message.channel, '持52 のように発言してください')
            return False

        if member.attacktime[sortie] is None or member.attacktime[sortie] == 0:
            self.TemporaryMessage(message.channel, '持ち越しではありません')
            return False

        error = await self.AttackCheck(message, member, bidx)
        if error:
            return False

        boss = self.bosscount[bidx] * BOSSNUMBER + bidx

        member.Attack(boss, sortie)
        if member.attackmessage is not None:
            self.messagereaction.pop(member.attackmessage.id, None)
        member.attackmessage = message

        self.messagereaction[message.id] = self.CreateAttackReaction(member, message, boss, sortie, member.attacktime[sortie])

        if member.taskkill != 0:
            await message.add_reaction(self.taskkillmark)

        await self.AddReaction(message, True)

        return True

    async def Cancel(self, message, member : ClanMember, opt):
        if member.IsAttack():
            member.Cancel()
            self.TemporaryMessage(message.channel, '前のアタックをキャンセルしました')

        return True

    async def TaskKill(self, message, member : ClanMember, opt):
        member.taskkill = message.id
        await message.add_reaction(self.taskkillmark)
        return True

    async def Reload(self, message, member : ClanMember, opt):
        return True

    async def Defeat(self, message, member : ClanMember, opt):
        try:
            bidx = int(opt) - 1
            if bidx < 0 or BOSSNUMBER <= bidx:
                raise ValueError
        except ValueError:
            self.TemporaryMessage(message.channel, '数値エラー')
            return False

        newlap = self.DefeatBoss(bidx)
        mention = self.CreateNotice(newlap, bidx)

        if mention is not None:
            await message.channel.send(mention)
            
        self.TemporaryMessage(message.channel, '%d:%s を討伐済みにしました' % (bidx + 1, BossName[bidx]))

        return True

    async def Undefeat(self, message, member : ClanMember, opt):
        try:
            bidx = int(opt) - 1
            if bidx < 0 or BOSSNUMBER <= bidx:
                raise ValueError
        except ValueError:
            self.TemporaryMessage(message.channel, '数値エラー')
            return False

        newlap = self.UndefeatBoss(bidx)
        if newlap is not None:
            self.TemporaryMessage(message.channel, '%d周目に戻しました' % newlap + 1)
        else:
            self.TemporaryMessage(message.channel, '%d:%s を未討伐にしました' % (bidx + 1, BossName[bidx]))
        return True

    @staticmethod
    def BossReverse(boss : set):
        bossfull = {0, 1, 2, 3, 4}
        return bossfull - boss

    async def SetBoss(self, message, member : ClanMember, opt):
        try:
            sp = opt.split(' ')
            if len(sp) != BOSSNUMBER:
                raise ValueError

            self.bosscount = [int(s) - 1 for s in sp]
            await message.channel.send('ボスを設定しました')
        except ValueError:
            await message.channel.send('数値エラー')

        return True

    async def Memo(self, message, member : ClanMember, opt):
        return True

    async def Reserve(self, message, member : ClanMember, opt : str):
        strarray = opt.split(' ')

        route = self.RouteAnalyze(strarray[0])

        comment = None
        if 1 < len(strarray):
            comment = strarray[1]

        self.AddReserve(route, member, comment)

        routestr = [('%d-%d' % (m // BOSSNUMBER + 1, m % BOSSNUMBER +1)) for m in route]
        self.TemporaryMessage(message.channel, '%sの予約を入れました' % (','.join(routestr)))

        return True

    async def Unreserve(self, message, member : ClanMember, opt : str):
        if opt == 'all':
            self.RemoveReserve(lambda m: m.member == member)
            self.TemporaryMessage(message.channel, '予約をすべて消しました')
            return True

        route = self.RouteAnalyze(opt)

        if len(route) == 0:
            self.TemporaryMessage(message.channel, '消したい周回を入れてください すべて消すならallと入れてください')
            return False

        self.RemoveReserve(lambda m: m.member == member and m.boss in route)

        routestr = [('%d-%d' % (m // BOSSNUMBER + 1, m % BOSSNUMBER +1)) for m in route]
        self.TemporaryMessage(message.channel, '%sの予約を消しました' % (','.join(routestr)))
        
        return True

    async def Place(self, message, member : ClanMember, opt : str):
        strarray = opt.split(' ')
        
        route = self.RouteAnalyze(strarray[0])

        if len(route) == 0:
            self.TemporaryMessage(message.channel, 'ルートが有りません')
            return False        

        if 2 <= len(strarray):
            addmember = [self.FindMember(name) for name in strarray[1:]]
            addmember = [m for m in addmember if m is not None]
        else:
            addmember = []

        if len(addmember) == 0:
            self.TemporaryMessage(message.channel, 'メンバーがいません')
            return False        

        for m in addmember:
            self.AddReserve(route, m, None)

        routestr = [('%d-%d' % (m // BOSSNUMBER + 1, m % BOSSNUMBER +1)) for m in route]
        self.TemporaryMessage(message.channel, '%sに%sを追加しました' % (','.join(routestr), ' '.join([m.name for m in addmember])))

        return True

    async def Unplace(self, message, member : ClanMember, opt : str):

        if opt == 'all':
            self.reservelist.clear()
            self.TemporaryMessage(message.channel, '全員の予約を削除しました')
            return True

        strarray = opt.split(' ')
        route = self.RouteAnalyze(strarray[0])
        if 0 < len(route) == 0:
            routefunc : Callable[[ReserveUnit], bool] = lambda m: m.boss in route
            strarray = strarray[1:]
        else:
            routefunc : Callable[[ReserveUnit], bool] = lambda m: True

        addmember = [self.FindMember(name) for name in strarray]
        addmember = [m for m in addmember if m is not None]
        if len(addmember) == 0 and len(route) == 0:
            self.TemporaryMessage(message.channel, 'メンバーがいません')
            return False

        if 0 < len(addmember):
            memfunc : Callable[[ReserveUnit], bool] = lambda m: m.member in addmember
        else:
            memfunc : Callable[[ReserveUnit], bool] = lambda m: True

        self.RemoveReserve(lambda m: routefunc(m) and memfunc(m))
        self.TemporaryMessage(message.channel, '予約を消しました')

        return True

    async def Recruit(self, message, member : ClanMember, opt : str):
        if opt == '':
            bossdata = self.AliveBoss()
        else:
            bossdata = set()
            for n in opt:
                try:
                    b = int(n) - 1
                    bossdata.add(b)
                except ValueError:
                    pass
            if len(bossdata) == 0 or 0 < len(bossdata - self.AliveBoss()):
                await message.channel.send('ボスの数値が読み取れません')
                return False

        recruitmes = await message.channel.send('ボスを討伐する人はスタンプを押してください')

        for stamp in bossdata:
            await recruitmes.add_reaction(self.numbermarks[stamp + 1])

        return False

    async def Refresh(self, message, member : ClanMember, opt):
        await self.MemberRefresh()
        return True

    async def MemberList(self, message, member : ClanMember, opt):

        if 0 < len(message.guild.members):
            await message.channel.send('\n'.join([m.name for m in message.guild.members]))
        else:
            await message.channel.send('len(message.guild.members):%d' % len(message.guild.members))

        return False

    async def ChannelList(self, message, member : ClanMember, opt):
        mes = ''
        mes += 'len %d\n' % (len(message.guild.channels))

        for m in message.guild.channels:
            mes += '%s/%s\n' % (m.name, m.name == inputchannel)

        await message.channel.send(mes)

        return False

    def DelimiterErase(self, name : str):
        if self.namedelimiter is None or self.namedelimiter == "":
            return name

        npos = name.find(self.namedelimiter)
        if npos < 0:
            return name
        return name[0:npos]

    async def NameDelimiter(self, message, member : ClanMember, opt):
        self.namedelimiter = None  if opt == '' else opt

        for m in self.guild.members:
            if m.id in self.members:
                self.members[m.id].name = self.DelimiterErase(m.display_name)

        if self.namedelimiter is None:
            mes = 'デリミタをデフォルトに戻しました'
        else:
            mes = 'デリミタを%sに設定しました' % self.namedelimiter

        self.TemporaryMessage(message.channel, mes)

        return True

    async def MemberInitialize(self, message, member : ClanMember, opt):
        if not message.author.guild_permissions.administrator: return False

        self.members.clear()
        self.TemporaryMessage(message.channel, 'メンバーを全て削除しました')

        return True

    async def SetMemberRole(self, message, member : ClanMember, opt):
        rolelist = [role for role in self.guild.roles if opt in role.name]

        if len(rolelist) == 0:
            self.TemporaryMessage(message.channel, 'Roleが見つかりません')
            return False
        elif 2 <= len(rolelist):
            self.TemporaryMessage(message.channel, 'Roleが複数あります %s' % (','.join([m.name for m in rolelist])) )
            return False

        role = rolelist[0]
        if len(role.members) == 0:
            self.TemporaryMessage(message.channel, 'Roleメンバーが0人です')
            return False

        self.members.clear()

        for m in role.members:
            if not m.bot:
                self.GetMember(m)

        self.TemporaryMessage(message.channel, '%s のRoleのメンバーを登録しました' % role.name)

        return True

    async def Dice(self, message, member : ClanMember, opt):

        while True:
            rndstar = int(random.random() * 100 + 1)
            if rndstar not in self.dicehistory:
                self.dicehistory = self.dicehistory[1:]
                self.dicehistory.append(rndstar)
                break

        await message.channel.send('%s %s %d' % (member.name, chr(int(0x1F3B2)), rndstar))

        return True

    async def Role(self, message, member : ClanMember, opt):
        rolelist = [('%s:%s' %(role.name, ','.join([m.name for m in role.members]))) for role in self.guild.roles]
        await message.channel.send('\n'.join(rolelist))

        return True

    async def CmdReset(self, message, member : ClanMember, opt):
        member.Reset()
        return True

    async def History(self, message, member : ClanMember, opt):
        if opt == '':
            await message.channel.send(member.History())
        else:
            fmember = self.FindMember(opt)
            if fmember is not None:
                await message.channel.send(fmember.History())
            else:
                self.TemporaryMessage(message.channel, 'メンバーがいません')
        return False

    async def OverTime(self, message, member : ClanMember, opt):
        try:
            time = int(opt)
            if time < 0 or 90 < time:
                raise ValueError
            errmes = member.ChangeOvertime(time)
            if errmes is not None:
                self.TemporaryMessage(message.channel, errmes)
                return False
            self.TemporaryMessage(message.channel, '持ち越し時間を%d秒にしました' % time)
            return True
        except ValueError:
            self.TemporaryMessage(message.channel, '時間が読み取れません')
            return False

        return True

    async def DefeatLog(self, message, member : ClanMember, opt):
        text = ''
        for n in self.defeatTime:
            text += n + '\n'

        with StringIO(text) as bs:
            await message.channel.send(file=discord.File(bs, 'defeatlog.txt'))
        return False

    async def AttackLog(self, message, member : ClanMember, opt):
        text = ''
#        for n in self.attackTime:
#            text += n + '\n'

        with StringIO(text) as bs:
            await message.channel.send(file=discord.File(bs, 'attacklog.txt'))
        return False

    async def Score(self, message, member : ClanMember, opt):
        result = self.ScoreCalc(opt)
        if result is not None:
            await message.channel.send('%d-%d %s (残りHP %s %%)' % 
            (result.lap, result.bossindex + 1, BossName[result.bossindex], result.hprate))
            return True
        else:
            self.TemporaryMessage(message.channel, '計算できませんでした')
            return False
    
    async def SettingReload(self, message, member : ClanMember, opt):
        channel = message.channel

        GlobalStrage.Load()
        self.TemporaryMessage(channel, 'リロードしました')
        self.TemporaryMessage(channel, 'term %s-%s' % (BATTLESTART, BATTLEEND))

        return False

    async def MemberDelete(self, message, member : ClanMember, opt):
        if not message.author.guild_permissions.administrator:
            return False

        result = self.DeleteMember(opt)
        if result is not None:
            self.TemporaryMessage(message.channel, '%s を消しました' % result.name)
            return True
        else:
            self.TemporaryMessage(message.channel, 'メンバーがいません')
            return False

    async def MemberReset(self, message, member : ClanMember, opt):
        member.Reset()
        return True

    async def DailyReset(self, message, member : ClanMember, opt):
        if not message.author.guild_permissions.administrator:
            return False

        self.Reset()
        self.TemporaryMessage(message.channel, 'デイリーリセットしました')
        return True

    async def MonthlyReset(self, message, member : ClanMember, opt):
        if not message.author.guild_permissions.administrator:
            return False

        self.FullReset()
        self.TemporaryMessage(message.channel, 'マンスリーリセットしました')
        return True

    async def BossName(self, message, member : ClanMember, opt):
        if not self.admin: return False
        if not message.author.guild_permissions.administrator: return False
        channel = message.channel

        namearray = opt.split(',')

        if BOSSNUMBER != len(namearray):
            await channel.send('usage) bossname boss1,boss2,boss3,boss4,boss5')
            return
        
        global BossName
        BossName = namearray
        GlobalStrage.Save()

        self.TemporaryMessage(message.channel, 'ボスを更新しました'+','.join(BossName))
        return True

    async def Term(self, message, member : ClanMember, opt):
        if not self.admin: return False
        if not message.author.guild_permissions.administrator: return False
        channel = message.channel

        team = opt.split(',')

        if len(team) != 2:
            self.TemporaryMessage(channel, 'usage) team 1/20,1/30')
            return

        global BATTLESTART
        global BATTLEEND

        try:
            start = datetime.datetime.strptime(team[0], '%m/%d')
            end = datetime.datetime.strptime(team[1], '%m/%d')

            BATTLESTART = start.strftime('%m/%d')
            BATTLEEND = end.strftime('%m/%d')

            GlobalStrage.Save()
            await channel.send('クラバト期間は%s-%sです' % (BATTLESTART, BATTLEEND))
        except ValueError:
            self.TemporaryMessage(channel, '日付エラーです')
        return True

    async def AllClanAttack(self, message, member : ClanMember, opt):
        if not self.admin: return False
        if not message.author.guild_permissions.administrator: return False

        channel = message.channel

        mes = ''
        for guild in client.guilds:
            clan = clanhash.get(guild.id)
            if clan is not None:
                attackmembers = [m.name for m in clan.members.values() if m.IsAttack()]
                atn = len(attackmembers)
                if 0 < atn:
                    mes += '[%s] %d %s\n' % (guild.name, atn, ' '.join(attackmembers))

        await channel.send(mes)

        return False

    async def AllClanReport(self, message, member : ClanMember, opt):
        if not self.admin: return False
        if not message.author.guild_permissions.administrator: return False

        channel = message.channel

        mes = ''
        for guild in client.guilds:
            mes += '[%d] %s\n' % (guild.id, guild.name)

            clan = clanhash.get(guild.id)
            if clan is not None:
                mes += clan.Status() + '\n'

        dt_now = datetime.datetime.now()
        filename = 'report_%s.txt' % dt_now.strftime("%Y%m%d_%H%M")  
        
        with StringIO(mes) as bs:
            await channel.send(file=discord.File(bs, filename))

        return False

    async def ActiveMember(self, message, member : ClanMember, opt):
        channel = message.channel

        mes = ''

        ttime = datetime.datetime.now() + datetime.timedelta(hours = -1)
        active = [m for m in self.members.values() if ttime < m.lastactive and m.SortieCount() < MAX_SORITE]

        def Compare(a : ClanMember, b : ClanMember):
            return sign(a.SortieCount() - b.SortieCount())

        active = sorted(active, key=cmp_to_key(Compare))

        for m in active:
            mes += '%s: %d凸' % (m.name, m.SortieCount())
            mes += '\n'

        await channel.send(mes)
        return False

    async def InputError(self, message, member : ClanMember, opt):
        for clan in clanhash.values():
            clan.SetInputChannel()
            if clan.inputchannel is None:
                await message.channel.send('%s[%d]' % (clan.guild.name, clan.guild.id))

        return False

    async def ServerMessage(self, message, member : ClanMember, opt):
        if not self.admin: return False
        if not message.author.guild_permissions.administrator: return False

        s = opt.split(' ')

        if len(s) < 2:
            await message.channel.send('オプションがありません')
            return False

        try:
            gindex = int(s[0])
        except ValueError:
            await message.channel.send('guildidが違います')
            return False

        if gindex in clanhash:
            clan = clanhash[gindex]

            clan.SetInputChannel()
            if clan.inputchannel is None:
                await message.channel.send('inputchannel が設定されていません')
                return False
            
            await clan.inputchannel.send(s[1])
        else:
            await message.channel.send('guildがありません')
        
        return False

    async def ServerLeave(self, message, member : ClanMember, opt):
        if not self.admin: return False
        if not message.author.guild_permissions.administrator: return False

        try:
            gindex = int(opt)
        except ValueError:
            await message.channel.send('guildidが違います')
            return False

        if gindex in clanhash:
            clan = clanhash[gindex]

            await clan.guild.leave()
            return False

        guildlist = [g for g in client.guilds if g.id == gindex]
        if 1 <= len(guildlist):
            await guildlist[0].leave()
            return False

        await message.channel.send('guildがありません')
        return False

    async def ZeroServerLeave(self, message, member : ClanMember, opt):
        if not self.admin: return False
        if not message.author.guild_permissions.administrator: return False

        server = []

        global clanhash

        for clan in clanhash.values():
            if clan.lap == 0:
                server.append(clan.guild)

        for clan in server:
            await clan.leave()

        return False

    async def GuildList(self, message, member : ClanMember, opt):
        if not self.admin: return False
        if not message.author.guild_permissions.administrator: return False

        guildname = opt

        global client

        if guildname == '':
            guildlist = [(idx, guild) for idx, guild in enumerate(client.guilds) if idx < 10]
        else:
            guildlist = [(idx, guild) for idx, guild in enumerate(client.guilds) if guildname in guild.name]

        await message.channel.send('\n'.join(['%d:%s' % (m[0], m[1].name) for m in guildlist]))

        return False

    async def GuildCommand(self, message, member : ClanMember, opt):
        if not self.admin: return False
        if not message.author.guild_permissions.administrator: return False

        return False

    async def DamageChannel(self, message, member : ClanMember, opt):
        try:
            bidx = int(opt) - 1
            if 0 <= bidx and bidx < BOSSNUMBER:
                self.damagecontrol[bidx].SetChannel(message.channel)
                self.TemporaryMessage(message.channel, 'チャンネルを設定しました')
            else:
                raise ValueError
        except ValueError:
            self.TemporaryMessage(message.channel, '数字が読み取れません')
            return False

        return True

    async def Remain(self, message, member : ClanMember, opt):
        try:
            sp = opt.split(' ')
            if len(sp) < 2:
                self.TemporaryMessage(message.channel, '[ボス番号] [残りHP] で入力してください')
                return False
            bidx = int(sp[0]) - 1
            if bidx < 0 or BOSSNUMBER <= bidx:
                raise ValueError
            remainhp = int(sp[1])

            dc = self.damagecontrol[bidx]
            dc.RemainHp(remainhp)
            await dc.SendResult()
        except ValueError:
            self.TemporaryMessage(message.channel, '数字が読み取れません')
            return False

        damagecontrol = self.damagecontrol[bidx]
        if 0 < remainhp:
            damagecontrol.SetChannel(message.channel)
            damagecontrol.RemainHp(remainhp)
            await damagecontrol.SendResult()
        else:
            self.TemporaryMessage(message.channel, 'キャンセルしました')

        return False

    async def Damage(self, message, member : ClanMember, opt):
        if message.channel.type == discord.ChannelType.private:
            self.TemporaryMessage(message.channel, 'このチャンネルでは使えません')
            return False
        
        if not member.IsAttack():
            self.TemporaryMessage(message.channel, '攻撃中ではありません')
            return False
        
        try:
            damage = int(opt)
        except ValueError:
            damage = 0

        damagecontrol =  self.damagecontrol[member.boss % BOSSNUMBER]
        if not damagecontrol.active:
            self.TemporaryMessage(message.channel, 'ダメコンを行っていません')
            return 
        damagecontrol.Damage(member, damage)
        await damagecontrol.SendResult()
        return False

    @staticmethod
    def GetIndexValue(d : Dict, idx : int):
        i = 0
        for value in d.values():
            if i == idx:
                return value
            i += 1
        return None

    async def PhantomDamage(self, message, member : ClanMember, opt):
        if message.channel.type == discord.ChannelType.private:
            await message.channel.send('このチャンネルでは使えません')
            return
        
        try:
            sp = opt.split(' ')
            damage = int(sp[0])
            m = int(sp[1])
        except ValueError:
            damage = 0
            m = 0

        damagecontrol = self.damagecontrol[0]
        if not damagecontrol.active:
            await message.channel.send('ダメコンを行っていません')
            return 
        
        mem = self.GetIndexValue(self.members, m)
        if mem is None: mem = member

        damagecontrol.Damage(mem, damage)
        await damagecontrol.SendResult()

    async def DamageTest(self, message, member : ClanMember, opt):
        
        mem = self.GetIndexValue(self.members, 1)
        if mem is None: mem = member
        mem.name = 'ダイチ'
        self.damagecontrol.Damage(mem, 600)

        mem = self.GetIndexValue(self.members, 2)
        if mem is None: mem = member
        mem.name = 'アサヒ'
        self.damagecontrol.Damage(mem, 800)

        mem = self.GetIndexValue(self.members, 3)
        if mem is None: mem = member
        mem.name = 'ミタカ'
        self.damagecontrol.Damage(mem, 740)

        await self.damagecontrol.SendResult()


    def ScoreCalc(self, opt):
        try:
            score = int(opt)
            return ClanScore.Calc(score)

        except ValueError:
            return None
    
    def FindChannel(self, guild : discord.Guild, name : str) -> Optional[discord.TextChannel]:
        if guild is None or guild.channels is None:
            return None
        for channel in guild.channels:
            if channel.name == name:
                return client.get_channel(channel.id)
        return None

    def AllowMessage(self, message):
        if message.channel.name == inputchannel: return True
        if message.guild.me in message.mentions: return True

        return False

    def RouteAnalyze(self, routestr : str):
        result = []
        addroute = 1
        try:
            if 0 <= routestr.find('-'):
                a = routestr.split('-')
                if 2 <= len(a):
                    lap = int(a[0]) - 1
                    bidx = int(a[1]) - 1
                    
                    if 0 <= bidx and bidx < BOSSNUMBER:
                        if lap < 0: lap = self.bosscount[bidx]
                        return [lap * BOSSNUMBER + bidx]
                    else:
                        raise ValueError

                return None

            while 0 < len(routestr) and routestr[0] == '+':
                addroute += 1
                routestr = routestr[1:]

            route = int(routestr)
            while 0 < route:
                bidx = route % 10 - 1
                if 0 <= bidx and bidx < BOSSNUMBER:
                    result.append(bidx + (self.bosscount[bidx] + addroute) * BOSSNUMBER)
                    route = route // 10
                else:
                    raise ValueError

            return result

        except ValueError:
            pass

        return result

    def SetOutputChannel(self):
        if self.outputchannel is None:
            self.outputchannel = self.FindChannel(self.guild, outputchannel)

    def SetInputChannel(self):
        if self.inputchannel is None:
            self.inputchannel = self.FindChannel(self.guild, inputchannel)

    async def on_message(self, message):
        if self.AllowMessage(message):
            member = self.GetMember(message.author)
            member.UpdateActive()

            content = re.sub('<[^>]*>', '', message.content).strip()

            if message.channel.name == inputchannel:
                self.inputchannel = message.channel

            self.SetOutputChannel()
            if self.outputchannel is None:
                await message.channel.send('%s というテキストチャンネルを作成してください' % (outputchannel))
                return False

            for cmdtuple in self.commandlist:
                for cmd in cmdtuple[0]:
                    opt = Command(content, cmd)
                    if opt is not None:
                        try:
                            return await cmdtuple[1](message, member, opt)
                        except ValueError:
                            pass
        
        member = self.members.get(message.author.id)
        if member is not None:
            member.UpdateActive()

            # 自動ダメコン計算
            for damagecontrol in self.damagecontrol:
                if damagecontrol.channel == message.channel:
                    await damagecontrol.on_message(self, member, message)
                    return False

        return False

    async def on_raw_message_delete(self, payload):
        if payload.cached_message is None:
            return False

        member = self.members.get(payload.cached_message.author.id)
        if member is None: return False

        if member.Revert(payload.message_id) is not None:
            member.Cancel()
            return True

        if member.taskkill == payload.message_id:
            member.taskkill = 0
            return True

        if payload.message_id in self.messagereaction:
            func = self.messagereaction[payload.message_id]
            if func.deletereaction is not None:
                return await func.deletereaction(member, payload)

        return False

    def emojiindex(self, emojistr):
        for idx, emoji in enumerate(self.emojis):
            if emoji == emojistr:
                return idx
        for idx, emoji in enumerate(self.emojisoverkill):
            if emoji == emojistr:
                return idx
        return None

    @staticmethod
    def FillList(list : List, count : int, data):
        l = len(list)
        if l < count:
            for _i in range(count - l):
                list.append(data)

    def AddDefeatTime(self, count):
        now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        self.FillList(self.defeatTime, count + 1, now)
        self.defeatTime[count] = now
    
    def BossCount(self, bossindex :int):
        return self.bossLap * BOSSNUMBER + bossindex

    async def on_raw_reaction_add(self, payload):
        member : ClanMember = self.members.get(payload.user_id)
        if member is None:
            return False
        
        if payload.message_id in self.messagereaction:
            react = self.messagereaction[payload.message_id]
            if react.addreaction is not None:
                return await react.addreaction(member, payload)

        return True

    async def on_raw_reaction_remove(self, payload):
        member : ClanMember = self.members.get(payload.user_id)
        if member is None:
            return False

        if payload.message_id in self.messagereaction:
            react = self.messagereaction[payload.message_id]
            if react.removereaction is not None:
                return await react.removereaction(member, payload)

        return False
                        
    def TotalSortieCount(self):
        count = 0
        for member in self.members.values():
            count += member.SortieCount()
        return count

    def GetLevelUpLap(self, lap) -> int:
        for lv in reversed(LevelUpLap):
            if lv - 1 <= lap:
                return lv - 1
        return 0

    def UpdateLapPlayer(self) -> float:
        lvup = self.GetLevelUpLap(self.bossLap)
        length = lvup - self.bossLap
        if length <= 0:
            return 0
        if MA_LAP < length:
            length = MA_LAP
        
        baselap = self.lapAttackCount[self.bossLap - length - 1] if 0 <= self.bossLap - length - 1 else 0
        self.lapplayer = (self.lapAttackCount[self.bossLap - 1] - baselap) / length
        return self.lapplayer

    def LapAverage(self) -> float:
        lvup = self.GetLevelUpLap(self.bossLap)
        length = lvup - self.bossLap
        if length <= 0:
            return 0
        if MA_LAP < length:
            length = MA_LAP
        
        baselap = self.lapAttackCount[self.bossLap - length - 1] if 0 <= self.bossLap - length - 1 else 0
        return (self.lapAttackCount[self.bossLap - 1] - baselap) / length

    def BossLevel(self, bossindex):
        level = 1
        lap = self.bosscount[bossindex]
        for lvlap in LevelUpLap:
            if lap < lvlap :
                return level
            level += 1
        return level

    def NextLvUpLap(self, bossindex):
        levelindex = self.BossLevel(bossindex) - 1

        if len(LevelUpLap) <= levelindex: return 0
        return (LevelUpLap[levelindex] - self.bossLap - 1)

    def MinLap(self):
        return min(self.bosscount)

    def DefeatBoss(self, bossindex : int):
        minlap = self.MinLap()
        self.bosscount[bossindex] += 1

        self.RemoveReserveExpire()

        self.damagecontrol[bossindex].SetBossHp(BossHpData[self.BossLevel(bossindex) - 1][bossindex][0])

        newlap = self.MinLap()
        if minlap != newlap:
            return newlap
        return None

    def UndefeatBoss(self, bossindex : int):
        if 0 < self.bosscount[bossindex]:
            self.bosscount[bossindex] -= 1

        self.damagecontrol[bossindex].SetBossHp(BossHpData[self.BossLevel(bossindex) - 1][bossindex][0])

    def AliveBossString(self):
        return ' '.join([self.numbermarks[m + 1] for m in self.AliveBoss()])

    def AddReserve(self, route : List[int], member : ClanMember, comment : str):
        for r in route:
            insertflag = True
            for m in self.reservelist:
                # 前の周なら登録しない
                bidx = m.boss % BOSSNUMBER
                blap = m.boss // BOSSNUMBER
                if blap < self.bosscount[bidx]: continue

                if m.boss == r and m.member == member:
                    m.SetComment(comment)
                    insertflag = False
                    break
            if insertflag:
                self.reservelist.append(ReserveUnit(r, member, comment))

    def RemoveReserve(self, func : Callable[[ReserveUnit], bool]):
        n = len([m for m in self.reservelist if func(m)])
        if 0 < n:
            self.reservelist = [m for m in self.reservelist if not func(m)]
        return n

    def RemoveReserveExpire(self):
        def Chk(boss):
            bidx = boss % BOSSNUMBER
            return self.bosscount[bidx] <= boss // BOSSNUMBER

        self.reservelist = [m for m in self.reservelist if Chk(m.boss)]


    def StatusAttack(self):
        attacklist : List[List[ClanMember]] = [ [] for _i in range(BOSSNUMBER) ]
        for member in self.members.values():
            if member.IsAttack():
                bidx = member.boss % BOSSNUMBER
                if member.boss // BOSSNUMBER == self.bosscount[bidx]:
                    attacklist[bidx].append(member)

        if sum([len(m) for m in attacklist]) == 0 : return ''

        s = '攻撃中\n'
        for at in attacklist:
            if 0 < len(at):
                namelist = [m.DecoName('nOT') for m in at]
                s += '%s %d人 %s\n' % (self.numbermarks[at[0].boss % BOSSNUMBER + 1], len(at), ' '.join(namelist))

        return s

    def NumberMark(self, l : List[int]):
        return [self.numbermarks[i] for i in l]

    def StatusBoss(self):
        s = ''
        minlap = self.MinLap()

        s += 'ボス情報 '
        bossmark = self.NumberMark([i + 1 for i in range(BOSSNUMBER) if self.bosscount[i] == minlap])
        s += '%d周目 %s' % (minlap + 1, ' '.join(bossmark))

        if (minlap + 2) in LevelUpLap:
            return s + '\n'

        bossmark = self.NumberMark([i + 1 for i in range(BOSSNUMBER) if self.bosscount[i] == minlap + 1])
        if 0 < len(bossmark):
            s += ' / %d周目 %s' % (minlap + 2, ' '.join(bossmark))

        return s + '\n'

    def StatusOverkill(self):
        s = ''
        time = [0] * 4
        tstr = ['フル', '長', '中', '短']

        for m in self.members.values():
            for t in m.attacktime:
                if t is not None and 0 < t:
                    if t == 90: time[0] += 1
                    elif 70 < t: time[1] += 1
                    elif 40 < t: time[2] += 1
                    else: time[3] += 1

        if 0 < sum(time):
            s += '持越 '
            s += '  '.join(['%s:%d' % (tstr[i], time[i]) for i in range(4) if 0 < time[i] ])
            s += '\n'

        return s

    def StatusMemberList(self):
        s = ''
        
        fulllist : List[List[ClanMember]] = [[] for _i in range(MAX_SORITE + 1) ]

        for m in self.members.values():
            if not m.DayFinish():
                fulllist[m.SortieCount()].append(m)

        for i, mem in enumerate(fulllist):
            if 0 < len(mem):
                s += '**残%d凸 %d人**\n' % (MAX_SORITE - i, len(mem))
                s += '  '.join([m.DecoName('nOT') for m in mem]) + '\n'
        
        unfinish = sum([len(m) for m in fulllist])
        if len(self.members) != unfinish:
            s += '**完凸 %d人**\n' % (len(self.members) - unfinish)
        
        return s

    def StatusReserveBoss(self, boss : int, members : List[ReserveUnit]):
        result = '%d-%d %s\n' % (boss // BOSSNUMBER + 1, boss % BOSSNUMBER + 1, '  '.join([m.member.DecoName('nO') for m in members]) )

        return result

    def StatusReserve(self):
        s = ''
        lapreserve : Dict[int, List[ReserveUnit]] = {}
        for r in self.reservelist:
            if r.boss in lapreserve:
                lapreserve[r.boss].append(r)
            else:
                lapreserve[r.boss] = [r]

        if 0 < len(lapreserve):
            def Compare(a : int, b : int):
                aidx = a % BOSSNUMBER
                bidx = b % BOSSNUMBER
                if aidx == bidx:
                    return sign(a - b)
                return sign(aidx - bidx)

            bosslist = sorted(lapreserve.keys(), key=cmp_to_key(Compare))

            s += '予約リスト\n'
            for lap in bosslist:
                s += self.StatusReserveBoss(lap, lapreserve[lap])
                
        return s

    def Status(self):
        s = ''

        s += self.StatusBoss()
        s += self.StatusAttack()
        s += self.StatusOverkill()

        s += '\n' + self.StatusMemberList()

        reserve = self.StatusReserve()
        if 0 < len(reserve):
            s += '\n' + reserve

        return s

def GetClan(guild, message) -> Clan:
    global clanhash
    g = clanhash.get(guild.id)

    if g is None:
        g = Clan(message.channel.id)
        clanhash[guild.id] = g

    if g.guild is None:
        g.guild = guild

    return g

def DateCalc(nowdate, deltadays):
    date = datetime.datetime.strptime(nowdate, '%m/%d')
    return (date + datetime.timedelta(days = deltadays)).strftime('%m/%d')

@tasks.loop(seconds=60)
async def loop():
    # 現在の時刻
    now = datetime.datetime.now()
    nowdate = now.strftime('%m/%d')
    nowtime = now.strftime('%H:%M')

    #毎日5時更新
    if nowtime == '05:00':
        Outlog(ERRFILE, '05:00 batch start len:%d ' % (len(clanhash)))

        message = 'おはようございます\nメンバーの情報をリセットしました'
        dailyfunc = None

        if nowdate == DateCalc(BATTLESTART, -1):
            message = 'おはようございます\n明日よりクランバトルです。状況報告に名前が出ていない人は、今日中に「凸」と発言してください。'
            dailyfunc = lambda clan: clan.FullReset()
            resetflag = True

        if nowdate == BATTLESTART:
            message = 'おはようございます\nいよいよクランバトルの開始です。頑張りましょう。'
            dailyfunc = lambda clan: clan.FullReset()
            resetflag = True

        if nowdate == BATTLEEND:
            message = 'おはようございます\n今日がクランバトル最終日です。24時が終了時刻ですので早めに攻撃を終わらせましょう。'
            resetflag = True
        
        for guildid, clan in clanhash.items():
            try:
                if dailyfunc is not None:
                    dailyfunc(clan)

                if resetflag or 0 < clan.TotalSortieCount():
                    clan.SetInputChannel()
                    if clan.inputchannel is not None:
                        await clan.inputchannel.send(message)

                    clan.Reset()
                    await Output(clan, clan.Status())
                else:
                    clan.Reset()

                clan.Save(guildid)

                cstr = 'input:ok'
                if clan.inputchannel is None:
                    cstr = 'input:ng channellen: %d' % len(clan.guild.channels)

                Outlog(ERRFILE, '%s flag:%s %s' % (clan.guild.name, resetflag, cstr))
            except Exception as e:
                Outlog(ERRFILE, 'error: %s e.args:%s' % (clan.guild.name if clan.guild is not None else 'Unknown', e.args))

        Outlog(ERRFILE, '05:00 batch end')

    #最終日の表示
    if nowtime == '00:00' and nowdate == DateCalc(BATTLEEND, 1):
        for clan in clanhash.values():
            if nowdate == BATTLEEND:
                if clan.inputchannel is not None:
                    message = 'クランバトル終了です。お疲れさまでした。'
                    await clan.inputchannel.send(message)
    
    #リポートの催促
    shtime = now
    for clan in clanhash.values():
        for member in clan.members.values():
            if member.reportlimit is not None and member.reportlimit < shtime:
                member.reportlimit = None

                if clan.inputchannel is not None:
                    message = '%s 凸結果の報告をお願いします' % member.mention
                    await clan.inputchannel.send(message)


# 起動時に動作する処理
@client.event
async def on_ready():
    # 起動したらターミナルにログイン通知が表示される
    print('ログインしました')
    Outlog(ERRFILE, "login.")

    global clanhash

    for guildid, clan in clanhash.items():
        if clan.guild is None:
            matchguild = [g for g in client.guilds if g.id == guildid]
            if len(matchguild) == 1:
                clan.SetGuild(matchguild[0])
                print(matchguild[0].name + " set.")

            else: 
                print('[%d] not found' % guildid)
        

async def VolatilityMessage(channel, mes, time):
    log = await channel.send(mes)
    await asyncio.sleep(time)
    await log.delete()

# メッセージ受信時に動作する処理
@client.event
async def on_message(message):
    # メッセージ送信者がBotだった場合は無視する
    if message.author.bot:
        return
    if message.channel.type == discord.ChannelType.text:
        clan = GetClan(message.guild, message)
        result = await clan.on_message(message)

        if result:
            clan.Save(message.guild.id)
            await Output(clan, clan.Status())
        return

@client.event
async def on_raw_message_delete(payload):
    clan = clanhash.get(payload.guild_id)

    if clan is not None and clan.IsInput(payload.channel_id):

        result = await clan.on_raw_message_delete(payload)
        if result:
            clan.Save(payload.guild_id)
            await Output(clan, clan.Status())

@client.event
async def on_raw_reaction_add(payload):
    clan = clanhash.get(payload.guild_id)

    if clan is not None:
        result = await clan.on_raw_reaction_add(payload)
        if result:
            clan.Save(payload.guild_id)
            await Output(clan, clan.Status())

@client.event
async def on_raw_reaction_remove(payload):

    clan = clanhash.get(payload.guild_id)

    if clan is not None and clan.IsInput(payload.channel_id):

        result = await clan.on_raw_reaction_remove(payload)
        if result:
            clan.Save(payload.guild_id)
            await Output(clan, clan.Status())

@client.event
async def on_member_remove(member):
    if member.bot: return

    clan = clanhash.get(member.guild.id)
    if clan is None: return

    if member.id in clan.members:
        del clan.members[member.id]
        clan.Save(member.guild.id)
        await Output(clan, clan.Status())

@client.event
async def on_guild_join(guild):
    Outlog(ERRFILE, "on_guild_join. %s" % guild.name)

@client.event
async def on_guild_remove(guild):
    global clanhash

    if guild.id in clanhash:
        del clanhash[guild.id]
        try:
            os.remove('clandata/%d.json' % (guild.id))
        except FileNotFoundError:
            pass

async def Output(clan : Clan, message : str):
    clan.SetOutputChannel()
    if clan.outputchannel is not None:
        if clan.outputlock == 1: return
        try:
            while clan.outputlock != 0:
                await asyncio.sleep(1)

            if clan.lastmessage is not None:
                clan.outputlock = 1
                try:
                    await clan.lastmessage.delete()
                except (discord.errors.NotFound, discord.errors.Forbidden):
                    pass
                clan.lastmessage = None

            try:
                clan.outputlock = 2
                clan.lastmessage = await clan.outputchannel.send(message)
            except discord.errors.Forbidden:
                clan.outputchannel = None
        finally:
            clan.outputlock = 0


def Outlog(filename, data):
    datetime_format = datetime.datetime.now()
    datestr = datetime_format.strftime("%Y/%m/%d %H:%M:%S")  # 2017/11/12 09:55:28
    print(datestr + " " + data, file=codecs.open(filename, 'a', 'utf-8'))

# ギルドデータ読み込み
files = glob.glob("./clandata/*.json")

for file in files:
    clanid = int (os.path.splitext(os.path.basename(file))[0])
    if clanid != 0:
        clan = Clan.Load(clanid)
        clanhash[clanid] = clan

GlobalStrage.Load()

#ループ処理実行
loop.start()

# Botの起動とDiscordサーバーへの接続
client.run(tokenkeycode.TOKEN)


