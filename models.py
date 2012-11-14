from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import create_engine
from sqlalchemy import Column, Integer, String, DateTime, Sequence, ForeignKey, func
from sqlalchemy.types import DateTime
from sqlalchemy.orm import sessionmaker, relationship, backref

import os
import sys
path = os.path.dirname(os.path.abspath(sys.argv[0]))
eng = create_engine('sqlite:///'+path+'\\work.db', echo=True)
Base = declarative_base()
Session = sessionmaker(bind = eng)
sess = Session()

class WorkOnWindow(Base):
    __tablename__ = 'work_on_window'
    
    id = Column(Integer, Sequence('work_on_window_seq'), primary_key=True)
    timestamp = Column(DateTime)
    window_class_1 = Column(String(100))
    window_class_2 = Column(String(100))
    window_title = Column(String(300))
    seconds_on_window = Column(Integer)
    project = Column(Integer, ForeignKey('projects.id'))
    
    def __init__(self, window_class, window_title, seconds_on_window):
        self.timestamp = datetime.now()
        self.window_class_1 = window_class[0]
        self.window_class_2 = window_class[1]
        self.window_title = window_title.decode('ISO-8859-1')
        self.seconds_on_window = seconds_on_window

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, Sequence('projects_seq'), primary_key=True)
    name = Column(String(500))
    time_spent = Column(Integer)
    work_on_window = relationship('WorkOnWindow')
    
    def __init__(self, name):
        self.name = name
        self.time_spent = 0
        
    def update_time(self):
        q_time_spent = sess.query(func.sum(WorkOnWindow.seconds_on_window)).filter(WorkOnWindow.project == self.id).first()
        self.time_spent = q_time_spent[0]
        return self.time_spent