from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

Base = declarative_base()

stars = [17,25,30,38,43,51,56,64]

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)




class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer)
    player_id = Column(Integer)
    win = Column(Integer)



class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer)
    players = Column(String)  # Serialized JSON string
    game = Column(Boolean)
    reg_id = Column(Integer)
    positions = Column(String)
    queue = Column(Integer)
    dice = Column(Integer)
    button_clicked = Column(Integer)
    sleeps = Column(Integer)

    def start_reg(self, message_id):
        self.reg_id = message_id
    
    def add_player(self, player):
        players_list = json.loads(self.players) if self.players else []
        players_list.append(player)
        self.players = json.dumps(players_list)
    
    def start_game(self):
        self.game = True
    
    def stop_game(self):
        self.game = False
        self.players = []
        self.reg_id = None
    
    def get_players(self):
        return json.loads(self.players) if self.players else []
    
    def get_positions(self):
        return json.loads(self.positions) if self.positions else []
    
    def next_quewe(self):
        if self.queue == 4:
            self.queue = 1
        else:
            self.queue += 1
    
    def check_stone(self, dice):
        self.dice = dice
        positions = self.get_positions()[self.queue-1]
        allow_stones = []



        for i,pos in enumerate(positions, 1):
            if (self.queue == 1 and 74-pos < self.dice) or (self.queue == 2 and 80-pos < self.dice) or (self.queue == 3 and 86-pos < self.dice) or (self.queue == 4 and 92-pos < self.dice):
                continue
            allow_stones.append(i)
        return allow_stones
    
    def forward(self, stone):
        positions = self.get_positions()
        pos = positions[self.queue-1][stone-1]
        for i in range(self.dice):
            if pos in (1,2,3,4):
                pos = 17
                continue
            elif pos in (5,6,7,8):
                pos = 30
                continue
            elif pos in (9,10,11,12):
                pos = 43
                continue
            elif pos in (13,14,15,16):
                pos = 56
                continue
            elif self.queue == 1 and pos == 67:
                pos = 69
                continue
            elif self.queue == 2 and pos == 68:
                pos = 17
                continue
            elif self.queue == 3 and pos == 68:
                pos = 17
                continue
            elif self.queue == 4 and pos == 68:
                pos = 17    
                continue        
            elif self.queue == 2 and pos == 28:
                pos = 75
                continue
            elif self.queue == 3 and pos == 41:
                pos = 81
                continue
            elif self.queue == 4 and pos == 54:
                pos = 87   
                continue     
            pos += 1
        
        if pos == 22:
            pos = 34
        elif pos == 35:
            pos = 47
        elif pos == 48:
            pos = 60
        elif pos == 61:
            pos = 21
        
        if pos in (69,70,71,72,73):
            pos = 74
        elif pos in (75,76,77,78,79):
            pos = 80
        elif pos in (81,82,83,84,85):
            pos = 86
        elif pos in (87,88,89,90,91):
            pos = 92
            
        positions[self.queue-1][stone-1] = pos
        self.positions = json.dumps(positions)
        session.commit()
        if (positions[0][0] == 74 and positions[0][1] == 74 and positions[0][2] == 74 and positions[0][3] == 74) or (
                positions[1][0] == 80 and positions[1][1] == 80 and positions[1][2] == 80 and positions[1][3] == 80) or (
                positions[2][0] == 86 and positions[2][1] == 86 and positions[2][2] == 86 and positions[2][3] == 86) or (
                positions[3][0] == 92 and positions[3][1] == 92 and positions[3][2] == 92 and positions[3][3] == 92):
            return 'win'
        for i, pl in enumerate(positions):
            if i == self.queue-1:
                continue
            for j, ps in enumerate(pl):
                if pos == ps and pos not in stars:
                    if i == 0 and j == 0:
                        positions[0][0] = 1
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 0 and j == 1:
                        positions[0][1] = 2
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 0 and j == 2:
                        positions[0][2] = 3
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 0 and j == 3:
                        positions[0][3] = 4
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 1 and j == 0:
                        positions[1][0] = 5
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 1 and j == 1:
                        positions[1][1] = 6
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 1 and j == 2:
                        positions[1][2] = 7
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 1 and j == 3:
                        positions[1][3] = 8
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 2 and j == 0:
                        positions[2][0] = 9
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 2 and j == 1:
                        positions[2][1] = 10
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 2 and j == 2:
                        positions[2][2] = 11
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 2 and j == 3:
                        positions[2][3] = 12
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 3 and j == 0:
                        positions[3][0] = 13
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 3 and j == 1:
                        positions[3][1] = 14
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 3 and j == 2:
                        positions[3][2] = 15
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    elif i == 3 and j == 3:
                        positions[3][3] = 16
                        self.positions = json.dumps(positions)
                        session.commit()
                        return ('back', i, j+1)
                    

        if self.dice != 6 and pos not in (74,80,86,92):
            self.next_quewe()
        session.commit()
        return 'forward'



engine = create_engine('sqlite:///memory.db')  # Use your actual database connection string
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


if __name__ == "__main__":
    # Example of usage



    # Creating a group instance
    group = Group(chat_id = 2525252)

    # Starting registration
    group.start_reg(12345)

    # Adding players
    group.add_player("Player1")
    group.add_player("Player2")
    group.add_player("Player3")

    # Starting the game
    group.start_game()

    # Adding the group to the database
    session.add(group)
    session.commit()

    # Querying the database
    queried_group = session.query(Group).filter_by(chat_id=2525252).first()

    # Accessing attributes
    print("Group ID:", queried_group.id)
    print("Players:", json.loads(queried_group.players) if queried_group.players else [])
    print("Is Game Started?", queried_group.game)
    print("Registration ID:", queried_group.reg_id)
