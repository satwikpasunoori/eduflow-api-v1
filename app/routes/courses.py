from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Course, Module, Lesson, Enrollment, LessonProgress, User, UserRole, CourseCategory, CourseLevel
from app.utils import role_required, generate_ai_summary, paginate_query

ns = Namespace('courses', description='Course management — CRUD, search, filter')

course_input = ns.model('CourseInput', {
    'title':       fields.String(required=True, example='Python for Beginners'),
    'description': fields.String(example='Learn Python from scratch'),
    'category':    fields.String(example='programming', enum=[c.value for c in CourseCategory]),
    'level':       fields.String(example='beginner', enum=[l.value for l in CourseLevel]),
    'price':       fields.Float(example=0.0),
    'thumbnail':   fields.String(example='https://example.com/thumb.jpg'),
    'is_published':fields.Boolean(example=True),
})

module_input = ns.model('ModuleInput', {
    'title':       fields.String(required=True, example='Getting Started'),
    'description': fields.String(example='Introduction and setup'),
    'order':       fields.Integer(example=1),
})

lesson_input = ns.model('LessonInput', {
    'title':     fields.String(required=True, example='Installing Python'),
    'content':   fields.String(example='Step by step installation guide...'),
    'video_url': fields.String(example='https://youtube.com/watch?v=xxx'),
    'duration':  fields.Integer(example=15),
    'order':     fields.Integer(example=1),
    'is_free':   fields.Boolean(example=True),
})


# ── /courses ──────────────────────────────────────────────────
@ns.route('')
class CourseList(Resource):

    @ns.doc(description='List all published courses. Filter by category, level, price. Search by title.')
    def get(self):
        """List courses — with search, filter, sort, pagination"""
        q       = request.args.get('q', '').strip()
        cat     = request.args.get('category', '')
        level   = request.args.get('level', '')
        min_p   = request.args.get('min_price', type=float)
        max_p   = request.args.get('max_price', type=float)
        sort    = request.args.get('sort', 'newest')
        page    = request.args.get('page', 1, type=int)
        per_p   = request.args.get('per_page', 10, type=int)

        query = Course.query.filter_by(is_published=True)

        if q:
            query = query.filter(Course.title.ilike(f'%{q}%'))
        if cat:
            try:    query = query.filter_by(category=CourseCategory(cat))
            except: pass
        if level:
            try:    query = query.filter_by(level=CourseLevel(level))
            except: pass
        if min_p is not None:
            query = query.filter(Course.price >= min_p)
        if max_p is not None:
            query = query.filter(Course.price <= max_p)

        if sort == 'rating':
            query = query.order_by(Course.rating.desc())
        elif sort == 'price_asc':
            query = query.order_by(Course.price.asc())
        elif sort == 'price_desc':
            query = query.order_by(Course.price.desc())
        else:
            query = query.order_by(Course.created_at.desc())

        meta, items = paginate_query(query, page, per_p)
        return {'meta': meta, 'courses': [c.to_dict() for c in items]}, 200

    @jwt_required()
    @ns.expect(course_input, validate=True)
    @ns.doc(security='Bearer', description='Create a new course (Instructor or Admin only)')
    def post(self):
        """Create course — instructor/admin only"""
        user = User.query.get(get_jwt_identity())
        if user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
            return {'message': 'Only instructors and admins can create courses'}, 403
        data = request.json
        course = Course(
            title=data['title'],
            description=data.get('description', ''),
            category=CourseCategory(data.get('category', 'other')),
            level=CourseLevel(data.get('level', 'beginner')),
            price=data.get('price', 0.0),
            thumbnail=data.get('thumbnail', ''),
            is_published=data.get('is_published', False),
            instructor_id=user.id,
        )
        db.session.add(course)
        db.session.commit()
        return {'message': 'Course created', 'course': course.to_dict()}, 201


# ── /courses/<id> ─────────────────────────────────────────────
@ns.route('/<int:course_id>')
class CourseDetail(Resource):

    def get(self, course_id):
        """Get course detail — with all modules and lessons"""
        course = Course.query.get_or_404(course_id)
        return course.to_dict(detailed=True), 200

    @jwt_required()
    @ns.expect(course_input)
    @ns.doc(security='Bearer')
    def put(self, course_id):
        """Update course — owner or admin only"""
        user   = User.query.get(get_jwt_identity())
        course = Course.query.get_or_404(course_id)
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return {'message': 'Not authorized to edit this course'}, 403
        data = request.json or {}
        for field in ['title', 'description', 'price', 'thumbnail', 'is_published']:
            if field in data:
                setattr(course, field, data[field])
        if 'category' in data:
            try: course.category = CourseCategory(data['category'])
            except: pass
        if 'level' in data:
            try: course.level = CourseLevel(data['level'])
            except: pass
        db.session.commit()
        return {'message': 'Course updated', 'course': course.to_dict()}, 200

    @jwt_required()
    @ns.doc(security='Bearer')
    def delete(self, course_id):
        """Delete course — owner or admin only"""
        user   = User.query.get(get_jwt_identity())
        course = Course.query.get_or_404(course_id)
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return {'message': 'Not authorized to delete this course'}, 403
        db.session.delete(course)
        db.session.commit()
        return {'message': 'Course deleted successfully'}, 200


