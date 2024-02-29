
from flask import (
    Blueprint,redirect,render_template,request,url_for,current_app,jsonify
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
import os

from bac.auth import su_required
from bac.db import get_db

bp = Blueprint('admin',__name__,url_prefix='/admin')

@bp.route('/viewquest')
@su_required
def viewquest():
    questions = []
    db = get_db()     
    rows = db.execute(
        'SELECT * FROM question'
    ).fetchall()    
    for row in rows:
        question = load_question(row)
        questions.append(question)

    return render_template('admin/viewquest.html',questions=questions)

@bp.route('/<int:id>/update', methods=('GET','POST'))
@su_required
def editquest(id):
    if request.method == 'POST':
        if len(request.form) > 0:
            title = request.form.get('title')
            body = request.form.get('body')    
            if isinstance(body,str):
                body = body.strip() 

            legend = request.form.get('legend')
            choices = []
            choice = request.form.get('choice')
            if choice is not None:
                choices.append(choice)
            else:
                for i in range(5):
                    choice = request.form.get('choice'+str(i))
                    if choice is not None:
                        choices.append(choice)

            answers = []        
            answer = request.form.get('answer')
            if answer is not None:
                answers.append(answer)
            else:
                for i in range(5):
                    answer = request.form.get('answer'+str(i))
                    if answer is not None:
                        answers.append(answer)

            error = None
            if not title:
                error = 'Title is required'
            if len(answers) == 0:
                error = 'Answer is required'

            if error is not None:
                # Debug
                print('Error',error)
                return jsonify(error=error), 400
            else:
                db = get_db()
                if id > 0:
                    print('Update ',id )
                    db.execute(
                    'UPDATE question SET title = ?, body = ? , legend = ? '
                        ' WHERE id = ?',
                        (title,body,legend,id))
                else:
                    print('Insert ',id )
                    cursor = db.execute(
                        'INSERT INTO question (title,body,legend)'
                            ' VALUES (?,?,?)',
                            (title,body,legend))            
                    id = cursor.lastrowid
                
                db.execute('DELETE FROM answer WHERE question_id = ?',(id,))
                for answer in answers:
                    db.execute(
                        'INSERT INTO answer (title,question_id,solution)'
                        ' VALUES (?,?,?)',
                        (answer,id,1))
                    
                if choices is not None:
                    for answer in choices:
                        db.execute(
                            'INSERT INTO answer (title,question_id,solution)'
                            ' VALUES (?,?,?)',
                            (answer,id,0))

                db.execute('DELETE FROM image WHERE question_id = ?',(id,))
                images = []
                for i in range(5):
                    image = request.form.get('image'+str(i))
                    if image is not None:
                        images.append(image)
                        
                for path in images:
                    print('Keep',path)
                    db.execute(
                        'INSERT INTO image (question_id,path)'
                        ' VALUES (?,?)',
                        (id,path))

                for key,file in request.files.items():
                    print('Upload',key,file)
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        path = os.path.join(current_app.config['UPLOAD_FOLDER'],filename)
                        file.save(path)
                        path = os.path.sep+os.path.relpath(path,'bac')
                        db.execute(
                            'INSERT INTO image (question_id,path)'
                            ' VALUES (?,?)',
                            (id,path))
                db.commit() 
        return jsonify({'msg':'Question submited'})

    if id > 0:
        question = get_question(id)
    else:
        question = None
    return render_template('admin/editquest.html',question=question) 

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/<int:id>/deletequest')
@su_required
def deletequest(id):
    db = get_db()
    db.execute('DELETE FROM answer WHERE question_id = ?',(id,))
    db.execute('DELETE FROM image WHERE question_id = ?',(id,))
    db.execute('DELETE FROM question WHERE id = ?',(id,))
    db.commit()
    return redirect(url_for('admin.viewquest'))

def clean_dict(row):    
    row = dict(row)
    result = {}
    for key,value in row.items():
        if value is None:
            value = ''
        result[key] = value
    return result

def load_question(row):
    db = get_db()
    id = row['id']
    question = dict(row)
    answer = db.execute(
        'SELECT * FROM answer WHERE question_id == ?'
        ,(id,)
    ).fetchall()    

    answer = [clean_dict(item) for item in answer] 
    question['answer'] = list(filter(
        lambda item: item['solution'] > 0,answer))
    question['choice'] = list(filter(
        lambda item: item['solution'] == 0, answer))
    
    image = db.execute(
        'SELECT * FROM image WHERE question_id == ?'
        ,(id,)
    ).fetchall()    
    question['image'] =  [dict(img) for img in image]
    return question

def get_question(id):
    question = get_db().execute(
        'SELECT * FROM question WHERE id == ?',(id,)
    ).fetchone()

    if question is None:
        abort(404,f"No question found")

    question = load_question(question)
    return question
