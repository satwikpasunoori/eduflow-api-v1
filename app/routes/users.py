from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Enrollment, UserRole
from app.extensions import db

ns = Namespace('users', description='User profile and course management')


@ns.route('/my-courses')
class MyCourses(Resource):

    @jwt_required()
    @ns.doc(security='Bearer', description='Get all courses the logged-in student is enrolled in')
    def get(self):
        """My courses — all enrolled courses with progress"""
        user = User.query.get(get_jwt_identity())
        enrollments = user.enrollments.all()
        return {
            'total': len(enrollments),
            'enrollments': [e.to_dict() for e in enrollments]
        }, 200


@ns.route('/all')
class AllUsers(Resource):

    @jwt_required()
    @ns.doc(security='Bearer', description='List all users — admin only')
    def get(self):
        """All users — admin only"""
        caller = User.query.get(get_jwt_identity())
        if caller.role != UserRole.ADMIN:
            return {'message': 'Admin access required'}, 403
        users = User.query.all()
        return {'total': len(users), 'users': [u.to_dict() for u in users]}, 200
