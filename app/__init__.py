from flask import Flask, jsonify
from flask_restx import Api
from config import config
from app.extensions import db, jwt, bcrypt, limiter, cors

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    db.init_app(app); jwt.init_app(app); bcrypt.init_app(app); limiter.init_app(app); cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    authorizations = {'Bearer': {'type':'apiKey','in':'header','name':'Authorization','description':'Enter: Bearer <your_token>'}}
    api = Api(app, version='1.0', title='EduFlow API',
        description='🎓 AI-powered Course Platform API | JWT Auth | Roles | Gemini AI | Analytics\n\nQuick Start: 1. POST /api/auth/register  2. POST /api/auth/login  3. Click Authorize → paste Bearer <token>',
        doc='/api/docs', prefix='/api', authorizations=authorizations, security='Bearer')

    from app.routes import auth_ns, courses_ns, analytics_ns, users_ns
    api.add_namespace(auth_ns,      path='/auth')
    api.add_namespace(courses_ns,   path='/courses')
    api.add_namespace(analytics_ns, path='/analytics')
    api.add_namespace(users_ns,     path='/users')

    @app.errorhandler(404)
    def not_found(e): return jsonify({'message':'Resource not found'}), 404
    @app.errorhandler(429)
    def rate_limited(e): return jsonify({'message':'Rate limit exceeded'}), 429
    @jwt.expired_token_loader
    def expired(h,p): return jsonify({'message':'Token expired — please login again'}), 401
    @jwt.unauthorized_loader
    def missing(r): return jsonify({'message':f'Authorization required — {r}'}), 401

    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')

    @app.route('/health')
    def health(): return jsonify({'status':'ok','service':'EduFlow API','version':'1.0'}), 200

    with app.app_context():
        db.create_all()
        _seed()
    return app

def _seed():
    from app.models import User, Course, Module, Lesson, Enrollment, UserRole, CourseCategory, CourseLevel
    from app.extensions import bcrypt as bc
    if User.query.count() > 0: return

    admin = User(name='Admin',email='admin@eduflow.com',password=bc.generate_password_hash('admin123').decode(),role=UserRole.ADMIN)
    inst  = User(name='Satwik Pasunoori',email='satwik@eduflow.com',password=bc.generate_password_hash('satwik123').decode(),role=UserRole.INSTRUCTOR)
    stud  = User(name='Demo Student',email='student@eduflow.com',password=bc.generate_password_hash('student123').decode(),role=UserRole.STUDENT)
    db.session.add_all([admin,inst,stud]); db.session.flush()

    courses_data = [
        {'title':'Python for Backend Development','description':'Master Python for building robust backend systems with Flask and REST APIs.','category':CourseCategory.PROGRAMMING,'level':CourseLevel.BEGINNER,'price':0.0,'is_published':True,'rating':4.8,
         'modules':[{'title':'Python Fundamentals','lessons':[('Variables & Data Types',20,True),('Functions & Modules',25,True),('OOP in Python',30,False)]},{'title':'Flask Web Framework','lessons':[('Flask Setup & Routing',20,True),('Request & Response',25,False),('Flask Blueprints',30,False)]}]},
        {'title':'Flask REST API Masterclass','description':'Build production-grade REST APIs with Flask, SQLAlchemy, and JWT authentication.','category':CourseCategory.WEB_DEV,'level':CourseLevel.INTERMEDIATE,'price':999.0,'is_published':True,'rating':4.9,
         'modules':[{'title':'REST API Design','lessons':[('REST Principles',15,True),('HTTP Methods & Status Codes',20,True),('API Versioning',20,False)]},{'title':'Auth & Security','lessons':[('JWT Authentication',30,False),('Role-Based Access',25,False),('Rate Limiting',20,False)]}]},
        {'title':'AI & ML with Python','description':'From ML fundamentals to deploying AI models and working with LLM APIs.','category':CourseCategory.AI_ML,'level':CourseLevel.INTERMEDIATE,'price':1499.0,'is_published':True,'rating':4.7,
         'modules':[{'title':'ML Fundamentals','lessons':[('What is Machine Learning?',20,True),('Data Preprocessing',30,False),('Supervised vs Unsupervised',25,False)]}]},
    ]

    for cd in courses_data:
        mods = cd.pop('modules')
        course = Course(**cd, instructor_id=inst.id)
        db.session.add(course); db.session.flush()
        for i,md in enumerate(mods):
            lessons = md.pop('lessons')
            module = Module(title=md['title'],order=i+1,course_id=course.id)
            db.session.add(module); db.session.flush()
            for j,(lt,dur,free) in enumerate(lessons):
                db.session.add(Lesson(title=lt,duration=dur,is_free=free,order=j+1,module_id=module.id,content=f'Content for: {lt}'))

    db.session.flush()
    first = Course.query.first()
    if first: db.session.add(Enrollment(student_id=stud.id,course_id=first.id))
    db.session.commit()
    print('Seed done: admin@eduflow.com/admin123 | satwik@eduflow.com/satwik123 | student@eduflow.com/student123')
