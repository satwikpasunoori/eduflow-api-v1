from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from app.extensions import db, bcrypt
from app.models import User, UserRole

ns = Namespace('auth', description='Authentication — register, login, profile')

# ── Swagger models ────────────────────────────────────────────
register_model = ns.model('Register', {
    'name':     fields.String(required=True, example='Satwik Pasunoori'),
    'email':    fields.String(required=True, example='satwik@example.com'),
    'password': fields.String(required=True, example='password123'),
    'role':     fields.String(example='student', enum=['student','instructor','admin']),
})

login_model = ns.model('Login', {
    'email':    fields.String(required=True, example='satwik@example.com'),
    'password': fields.String(required=True, example='password123'),
})


@ns.route('/register')
class Register(Resource):
    @ns.expect(register_model, validate=True)
    @ns.doc(description='Register a new user account')
    def post(self):
        """Register — create a new account"""
        data = request.json
        if User.query.filter_by(email=data['email']).first():
            return {'message': 'Email already registered'}, 409
        role_str = data.get('role', 'student').lower()
        try:
            role = UserRole(role_str)
        except ValueError:
            role = UserRole.STUDENT
        user = User(
            name=data['name'].strip(),
            email=data['email'].lower().strip(),
            password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
            role=role,
        )
        db.session.add(user)
        db.session.commit()
        access  = create_access_token(identity=user.id)
        refresh = create_refresh_token(identity=user.id)
        return {'message': 'Account created successfully', 'user': user.to_dict(),
                'access_token': access, 'refresh_token': refresh}, 201


@ns.route('/login')
class Login(Resource):
    @ns.expect(login_model, validate=True)
    @ns.doc(description='Login and receive JWT tokens')
    def post(self):
        """Login — returns access + refresh tokens"""
        data = request.json
        user = User.query.filter_by(email=data['email'].lower().strip()).first()
        if not user or not bcrypt.check_password_hash(user.password, data['password']):
            return {'message': 'Invalid email or password'}, 401
        if not user.is_active:
            return {'message': 'Account is deactivated'}, 403
        access  = create_access_token(identity=user.id)
        refresh = create_refresh_token(identity=user.id)
        return {'message': 'Login successful', 'user': user.to_dict(),
                'access_token': access, 'refresh_token': refresh}, 200


@ns.route('/refresh')
class Refresh(Resource):
    @jwt_required(refresh=True)
    @ns.doc(security='Bearer', description='Get a new access token using refresh token')
    def post(self):
        """Refresh — get new access token"""
        user_id = get_jwt_identity()
        access  = create_access_token(identity=user_id)
        return {'access_token': access}, 200


@ns.route('/me')
class Me(Resource):
    @jwt_required()
    @ns.doc(security='Bearer', description='Get current logged-in user profile')
    def get(self):
        """Me — get my profile"""
        user = User.query.get_or_404(get_jwt_identity())
        return user.to_dict(), 200

    @jwt_required()
    @ns.doc(security='Bearer', description='Update your profile name')
    def put(self):
        """Me — update my profile"""
        user = User.query.get_or_404(get_jwt_identity())
        data = request.json or {}
        if 'name' in data:
            user.name = data['name'].strip()
        db.session.commit()
        return user.to_dict(), 200
