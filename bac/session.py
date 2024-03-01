from flask import (
    Blueprint,redirect,render_template,request,session,url_for,jsonify
)
from werkzeug.exceptions import abort
from bac.db import get_db
import random
import json

bp = Blueprint('session',__name__)

@bp.route('/',methods=('GET','POST'))
def index():
    if request.method == 'POST':
        return redirect(url_for('auth.login'),code=307)
        
    settings = {
        'title':'Bac++',
        'subtitle': 'Bactériologie médicale',  
        'body':'Test tes connaissances en bactériologie médicale',
        'photo':"static/images/home.png"
    }
    return render_template('session/index.html', **settings)

@bp.route('/start',methods=('GET',))
def start():
    training = True #TODO should be in the user's profile
    questions = get_questions() 
    if len(questions) == 0:
        return redirect(url_for('session.index'))
    session['score'] = 0
    session['solutions'] = [q['solution'] for q in questions]    
    if not training:
        for question in questions:
            del question['solution']    
    return render_template('session/question.html',questions=questions)

@bp.route('/answer',methods=('GET','POST',))
def answer():
    solutions = session.get('solutions',[])
    score = session.get('score',0)
    if request.method == 'POST':
        error = None
        score = request.form.get('score','0')
        try:
            score = int(score)
        except:
            score = 0
        answers = request.form.get('answer',[])
        answers = json.loads(answers)       
        if len(answers) == len(solutions):
            sc = 0
            for answer,solution in zip(answers,solutions):
                if check_answer(answer,solution):
                    sc += 1            
            if score > 0 and sc != score:
                print("Bad score",sc,score) 
            score = sc
        else:
            print(answers)
            print(solutions)
            error = "Wrong number of answers " 
        print('Score:', score)
        session['score'] = score
        if error is not None:
            print(error)
            return jsonify(error=error), 400
        return jsonify({'msg':'Answers submited'})
    
    total = len(solutions)
    return render_template('session/result.html',score=score,total=total)

def check_answer(answer,solution):
    ret = True
    for item in answer:
        if not item in solution:
            ret = False
    for item in solution:
        if not item in answer:
            ret = False
    return ret

def get_questions(n = 10):
    questions = []
    db = get_db()     
    rows = db.execute('SELECT * FROM question'
                      ' ORDER BY RANDOM() LIMIT ?',(n,)).fetchall() 
    for row in rows:
        q = load_question(dict(row))
        questions.append(q) 
    return questions

def clean_dict(row):    
    row = dict(row)
    result = {}
    for key,value in row.items():
        if value is None:
            value = ''
        result[key] = value
    return result

def load_question(question):
    db = get_db()
    id = question.get('id',0)
    answer = db.execute(
        'SELECT * FROM answer WHERE question_id == ?'
        ,(id,)
    ).fetchall()    

    answer = [clean_dict(item) for item in answer] 
    size = len(answer)
    random.shuffle(answer)
    solution = [ind for ind in range(size) if answer[ind]['solution'] > 0]
    for item in answer:
        del item['solution']
    del question['created']

    question['choice'] = answer
    question['solution'] = solution
    question['multi'] = 1 if len(solution) > 1  else 0

    image = db.execute(
        'SELECT * FROM  image WHERE question_id == ?'
        ,(id,)
    ).fetchall() 
    question['image'] =  [dict(img) for img in image]
    return question