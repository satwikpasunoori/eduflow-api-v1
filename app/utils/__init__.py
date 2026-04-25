import os, requests, json
from functools import wraps
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask import jsonify
from app.models import User, UserRole

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = User.query.get(get_jwt_identity())
            if not user or user.role not in roles:
                return jsonify({'message':'Access denied — insufficient permissions'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def generate_ai_summary(course_title, category, level):
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        return {
            'description': f"This {level} level {category.replace('_',' ')} course '{course_title}' covers essential concepts and practical skills through structured lessons and real-world projects.",
            'learning_outcomes': [
                f"Understand core concepts of {category.replace('_',' ')}",
                f"Apply {level}-level techniques in real projects",
                "Write clean, well-structured code",
                "Debug and troubleshoot common issues",
                "Build a portfolio-worthy project by course end",
            ],
            'ai_powered': False,
            'note': 'Add GEMINI_API_KEY to .env for AI-powered summaries',
        }
    prompt = f"""You are an expert e-learning content creator. Generate a course summary for:
Title: {course_title}, Category: {category.replace('_',' ')}, Level: {level}
Respond in this exact JSON format only:
{{"description":"2-3 sentence engaging course description","learning_outcomes":["outcome 1","outcome 2","outcome 3","outcome 4","outcome 5"]}}"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        r = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=15)
        if r.status_code == 200:
            text = r.json()['candidates'][0]['content']['parts'][0]['text']
            text = text.strip().lstrip('```json').rstrip('```').strip()
            result = json.loads(text)
            result['ai_powered'] = True
            return result
        raise Exception(f"Gemini returned {r.status_code}")
    except Exception as e:
        return {
            'description': f"'{course_title}' is a comprehensive {level} course in {category.replace('_',' ')} designed to take you from foundational understanding to practical mastery.",
            'learning_outcomes': [f"Master {level}-level {category.replace('_',' ')} concepts","Build real-world projects","Follow industry best practices","Solve complex problems independently","Be job-ready in this domain"],
            'ai_powered': False,
            'note': f'Gemini unavailable — using template summary',
        }

def paginate_query(query, page, per_page=10):
    p = query.paginate(page=page, per_page=per_page, error_out=False)
    return {'page':page,'per_page':per_page,'total':p.total,'pages':p.pages,'has_next':p.has_next,'has_prev':p.has_prev}, p.items