# ── /courses/<id>/ai-summary ──────────────────────────────────
@ns.route('/<int:course_id>/ai-summary')
class AISummary(Resource):

    @jwt_required()
    @ns.doc(security='Bearer', description='Generate AI-powered course description and learning outcomes using Gemini API. Works without API key too — returns smart template.')
    def post(self, course_id):
        """AI Summary — generate course description with Gemini AI"""
        user   = User.query.get(get_jwt_identity())
        course = Course.query.get_or_404(course_id)
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return {'message': 'Only the course owner can generate AI summaries'}, 403

        result = generate_ai_summary(course.title, course.category.value, course.level.value)

        course.ai_summary = result['description']
        if not course.description:
            course.description = result['description']
        db.session.commit()

        return {
            'message': 'AI summary generated successfully',
            'ai_powered': result.get('ai_powered', False),
            'note': result.get('note', ''),
            'description': result['description'],
            'learning_outcomes': result['learning_outcomes'],
            'course': course.to_dict(),
        }, 200


# ── /courses/<id>/modules ─────────────────────────────────────
@ns.route('/<int:course_id>/modules')
class ModuleList(Resource):

    def get(self, course_id):
        """List all modules in a course"""
        course  = Course.query.get_or_404(course_id)
        modules = course.modules.order_by(Module.order).all()
        return {'modules': [m.to_dict(with_lessons=True) for m in modules]}, 200

    @jwt_required()
    @ns.expect(module_input, validate=True)
    @ns.doc(security='Bearer')
    def post(self, course_id):
        """Add a module to course — instructor/admin only"""
        user   = User.query.get(get_jwt_identity())
        course = Course.query.get_or_404(course_id)
        if course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return {'message': 'Not authorized'}, 403
        data = request.json
        module = Module(
            title=data['title'],
            description=data.get('description', ''),
            order=data.get('order', course.modules.count() + 1),
            course_id=course_id,
        )
        db.session.add(module)
        db.session.commit()
        return {'message': 'Module created', 'module': module.to_dict()}, 201


# ── /modules/<id>/lessons ─────────────────────────────────────
@ns.route('/modules/<int:module_id>/lessons')
class LessonList(Resource):

    @jwt_required()
    @ns.expect(lesson_input, validate=True)
    @ns.doc(security='Bearer')
    def post(self, module_id):
        """Add a lesson to a module — instructor/admin only"""
        user   = User.query.get(get_jwt_identity())
        module = Module.query.get_or_404(module_id)
        if module.course.instructor_id != user.id and user.role != UserRole.ADMIN:
            return {'message': 'Not authorized'}, 403
        data = request.json
        lesson = Lesson(
            title=data['title'],
            content=data.get('content', ''),
            video_url=data.get('video_url', ''),
            duration=data.get('duration', 0),
            order=data.get('order', module.lessons.count() + 1),
            is_free=data.get('is_free', False),
            module_id=module_id,
        )
        db.session.add(lesson)
        db.session.commit()
        return {'message': 'Lesson created', 'lesson': lesson.to_dict()}, 201


# ── /courses/<id>/enroll ──────────────────────────────────────
@ns.route('/<int:course_id>/enroll')
class EnrollCourse(Resource):

    @jwt_required()
    @ns.doc(security='Bearer', description='Enroll the logged-in student in a course')
    def post(self, course_id):
        """Enroll — join a course"""
        user   = User.query.get(get_jwt_identity())
        course = Course.query.get_or_404(course_id)
        if not course.is_published:
            return {'message': 'Course is not published yet'}, 400
        existing = Enrollment.query.filter_by(student_id=user.id, course_id=course_id).first()
        if existing:
            return {'message': 'Already enrolled in this course'}, 409
        enr = Enrollment(student_id=user.id, course_id=course_id)
        db.session.add(enr)
        db.session.commit()
        return {'message': f'Enrolled in "{course.title}" successfully', 'enrollment': enr.to_dict()}, 201


# ── /courses/<id>/progress ────────────────────────────────────
@ns.route('/<int:course_id>/progress')
class CourseProgress(Resource):

    @jwt_required()
    @ns.doc(security='Bearer')
    def get(self, course_id):
        """Progress — get my progress in a course"""
        user = User.query.get(get_jwt_identity())
        enr  = Enrollment.query.filter_by(student_id=user.id, course_id=course_id).first()
        if not enr:
            return {'message': 'Not enrolled in this course'}, 404
        completed_lessons = [lp.lesson_id for lp in enr.lesson_progress.filter_by(completed=True).all()]
        return {
            'course_id': course_id,
            'progress_percent': enr.progress_percent,
            'completed_lessons': completed_lessons,
            'enrolled_at': enr.enrolled_at.isoformat(),
        }, 200


# ── /lessons/<id>/complete ────────────────────────────────────
@ns.route('/lessons/<int:lesson_id>/complete')
class CompleteLesson(Resource):

    @jwt_required()
    @ns.doc(security='Bearer', description='Mark a lesson as completed and track progress')
    def post(self, lesson_id):
        """Complete lesson — mark as done, update progress"""
        from datetime import datetime
        user   = User.query.get(get_jwt_identity())
        lesson = Lesson.query.get_or_404(lesson_id)
        course = lesson.module.course
        enr    = Enrollment.query.filter_by(student_id=user.id, course_id=course.id).first()
        if not enr:
            return {'message': 'Not enrolled in this course'}, 403

        lp = LessonProgress.query.filter_by(enrollment_id=enr.id, lesson_id=lesson_id).first()
        if not lp:
            lp = LessonProgress(enrollment_id=enr.id, lesson_id=lesson_id)
            db.session.add(lp)

        lp.completed    = True
        lp.completed_at = datetime.utcnow()

        # auto-mark course complete if 100%
        enr.completed = enr.progress_percent == 100
        db.session.commit()

        return {
            'message': 'Lesson marked as complete',
            'progress_percent': enr.progress_percent,
            'course_completed': enr.completed,
        }, 200
