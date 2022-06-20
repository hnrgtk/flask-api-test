import os
import uuid
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import desc
from sqlalchemy_serializer import SerializerMixin

# Init app
app = Flask(__name__)
CORS(app)
basedir = os.path.abspath(os.path.dirname(__file__))

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(basedir, "db.sqlite")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Init db
db = SQLAlchemy(app)

def generate_uuid():
  return str(uuid.uuid4())

# Models
class Task(db.Model, SerializerMixin):
  __tablename__ = 'tasks'

  id = db.Column(db.Text, primary_key=True, default=generate_uuid)
  name = db.Column(db.String(50), nullable=False)
  description = db.Column(db.String(250), nullable=True)
  position = db.Column(db.Integer, nullable=False)
  column_id = db.Column(db.Integer, db.ForeignKey('columns.id'), nullable=False)

class Column(db.Model, SerializerMixin):
  __tablename__ = 'columns'

  id = db.Column(db.Text, primary_key=True, default=generate_uuid)
  name = db.Column(db.String(50), nullable=False)
  position = db.Column(db.Integer, nullable=False)
  tasks = db.relationship('Task', backref='columns_ref', lazy=True, order_by="Task.position.asc()")
  board_id = db.Column(db.Integer, db.ForeignKey('boards.id'), nullable=False)

class Board(db.Model, SerializerMixin):
  __tablename__ = 'boards'

  id = db.Column(db.Text, primary_key=True, default=generate_uuid)
  name = db.Column(db.String(50), nullable=False)
  columns = db.relationship('Column', backref='boards_ref', lazy=True, order_by="Column.position.asc()")

# Routes
@app.route('/board', methods=["POST"])
def create_board():
  data = request.get_json()

  board = Board(name=data['board_name'])
  db.session.add(board)
  db.session.commit()
  return board.to_dict(only=('id', 'name')), 201

@app.route('/board/add_column', methods=["POST"])
def add_column():
  data = request.get_json()

  new_column = Column(
    name = data['column_name'],
    position = data['column_position'],
    board_id = data['board_id']
  )
  db.session.add(new_column)

  board = Board.query.filter_by(id=data['board_id']).first()
  board.columns.append(new_column)

  db.session.add(board)
  db.session.commit()

  return {"message": "Column created successfully!"}, 201

@app.route('/board/add_task', methods=["POST"])
def add_task():
  data = request.get_json()
  column = Column.query.filter_by(id=data['column_id']).first()

  if column != None:
    new_task = Task(
      name = data.get('task_name'),
      description = data.get('task_description'),
      position = data.get('task_position'),
      column_id = data.get('column_id'),
    )
    db.session.add(column)
    db.session.add(new_task)
    db.session.commit()
    return {"message": "Task created successfully!"}, 201

  return {}, 400

@app.route('/board/move_task', methods=["POST"])
def move_task():
  data = request.get_json()
  column_id = data.get('column_id')
  task_id = data.get('task_id')
  new_position = data.get('task_position')

  results = db.session.query(Column, Task).filter(Column.id == column_id).join(Task, Task.id == task_id).first_or_404()

  order = [x for x in results[0].tasks]
  order.insert(new_position, results[1])

  for i, task in enumerate(order):
    task.position = i

    if task.id == task_id:
      task.column_id = column_id

  db.session.commit()

  return {"message": "Task moved successfully!"}, 200

@app.route('/board/<board_id>', methods=["GET"])
def get_board_by_id(board_id):
  board = db.session.query(Board).filter(Board.id == board_id).first()
  return board.to_dict(
    only=(
      'id', 'name', 
      'columns.id', 'columns.name', 'columns.position',
      'columns.tasks.id', 'columns.tasks.name', 
      'columns.tasks.description', 'columns.tasks.position'
  )), 200
  
@app.route("/boards", methods=["GET"])
def get_boards():
  boards = Board.query.all()
  return jsonify([board.to_dict(only=('id', 'name')) for board in boards]), 200

if __name__ == '__main__':
  db.create_all()
  app.run(debug=True, port=3333)