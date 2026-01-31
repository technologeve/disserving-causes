from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import supabase
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_key_for_dev")

# --- Helpers ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_role():
    if 'user' not in session:
        return None
    # In a real app we might store role in session to avoid DB hit every time,
    # or fetch it fresh. For now, let's assume it's in session metadata if we put it there during login.
    return session.get('role')

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # Authenticate with Supabase
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            session['user'] = response.user.id
            session['access_token'] = response.session.access_token
            
            # Fetch user profile to get role
            profile_response = supabase.table('profiles').select('*').eq('id', response.user.id).execute()
            
            if profile_response.data:
                session['role'] = profile_response.data[0]['role']
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Profile not found. Please contact support.', 'error')
                
        except Exception as e:
            flash(str(e), 'error')
            
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        try:
            supabase.auth.reset_password_email(email)
            flash('Password reset link has been sent to your email.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Error: {str(e)}", 'error')
            
    return render_template('forgot_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role')
        organization = request.form.get('organization') # For charities/profs
        subject = request.form.get('subject') # For students
        
        try:
            # 1. Sign up user with metadata
            # This triggers the 'handle_new_user' function in the database to create the profile
            auth_response = supabase.auth.sign_up({
                "email": email, 
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "role": role,
                        "organization": organization,
                        "subject": subject
                    }
                }
            })
            
            # Check if sign up was successful (user might be None if rate limited or error)
            if auth_response.user:
                flash('Registration successful! Please check your email to verify your account (if enabled) or log in.', 'success')
                return redirect(url_for('login'))
            else:
                 flash("Registration failed. Please try again.", 'error')
                
        except Exception as e:
            flash(f"Registration failed: {str(e)}", 'error')
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    supabase.auth.sign_out()
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    user_id = session.get('user')
    
    # Fetch data relevant to the role
    context = {"role": role}
    
    if role == 'charity':
        # Get my projects
        projects = supabase.table('projects').select('*').eq('charity_id', user_id).execute()
        context['projects'] = projects.data
    elif role in ['student', 'professor']:
        # Get projects I've expressed interest in? Or simply show available projects.
        # For dashboard, maybe show "My Applications/Interests"
        interests = supabase.table('interests').select('*, projects(*)').eq('user_id', user_id).execute()
        context['my_interests'] = interests.data
        
    return render_template('dashboard.html', **context)

@app.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    if session.get('role') != 'charity':
        flash('Only charities can create projects.', 'error')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        requirements = request.form.get('requirements')
        subject = request.form.get('subject')
        
        try:
            data = {
                "title": title,
                "description": description,
                "requirements": requirements,
                "subject": subject,
                "charity_id": session.get('user')
            }
            supabase.table('projects').insert(data).execute()
            flash('Project created successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f"Error creating project: {str(e)}", 'error')
            
    return render_template('create_project.html')

@app.route('/projects')
@login_required
def projects():
    subject_filter = request.args.get('subject')
    sponsored_filter = request.args.get('sponsored')
    
    # Base query
    query = supabase.table('projects').select('*, profiles(organization)').eq('status', 'open')
    
    if subject_filter:
        query = query.ilike('subject', f'%{subject_filter}%')
        
    try:
        response = query.execute()
        all_projects = response.data
        
        # Post-process for "Sponsored by my Uni" filter if enabled used
        # This is complex to do in one Supabase query without dedicated RPC functions or complex joins,
        # so we'll do loose filtering here in Python for this prototype.
        if sponsored_filter and session.get('role') == 'student':
            user_id = session.get('user')
            # 1. Get student's organization (University)
            user_profile = supabase.table('profiles').select('organization').eq('id', user_id).execute()
            if user_profile.data:
                my_uni = user_profile.data[0]['organization']
                
                filtered_projects = []
                for p in all_projects:
                    # Check if any professor from my_uni has expressed interest in this project
                    # Fetch interests for this project
                    interests = supabase.table('interests').select('user_id, profiles(role, organization)').eq('project_id', p['id']).execute()
                    
                    is_sponsored_by_my_uni = False
                    for i in interests.data:
                        profile = i['profiles']
                        if profile and profile.get('role') == 'professor' and profile.get('organization') == my_uni:
                            is_sponsored_by_my_uni = True
                            break
                    
                    if is_sponsored_by_my_uni:
                        filtered_projects.append(p)
                
                all_projects = filtered_projects

    except Exception as e:
        flash(f"Error fetching projects: {str(e)}", 'error')
        all_projects = []
        
    return render_template('projects.html', projects=all_projects)

@app.route('/project/<project_id>/sponser', methods=['POST'])
@login_required
def express_interest(project_id):
    # Determine if user is student or professor
    role = session.get('role')
    if role not in ['student', 'professor']:
        flash("Only students and professors can express interest.", 'error')
        return redirect(url_for('projects'))
        
    message = request.form.get('message', '')
    
    try:
        data = {
            "project_id": project_id,
            "user_id": session.get('user'),
            "message": message
        }
        supabase.table('interests').insert(data).execute()
        flash('Interest expressed successfully!', 'success')
    except Exception as e:
        # Check for duplicate key error which means already applied
        if 'duplicate key' in str(e) or '23505' in str(e): # Postgres code for unique violation
             flash('You have already expressed interest in this project.', 'warning')
        else:
            flash(f"Error: {str(e)}", 'error')
            
    return redirect(url_for('projects'))


if __name__ == '__main__':
    app.run(debug=True, port=8080)
