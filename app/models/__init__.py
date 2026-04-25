from app.extensions import db
from datetime import datetime
import enum

class UserRole(str, enum.Enum):
    ADMIN='admin'; INSTRUCTOR='instructor'; STUDENT='student'

class CourseLevel(str, enum.Enum):
    BEGINNER='beginner'; INTERMEDIATE='intermediate'; ADVANCED='advanced'

class CourseCategory(str, enum.Enum):
    PROGRAMMING='programming'; DATA_SCIENCE='data_science'; WEB_DEV='web_development'
    AI_ML='ai_ml'; DATABASE='database'; DEVOPS='devops'; OTHER='other'

class User(db.Model):
    __tablename__='users'
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100),nullable=False)
    email=db.Column(db.String(120),unique=True,nullable=False,index=True)
    password=db.Column(db.String(255),nullable=False)
    role=db.Column(db.Enum(UserRole),default=UserRole.STUDENT,nullable=False)
    is_active=db.Column(db.Boolean,default=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    courses=db.relationship('Course',backref='instructor',lazy='dynamic',foreign_keys='Course.instructor_id')
    enrollments=db.relationship('Enrollment',backref='student',lazy='dynamic')
    def to_dict(self):
        return {'id':self.id,'name':self.name,'email':self.email,'role':self.role.value,'is_active':self.is_active,'created_at':self.created_at.isoformat()}

class Course(db.Model):
    __tablename__='courses'
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(200),nullable=False)
    description=db.Column(db.Text,default='')
    category=db.Column(db.Enum(CourseCategory),default=CourseCategory.OTHER)
    level=db.Column(db.Enum(CourseLevel),default=CourseLevel.BEGINNER)
    price=db.Column(db.Float,default=0.0)
    thumbnail=db.Column(db.String(255),default='')
    is_published=db.Column(db.Boolean,default=False)
    ai_summary=db.Column(db.Text,default='')
    rating=db.Column(db.Float,default=0.0)
    instructor_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
    modules=db.relationship('Module',backref='course',lazy='dynamic',cascade='all, delete-orphan',order_by='Module.order')
    enrollments=db.relationship('Enrollment',backref='course',lazy='dynamic',cascade='all, delete-orphan')
    @property
    def total_lessons(self): return sum(m.lessons.count() for m in self.modules)
    @property
    def enrollment_count(self): return self.enrollments.count()
    def to_dict(self,detailed=False):
        data={'id':self.id,'title':self.title,'description':self.description,'category':self.category.value,'level':self.level.value,'price':self.price,'thumbnail':self.thumbnail,'is_published':self.is_published,'rating':self.rating,'ai_summary':self.ai_summary,'instructor':{'id':self.instructor.id,'name':self.instructor.name},'total_lessons':self.total_lessons,'enrollment_count':self.enrollment_count,'created_at':self.created_at.isoformat()}
        if detailed: data['modules']=[m.to_dict(with_lessons=True) for m in self.modules]
        return data

class Module(db.Model):
    __tablename__='modules'
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(200),nullable=False)
    description=db.Column(db.Text,default='')
    order=db.Column(db.Integer,default=0)
    course_id=db.Column(db.Integer,db.ForeignKey('courses.id'),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    lessons=db.relationship('Lesson',backref='module',lazy='dynamic',cascade='all, delete-orphan',order_by='Lesson.order')
    def to_dict(self,with_lessons=False):
        data={'id':self.id,'title':self.title,'description':self.description,'order':self.order,'lesson_count':self.lessons.count(),'course_id':self.course_id}
        if with_lessons: data['lessons']=[l.to_dict() for l in self.lessons]
        return data

class Lesson(db.Model):
    __tablename__='lessons'
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(200),nullable=False)
    content=db.Column(db.Text,default='')
    video_url=db.Column(db.String(255),default='')
    duration=db.Column(db.Integer,default=0)
    order=db.Column(db.Integer,default=0)
    is_free=db.Column(db.Boolean,default=False)
    module_id=db.Column(db.Integer,db.ForeignKey('modules.id'),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    progress=db.relationship('LessonProgress',backref='lesson',lazy='dynamic',cascade='all, delete-orphan')
    def to_dict(self):
        return {'id':self.id,'title':self.title,'content':self.content,'video_url':self.video_url,'duration':self.duration,'order':self.order,'is_free':self.is_free,'module_id':self.module_id}

class Enrollment(db.Model):
    __tablename__='enrollments'
    __table_args__=(db.UniqueConstraint('student_id','course_id'),)
    id=db.Column(db.Integer,primary_key=True)
    student_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    course_id=db.Column(db.Integer,db.ForeignKey('courses.id'),nullable=False)
    enrolled_at=db.Column(db.DateTime,default=datetime.utcnow)
    completed=db.Column(db.Boolean,default=False)
    lesson_progress=db.relationship('LessonProgress',backref='enrollment',lazy='dynamic',cascade='all, delete-orphan')
    @property
    def progress_percent(self):
        total=sum(m.lessons.count() for m in self.course.modules)
        if total==0: return 0
        done=self.lesson_progress.filter_by(completed=True).count()
        return round((done/total)*100)
    def to_dict(self):
        return {'id':self.id,'course':{'id':self.course.id,'title':self.course.title},'enrolled_at':self.enrolled_at.isoformat(),'completed':self.completed,'progress_percent':self.progress_percent}

class LessonProgress(db.Model):
    __tablename__='lesson_progress'
    __table_args__=(db.UniqueConstraint('enrollment_id','lesson_id'),)
    id=db.Column(db.Integer,primary_key=True)
    enrollment_id=db.Column(db.Integer,db.ForeignKey('enrollments.id'),nullable=False)
    lesson_id=db.Column(db.Integer,db.ForeignKey('lessons.id'),nullable=False)
    completed=db.Column(db.Boolean,default=False)
    completed_at=db.Column(db.DateTime,nullable=True)
