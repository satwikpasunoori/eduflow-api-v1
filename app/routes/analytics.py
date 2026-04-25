from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Course, Enrollment, User, UserRole, LessonProgress
from app.extensions import db
from sqlalchemy import func

ns = Namespace('analytics', description='Platform analytics and dashboard stats')


@ns.route('/dashboard')
class Dashboard(Resource):

    @jwt_required()
    @ns.doc(security='Bearer', description='Platform-wide analytics — admin only')
    def get(self):
        """Dashboard — full platform analytics"""
        user = User.query.get(get_jwt_identity())
        if user.role != UserRole.ADMIN:
            return {'message': 'Admin access required'}, 403

        total_users       = User.query.count()
        total_courses     = Course.query.count()
        published_courses = Course.query.filter_by(is_published=True).count()
        total_enrollments = Enrollment.query.count()
        completed_courses = Enrollment.query.filter_by(completed=True).count()

        completion_rate = 0
        if total_enrollments > 0:
            completion_rate = round((completed_courses / total_enrollments) * 100, 1)

        # top 5 most enrolled courses
        top_courses = (
            db.session.query(Course, func.count(Enrollment.id).label('cnt'))
            .join(Enrollment, Course.id == Enrollment.course_id)
            .group_by(Course.id)
            .order_by(func.count(Enrollment.id).desc())
            .limit(5)
            .all()
        )

        return {
            'overview': {
                'total_users': total_users,
                'total_courses': total_courses,
                'published_courses': published_courses,
                'total_enrollments': total_enrollments,
                'completed_courses': completed_courses,
                'completion_rate_percent': completion_rate,
            },
            'top_courses': [
                {'id': c.id, 'title': c.title, 'enrollments': cnt}
                for c, cnt in top_courses
            ],
        }, 200


@ns.route('/popular-courses')
class PopularCourses(Resource):

    @ns.doc(description='Top 10 most enrolled courses — public endpoint')
    def get(self):
        """Popular courses — public, no auth needed"""
        results = (
            db.session.query(Course, func.count(Enrollment.id).label('cnt'))
            .join(Enrollment, Course.id == Enrollment.course_id)
            .filter(Course.is_published == True)
            .group_by(Course.id)
            .order_by(func.count(Enrollment.id).desc())
            .limit(10)
            .all()
        )
        return {
            'popular_courses': [
                {**c.to_dict(), 'enrollment_count': cnt}
                for c, cnt in results
            ]
        }, 200


@ns.route('/my-stats')
class MyStats(Resource):

    @jwt_required()
    @ns.doc(security='Bearer', description='Personal stats for the logged-in student')
    def get(self):
        """My stats — personal learning analytics"""
        user = User.query.get(get_jwt_identity())
        enrollments = user.enrollments.all()
        completed   = [e for e in enrollments if e.completed]
        in_progress = [e for e in enrollments if not e.completed]

        return {
            'total_enrolled': len(enrollments),
            'completed': len(completed),
            'in_progress': len(in_progress),
            'courses': [e.to_dict() for e in enrollments],
        }, 200


@ns.route('/instructor-stats')
class InstructorStats(Resource):

    @jwt_required()
    @ns.doc(security='Bearer', description='Stats for the logged-in instructor')
    def get(self):
        """Instructor stats — my courses performance"""
        user    = User.query.get(get_jwt_identity())
        if user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
            return {'message': 'Instructor access required'}, 403

        courses = user.courses.all()
        stats   = []
        for course in courses:
            stats.append({
                'course_id':    course.id,
                'title':        course.title,
                'is_published': course.is_published,
                'enrollments':  course.enrollment_count,
                'total_lessons': course.total_lessons,
                'rating':       course.rating,
            })

        return {
            'total_courses':     len(courses),
            'published_courses': sum(1 for c in courses if c.is_published),
            'total_enrollments': sum(c.enrollment_count for c in courses),
            'courses': stats,
        }, 200
