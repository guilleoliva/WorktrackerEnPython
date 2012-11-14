# all the imports
from datetime import datetime, timedelta
import sqlalchemy
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash

#SQLAlchemy related imports
from sqlalchemy import or_
from models import *

# TODO: define models in a different module!!!!
from windows import WorkOnWindow

# configuration
DATABASE = 'work.db'
DEBUG = True
SECRET_KEY = '7R%2$$y;P,42#3o(}|/^=2:&=6}9~e'
USERNAME = 'admin'
PASSWORD = '1p2o3i4u'

app = Flask(__name__)
app.config.from_object(__name__)

eng = create_engine('sqlite:///work.db', echo=True)
Base = declarative_base()

def connect_db():
    return sess

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    if not exception:
        g.db.commit()
    
    g.db.close()

#### APP VIEWS ####
@app.route('/', methods=['GET', 'POST'])
def unbound_items():
    projects = g.db.query(Project).order_by(Project.name).all()
    q = request.args.get('q')
    hl = []
    if q:
        hl = g.db.query(WorkOnWindow).filter(or_( \
        WorkOnWindow.window_title.like("%%%s%%" % q), \
        WorkOnWindow.window_class_1.like("%%%s%%" % q)), \
        WorkOnWindow.project == None).\
        order_by(WorkOnWindow.timestamp)
    work_on_window = g.db.query(WorkOnWindow).filter(WorkOnWindow.project == None).order_by(WorkOnWindow.timestamp)
    if request.method == 'POST':
        pid = request.form.get('project_select')
        project = g.db.query(Project).get(pid)
        wows = request.form.getlist('wow')
        for wowid in wows:
            wow = g.db.query(WorkOnWindow).get(wowid)
            wow.project = pid
        project.update_time()
    return render_template('unbound_items.html', work_on_window=work_on_window, hl=hl, projects=projects)

@app.route('/results/', defaults={'offset':0}, methods=['GET'])
@app.route('/results/<int:offset>', methods=['GET'])
def results(offset):
    if type(offset) != int:
        abort(404)
    if offset < 0:
        abort(404)
    
    offset = offset * (-1)
    projects = g.db.query(Project).all()
    now = datetime.now()
    one_day = timedelta(1)
    time_offset = timedelta(offset)
    t_from = datetime(now.year, now.month, now.day) + time_offset
    t_to = t_from + one_day
    times = {}
    total = 0
    idle = g.db.query(func.sum(WorkOnWindow.seconds_on_window)).filter( \
        WorkOnWindow.window_class_2 == "System-Idle", \
        WorkOnWindow.timestamp >= t_from, \
        WorkOnWindow.timestamp < t_to \
    ).first()
    idle = idle[0]
    if not idle: idle = 0
    for p in projects:
        t = g.db.query(func.sum(WorkOnWindow.seconds_on_window)).filter( \
            WorkOnWindow.project == p.id, \
            WorkOnWindow.timestamp >= t_from, \
            WorkOnWindow.timestamp < t_to \
        ).first()
        t = t[0]
        if not t: t = 0
        times[p.id] = t
        total = total + t
    offset = (offset) * -1
    return render_template('results.html', projects=projects, times=times, total=total, idle=idle, offset=offset)

@app.route('/results_details/<int:pid>/', defaults={'offset':0}, methods=['GET', 'POST'])
@app.route('/results_details/<int:pid>/<int:offset>', methods=['GET', 'POST'])
def results_details(pid, offset):
    if type(offset) != int:
        abort(404)
    if offset < 0:
        abort(404)
    
    offset = offset * (-1)
    project = g.db.query(Project).get(pid)
    if not project: abort(404)
    projects = g.db.query(Project).all()
    
    now = datetime.now()
    one_day = timedelta(1)
    time_offset = timedelta(offset)
    t_from = datetime(now.year, now.month, now.day) + time_offset
    t_to = t_from + one_day
    times = {}
    total = 0

    wow = g.db.query(WorkOnWindow).filter( \
        WorkOnWindow.project == project.id, \
        WorkOnWindow.timestamp >= t_from, \
        WorkOnWindow.timestamp < t_to \
    ).order_by(WorkOnWindow.timestamp)
    if request.method == 'POST':
        new_pid = request.form.get('project_select')
        new_project = g.db.query(Project).get(new_pid)
        wows = request.form.getlist('wow')
        for wowid in wows:
            this_wow = g.db.query(WorkOnWindow).get(wowid)
            this_wow.project = new_pid
        new_project.update_time()
        project.update_time()
    offset = (offset) * -1
    return render_template('results_details.html', projects=projects, active_project=project, work_on_window=wow, offset=offset)
    
@app.route('/project_show/', defaults={'id':None}, methods=['GET', 'POST'])
@app.route('/project_show/<int:id>', methods=['GET', 'POST'])
def project_show(id):
    project = None
    projects = g.db.query(Project).order_by(Project.name).all()
    
    if id:
        project = g.db.query(Project).get(id)
        if not project:
            raise Exception("Project not found")
        
    if request.method == 'POST':
        if project:
            project.name = request.form['name']
        else:
            project = Project(request.form['name'])
            g.db.add(project)
            g.db.commit()
    if not id and project:
        return redirect("%s%d" % (url_for('project_show'), project.id))
    return render_template('project_show.html', project=project, projects=projects)
        
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('unbound_items'))
    return render_template('login.html', error=error)
    
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('unbound_items'))
    
if __name__ == '__main__':
    app.run()
