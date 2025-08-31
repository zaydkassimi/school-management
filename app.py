from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, make_response
import sqlite3
import hashlib
from functools import wraps
import pandas as pd
import io
import csv
from datetime import datetime
import json
from fpdf import FPDF  # Using FPDF instead of pdfkit
from collections import defaultdict
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Database initialization
def init_db():
    print("Initializing database...")
    
    # Only create database if it doesn't exist
    database_exists = os.path.exists('school.db')
    
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    print("Created users table")
    
    # Create grades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            module_name TEXT NOT NULL,
            grade REAL NOT NULL,
            teacher_name TEXT,
            academic_year TEXT DEFAULT '2024-2025',
            semester TEXT DEFAULT '1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    ''')
    print("Created grades table")
    
    # Create absences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS absences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            module_name TEXT DEFAULT NULL,
            count INTEGER DEFAULT 0,
            total_hours INTEGER DEFAULT 0,
            academic_year TEXT DEFAULT '2024-2025',
            semester TEXT DEFAULT '1',
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
    ''')
    print("Created absences table")
    
    # Create classes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            academic_year TEXT DEFAULT '2024-2025',
            teacher_name TEXT
        )
    ''')
    print("Created classes table")
    
    # Create student_class table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_class (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (class_id) REFERENCES classes (id)
        )
    ''')
    print("Created student_class table")
    
    # Create risk_thresholds table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS risk_thresholds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            min_grade REAL DEFAULT 10.0,
            max_absences INTEGER DEFAULT 10,
            risk_level TEXT DEFAULT 'medium'
        )
    ''')
    print("Created risk_thresholds table")
    
    # Insert default risk threshold
    cursor.execute('SELECT COUNT(*) FROM risk_thresholds')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO risk_thresholds (min_grade, max_absences, risk_level) VALUES (10.0, 10, "medium")')
        print("Inserted default risk threshold")
    
    print("Database initialization completed successfully")
    conn.commit()
    conn.close()
    
    if not database_exists:
        print("New database created. You can now add students and data.")
    else:
        print("Existing database loaded. Your data is preserved.")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.')
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Get risk level for a student
def get_student_risk_level(student_id):
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()
    
    # Get student's average grade
    cursor.execute('''
        SELECT AVG(grade) FROM grades WHERE student_id = ?
    ''', (student_id,))
    avg_grade = cursor.fetchone()[0] or 0
    
    # Get student's total absences across all modules
    cursor.execute('SELECT SUM(count) FROM absences WHERE student_id = ?', (student_id,))
    total_absences_result = cursor.fetchone()
    total_absences = total_absences_result[0] if total_absences_result and total_absences_result[0] else 0
    
    # Get risk thresholds
    cursor.execute('SELECT min_grade, max_absences FROM risk_thresholds LIMIT 1')
    threshold = cursor.fetchone()
    min_grade, max_absences = threshold if threshold else (10.0, 10)
    
    conn.close()
    
    # Calculate risk level
    if avg_grade < min_grade and total_absences > max_absences:
        return 'high'
    elif avg_grade < min_grade or total_absences > max_absences:
        return 'medium'
    else:
        return 'low'

# Get student ranking
def get_student_ranking(student_id):
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()
    
    # Get all students with their average grades
    cursor.execute('''
        SELECT u.id, u.name, AVG(g.grade) as avg_grade
        FROM users u
        LEFT JOIN grades g ON u.id = g.student_id
        WHERE u.role = 'student'
        GROUP BY u.id, u.name
        ORDER BY avg_grade DESC
    ''')
    
    students = cursor.fetchall()
    conn.close()
    
    # Find student's position
    for i, (sid, name, avg_grade) in enumerate(students, 1):
        if sid == student_id:
            return i, len(students), avg_grade or 0
    
    return None, len(students), 0

# Get student performance evolution over semesters
def get_student_evolution(student_id):
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()
    
    # Get student's grades across semesters
    cursor.execute('''
        SELECT academic_year, semester, AVG(grade) as avg_grade,
               COUNT(CASE WHEN grade >= 10 THEN 1 END) as passed,
               COUNT(*) as total
        FROM grades
        WHERE student_id = ?
        GROUP BY academic_year, semester
        ORDER BY academic_year, semester
    ''', (student_id,))
    
    evolution_data = cursor.fetchall()
    conn.close()
    
    # Process data for visualization
    result = []
    for year, semester, avg_grade, passed, total in evolution_data:
        success_rate = (passed / total * 100) if total > 0 else 0
        result.append({
            'period': f"{year} S{semester}",
            'avg_grade': round(avg_grade, 2) if avg_grade else 0,
            'success_rate': round(success_rate, 1)
        })
    
    return result

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check for admin login
        if email == 'admin' and password == 'admin':
            session['user_id'] = 'admin'
            session['role'] = 'admin'
            session['name'] = 'Administrator'
            return redirect(url_for('admin_dashboard'))
        
        # Check for student login
        conn = sqlite3.connect('school.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, password, role FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and user[2] == hash_password(password):
            session['user_id'] = user[0]
            session['role'] = user[3]
            session['name'] = user[1]
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('school.db')
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            flash('Email already registered')
            conn.close()
            return render_template('register.html')
        
        # Insert new user
        hashed_password = hash_password(password)
        cursor.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)', 
                      (name, email, hashed_password, 'student'))
        
        # Create default absence record for new student
        student_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    if request.method == 'POST':
        student_id = request.form['student_id']
        module_name = request.form['module_name']
        grade = request.form['grade']
        absences = request.form['absences']
        teacher_name = request.form.get('teacher_name', '')
        academic_year = request.form.get('academic_year', '2024-2025')
        semester = request.form.get('semester', '1')
        
        conn = sqlite3.connect('school.db')
        cursor = conn.cursor()
        
        # Update or insert grade
        cursor.execute('SELECT id FROM grades WHERE student_id = ? AND module_name = ? AND academic_year = ? AND semester = ?', 
                      (student_id, module_name, academic_year, semester))
        existing_grade = cursor.fetchone()
        
        if existing_grade:
            cursor.execute('''
                UPDATE grades 
                SET grade = ?, teacher_name = ? 
                WHERE student_id = ? AND module_name = ? AND academic_year = ? AND semester = ?
            ''', (grade, teacher_name, student_id, module_name, academic_year, semester))
        else:
            cursor.execute('''
                INSERT INTO grades 
                (student_id, module_name, grade, teacher_name, academic_year, semester) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_id, module_name, grade, teacher_name, academic_year, semester))
        
        # Update or insert module-specific absences
        cursor.execute('''
            SELECT id FROM absences 
            WHERE student_id = ? AND module_name = ? AND academic_year = ? AND semester = ?
        ''', (student_id, module_name, academic_year, semester))
        
        existing_absence = cursor.fetchone()
        
        if existing_absence:
            cursor.execute('''
                UPDATE absences 
                SET count = ? 
                WHERE student_id = ? AND module_name = ? AND academic_year = ? AND semester = ?
            ''', (absences, student_id, module_name, academic_year, semester))
        else:
            cursor.execute('''
                INSERT INTO absences 
                (student_id, module_name, count, academic_year, semester) 
                VALUES (?, ?, ?, ?, ?)
            ''', (student_id, module_name, absences, academic_year, semester))
        
        conn.commit()
        conn.close()
        
        flash('Student data updated successfully!')
        return redirect(url_for('admin_dashboard'))
    
    # Get filter parameters
    academic_year = request.args.get('academic_year', '2024-2025')
    module_filter = request.args.get('module', '')
    teacher_filter = request.args.get('teacher', '')
    risk_filter = request.args.get('risk', '')
    semester_filter = request.args.get('semester', '')
    
    # Get all students with their grades and absences
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()
    
    # Build query with filters
    query = '''
        SELECT u.id, u.name, u.email, 
               g.module_name,
               g.grade,
               COALESCE(a.count, 0) as absences,
               g.teacher_name,
               g.academic_year,
               g.semester
        FROM users u
        LEFT JOIN grades g ON u.id = g.student_id
        LEFT JOIN absences a ON (u.id = a.student_id AND g.module_name = a.module_name 
                                AND g.academic_year = a.academic_year AND g.semester = a.semester)
        WHERE u.role = 'student'
    '''
    
    params = []
    if academic_year:
        query += ' AND (g.academic_year = ? OR g.academic_year IS NULL)'
        params.append(academic_year)
    if module_filter:
        query += ' AND g.module_name LIKE ?'
        params.append(f'%{module_filter}%')
    if teacher_filter:
        query += ' AND g.teacher_name LIKE ?'
        params.append(f'%{teacher_filter}%')
    if semester_filter:
        query += ' AND g.semester = ?'
        params.append(semester_filter)
    
    query += ' ORDER BY u.name'
    
    try:
        cursor.execute(query, params)
        students_data = cursor.fetchall()
        
        # Get unique values for filters
        cursor.execute('SELECT DISTINCT academic_year FROM grades WHERE academic_year IS NOT NULL')
        academic_years = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT DISTINCT module_name FROM grades WHERE module_name IS NOT NULL')
        modules = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT DISTINCT teacher_name FROM grades WHERE teacher_name IS NOT NULL')
        teachers = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT DISTINCT semester FROM grades WHERE semester IS NOT NULL')
        semesters = [row[0] for row in cursor.fetchall()]
        
        # Process data to group by student
        students = {}
        for row in students_data:
            if len(row) < 9:  # Skip incomplete rows
                continue
                
            student_id, name, email, module_name, grade, absences, teacher_name, year, semester = row
            
            if student_id not in students:
                students[student_id] = {
                    'id': student_id,
                    'name': name,
                    'email': email,
                    'absences': absences,
                    'modules': [],
                    'risk_level': get_student_risk_level(student_id),
                    'avg_grade': 0,
                    'total_modules': 0
                }
            
            if module_name:  # Only add if module name exists
                students[student_id]['modules'].append({
                    'name': module_name,
                    'grade': grade,
                    'status': 'Admis' if grade >= 10 else 'Non Admis',
                    'teacher': teacher_name,
                    'year': year,
                    'semester': semester,
                    'absences': absences
                })
                students[student_id]['total_modules'] += 1
                students[student_id]['avg_grade'] += grade
        
        # Calculate average grades
        for student in students.values():
            if student['total_modules'] > 0:
                student['avg_grade'] = student['avg_grade'] / student['total_modules']
        
        # Apply risk filter
        if risk_filter:
            students = {k: v for k, v in students.items() if v['risk_level'] == risk_filter}
    except Exception as e:
        flash(f'Error: {str(e)}')
        students = {}
        academic_years = []
        modules = []
        teachers = []
        semesters = []
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         students=students.values(),
                         academic_years=academic_years,
                         modules=modules,
                         teachers=teachers,
                         semesters=semesters,
                         current_filters={
                             'academic_year': academic_year,
                             'module': module_filter,
                             'teacher': teacher_filter,
                             'risk': risk_filter,
                             'semester': semester_filter
                         })

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()
    
    # Get student's grades with absences for each module
    cursor.execute('''
        SELECT g.module_name, g.grade, g.teacher_name, g.academic_year, g.semester,
               COALESCE(a.count, 0) as absences
        FROM grades g
        LEFT JOIN absences a ON (g.student_id = a.student_id AND g.module_name = a.module_name 
                                AND g.academic_year = a.academic_year AND g.semester = a.semester)
        WHERE g.student_id = ? 
        ORDER BY g.academic_year, g.semester, g.module_name
    ''', (session['user_id'],))
    grades = cursor.fetchall()
    
    conn.close()
    
    # Process grades with status
    processed_grades = []
    total_absences = 0
    
    for module_name, grade, teacher_name, academic_year, semester, module_absences in grades:
        processed_grades.append({
            'module': module_name,
            'grade': grade,
            'status': 'Admis' if grade >= 10 else 'Non Admis',
            'teacher': teacher_name,
            'year': academic_year,
            'semester': semester,
            'absences': module_absences
        })
        total_absences += module_absences
    
    # Get risk level and ranking
    risk_level = get_student_risk_level(session['user_id'])
    ranking, total_students, avg_grade = get_student_ranking(session['user_id'])
    
    # Get performance evolution
    evolution_data = get_student_evolution(session['user_id'])
    
    return render_template('student_dashboard.html', 
                         grades=processed_grades, 
                         total_absences=total_absences,
                         name=session['name'],
                         risk_level=risk_level,
                         ranking=ranking,
                         total_students=total_students,
                         avg_grade=avg_grade,
                         evolution_data=evolution_data)

@app.route('/analytics')
@admin_required
def analytics():
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()
    
    # Get overall statistics
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "student"')
    total_students = cursor.fetchone()[0]
    
    cursor.execute('SELECT AVG(grade) FROM grades')
    overall_avg = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM grades WHERE grade < 10')
    failed_modules = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM grades')
    total_modules = cursor.fetchone()[0]
    
    # Get students at risk (with only unique student names and total absences across all modules)
    cursor.execute('''
        SELECT u.name, AVG(g.grade) as avg_grade,
        (SELECT SUM(count) FROM absences WHERE student_id = u.id) as absences
        FROM users u
        LEFT JOIN grades g ON u.id = g.student_id
        WHERE u.role = 'student'
        GROUP BY u.id, u.name
        HAVING avg_grade < 10 OR absences > 10
    ''')
    at_risk_students = cursor.fetchall()
    
    # Get module performance
    cursor.execute('''
        SELECT module_name, AVG(grade) as avg_grade, COUNT(*) as student_count
        FROM grades
        GROUP BY module_name
        ORDER BY avg_grade DESC
    ''')
    module_performance = cursor.fetchall()
    
    # Get performance evolution by semester
    cursor.execute('''
        SELECT academic_year, semester, 
               AVG(grade) as avg_grade,
               COUNT(CASE WHEN grade >= 10 THEN 1 END) as passed,
               COUNT(*) as total
        FROM grades
        GROUP BY academic_year, semester
        ORDER BY academic_year, semester
    ''')
    
    performance_evolution = []
    for year, semester, avg_grade, passed, total in cursor.fetchall():
        success_rate = (passed / total * 100) if total > 0 else 0
        performance_evolution.append({
            'period': f"{year} S{semester}",
            'avg_grade': round(avg_grade, 2) if avg_grade else 0,
            'success_rate': round(success_rate, 1)
        })
    
    conn.close()
    
    return render_template('analytics.html',
                         total_students=total_students,
                         overall_avg=overall_avg,
                         failed_modules=failed_modules,
                         total_modules=total_modules,
                         at_risk_students=at_risk_students,
                         module_performance=module_performance,
                         performance_evolution=performance_evolution)

@app.route('/export_data')
@admin_required
def export_data():
    format_type = request.args.get('format', 'csv')
    
    conn = sqlite3.connect('school.db')
    
    if format_type == 'excel':
        # Create Excel file with simplified pandas approach
        query = '''
            SELECT u.name, u.email, g.module_name, g.grade, g.teacher_name, 
                   g.academic_year, g.semester, 
                   COALESCE(a.count, 0) as absences
            FROM users u
            LEFT JOIN grades g ON u.id = g.student_id
            LEFT JOIN absences a ON (u.id = a.student_id AND g.module_name = a.module_name 
                                    AND g.academic_year = a.academic_year AND g.semester = a.semester)
            WHERE u.role = 'student'
            ORDER BY u.name, g.academic_year, g.semester, g.module_name
        '''
        
        try:
            # Use pandas to create DataFrame
            df = pd.read_sql_query(query, conn)
            
            # Add calculated Status column
            df['status'] = df['grade'].apply(lambda x: 'Admis' if x >= 10 else 'Non Admis' if not pd.isna(x) else 'N/A')
            
            # Rename columns for better readability
            df.columns = ['Student Name', 'Email', 'Module', 'Grade', 'Teacher', 
                         'Academic Year', 'Semester', 'Absences', 'Status']
            
            # Calculate summary data for another sheet
            total_students = df['Student Name'].nunique()
            avg_grade = df['Grade'].mean() if not df['Grade'].empty else 0
            passed = len(df[df['Status'] == 'Admis'])
            failed = len(df[df['Status'] == 'Non Admis'])
            success_rate = (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0
            
            summary_data = {
                'Metric': ['Total Students', 'Overall Average', 'Success Rate', 'Failed Modules'],
                'Value': [
                    total_students,
                    f"{avg_grade:.2f}/20",
                    f"{success_rate:.1f}%",
                    failed
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            
            # Save directly to Excel file first (as a temporary file)
            temp_excel_file = f'temp_student_data_{datetime.now().strftime("%Y%m%d")}.xlsx'
            
            # Use the simplest Excel writing approach
            with pd.ExcelWriter(temp_excel_file) as writer:
                df.to_excel(writer, sheet_name='Student Data', index=False)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Read the file back into memory
            with open(temp_excel_file, 'rb') as f:
                output = io.BytesIO(f.read())
            
            # Clean up the temporary file
            os.remove(temp_excel_file)
            
            # Prepare file for download
            output.seek(0)
            conn.close()
            
            # Send as Excel file
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'student_data_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
            
        except Exception as e:
            conn.close()
            return f"Error generating export file: {str(e)}", 500
    
    elif format_type == 'pdf':
        try:
            # Create PDF report using FPDF (no external dependencies)
            cursor = conn.cursor()
            
            # Get student data with proper join between grades and absences
            cursor.execute('''
                SELECT u.name, u.email, g.module_name, g.grade, g.teacher_name, 
                       g.academic_year, g.semester, 
                       COALESCE(a.count, 0) as absences
                FROM users u
                LEFT JOIN grades g ON u.id = g.student_id
                LEFT JOIN absences a ON (u.id = a.student_id AND g.module_name = a.module_name 
                                        AND g.academic_year = a.academic_year AND g.semester = a.semester)
                WHERE u.role = 'student'
                ORDER BY u.name, g.academic_year, g.semester, g.module_name
            ''')
            student_data = cursor.fetchall()
            
            # Get overall statistics
            cursor.execute('SELECT COUNT(*) FROM users WHERE role = "student"')
            total_students = cursor.fetchone()[0]
            
            cursor.execute('SELECT AVG(grade) FROM grades')
            overall_avg = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT COUNT(*) FROM grades WHERE grade < 10')
            failed_modules = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM grades')
            total_modules = cursor.fetchone()[0]
            
            success_rate = ((total_modules - failed_modules) / total_modules * 100) if total_modules > 0 else 0
            
            # Get at-risk students for the report
            cursor.execute('''
                SELECT u.name, AVG(g.grade) as avg_grade,
                (SELECT SUM(count) FROM absences WHERE student_id = u.id) as absences
                FROM users u
                LEFT JOIN grades g ON u.id = g.student_id
                WHERE u.role = 'student'
                GROUP BY u.id, u.name
                HAVING avg_grade < 10 OR absences > 10
            ''')
            at_risk_students = cursor.fetchall()
            
            # Get module performance
            cursor.execute('''
                SELECT module_name, AVG(grade) as avg_grade, COUNT(*) as student_count
                FROM grades
                GROUP BY module_name
                ORDER BY avg_grade DESC
            ''')
            module_performance = cursor.fetchall()
            
            conn.close()
            
            # Create PDF using FPDF
            class PDF(FPDF):
                def header(self):
                    # Logo - if you have one
                    # self.image('logo.png', 10, 8, 33)
                    self.set_font('Arial', 'B', 15)
                    self.cell(0, 10, 'School Management System - Performance Report', 0, 1, 'C')
                    self.set_font('Arial', 'I', 10)
                    self.cell(0, 10, f'Generated on {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'C')
                    self.ln(5)
                
                def footer(self):
                    self.set_y(-15)
                    self.set_font('Arial', 'I', 8)
                    self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
                
                def section_title(self, title):
                    self.set_font('Arial', 'B', 12)
                    self.set_fill_color(100, 149, 237)  # Cornflower blue
                    self.cell(0, 10, title, 0, 1, 'L', True)
                    self.ln(5)
                
                def table_header(self, headers):
                    self.set_font('Arial', 'B', 10)
                    self.set_fill_color(200, 220, 255)
                    
                    # Calculate column widths based on content
                    col_widths = []
                    total_width = self.w - 20  # Page width minus margins
                    
                    # Simple algorithm - divide equally for now
                    col_width = total_width / len(headers)
                    
                    for header in headers:
                        self.cell(col_width, 7, header, 1, 0, 'C', True)
                    self.ln()
                
                def table_row(self, data, col_widths=None):
                    self.set_font('Arial', '', 9)
                    
                    if not col_widths:
                        # Use equal width for columns
                        col_width = (self.w - 20) / len(data)
                        col_widths = [col_width] * len(data)
                    
                    for i, item in enumerate(data):
                        # Convert any non-string data
                        if item is None:
                            item = 'N/A'
                        elif not isinstance(item, str):
                            item = str(item)
                        
                        # Make sure cell doesn't overflow to next page
                        if self.get_y() + 7 > self.page_break_trigger:
                            self.add_page()
                        
                        self.cell(col_widths[i], 7, item, 1, 0, 'L')
                    self.ln()
            
            # Initialize PDF
            pdf = PDF()
            pdf.set_auto_page_break(True, margin=15)
            pdf.add_page()
            
            # Summary section
            pdf.section_title('Performance Summary')
            pdf.set_font('Arial', '', 10)
            pdf.cell(40, 10, f'Total Students: {total_students}', 0, 0)
            pdf.cell(60, 10, f'Overall Average: {overall_avg:.2f}/20', 0, 0)
            pdf.cell(50, 10, f'Success Rate: {success_rate:.1f}%', 0, 0)
            pdf.cell(40, 10, f'Failed Modules: {failed_modules}/{total_modules}', 0, 1)
            pdf.ln(5)
            
            # Students at Risk section
            if at_risk_students:
                pdf.add_page()
                pdf.section_title('Students at Risk')
                
                # Table header
                headers = ['Student Name', 'Average Grade', 'Absences', 'Risk Level', 'Recommendations']
                pdf.table_header(headers)
                
                # Table data
                for name, avg_grade, absences in at_risk_students:
                    risk_level = 'High' if (avg_grade or 0) < 10 and absences > 10 else 'Medium'
                    recommendation = "Weekly tutoring + checks" if risk_level == "High" else "Study groups + practice"
                    pdf.table_row([name, f"{avg_grade:.2f}/20", str(absences), risk_level, recommendation])
                pdf.ln(10)
            
            # Module Performance section
            if module_performance:
                pdf.add_page()
                pdf.section_title('Module Performance')
                
                # Table header
                headers = ['Module', 'Average Grade', 'Students', 'Success Rate']
                pdf.table_header(headers)
                
                # Table data
                for module_name, avg_grade, student_count in module_performance:
                    module_success = (avg_grade / 20 * 100) if avg_grade else 0
                    pdf.table_row([
                        module_name, 
                        f"{avg_grade:.2f}/20", 
                        str(student_count), 
                        f"{module_success:.1f}%"
                    ])
                pdf.ln(10)
            
            # Student Performance Data section
            pdf.add_page()
            pdf.section_title('Student Performance Data')
            
            # Limit columns to fit on page - show most important ones
            headers = ['Name', 'Email', 'Module', 'Grade', 'Teacher', 'Absences']
            pdf.table_header(headers)
            
            # Table data (limited to key columns)
            for student in student_data:
                pdf.table_row([
                    student[0],    # name
                    student[1],    # email
                    student[2] or 'N/A',   # module
                    f"{student[3]:.2f}" if student[3] else 'N/A',  # grade
                    student[4] or 'N/A',   # teacher
                    str(student[7] or '0')  # absences
                ])
            
            # Get PDF as bytes
            pdf_bytes = pdf.output(dest='S').encode('latin1')
            
            # Return PDF file
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'student_report_{datetime.now().strftime("%Y%m%d")}.pdf'
            )
            
        except Exception as e:
            return f"Error generating report: {str(e)}", 500
    
    else:  # CSV
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.name, u.email, g.module_name, g.grade, g.teacher_name, 
                   g.academic_year, g.semester, 
                   COALESCE(a.count, 0) as absences
            FROM users u
            LEFT JOIN grades g ON u.id = g.student_id
            LEFT JOIN absences a ON (u.id = a.student_id AND g.module_name = a.module_name 
                                    AND g.academic_year = a.academic_year AND g.semester = a.semester)
            WHERE u.role = 'student'
            ORDER BY u.name, g.academic_year, g.semester, g.module_name
        ''')
        
        data = cursor.fetchall()
        conn.close()
        
        # Create CSV in memory with improved formatting
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Name', 'Email', 'Module', 'Grade', 'Teacher', 'Academic Year', 'Semester', 'Absences', 'Status'])
        
        # Add status column and format grades
        formatted_data = []
        for row in data:
            # Calculate status
            grade = row[3]
            status = 'Admis' if grade and grade >= 10 else 'Non Admis' if grade is not None else 'N/A'
            
            # Format grade to 2 decimal places if not None
            formatted_grade = f"{grade:.2f}" if grade is not None else 'N/A'
            
            # Create new row with formatted data
            new_row = [
                row[0],                    # Name
                row[1],                    # Email
                row[2] or 'N/A',           # Module
                formatted_grade,           # Grade
                row[4] or 'N/A',           # Teacher
                row[5] or 'N/A',           # Academic Year
                row[6] or 'N/A',           # Semester
                str(row[7]),               # Absences
                status                     # Status
            ]
            formatted_data.append(new_row)
        
        # Write the formatted data
        writer.writerows(formatted_data)
        
        # Add summary data
        writer.writerow([])
        writer.writerow(['SUMMARY'])
        
        # Calculate summary metrics
        students = set([row[0] for row in data])
        total_students = len(students)
        grades = [row[3] for row in data if row[3] is not None]
        avg_grade = sum(grades) / len(grades) if grades else 0
        passed = len([g for g in grades if g >= 10])
        failed = len(grades) - passed
        success_rate = (passed / len(grades) * 100) if grades else 0
        
        # Write summary rows
        writer.writerow(['Total Students', total_students])
        writer.writerow(['Overall Average', f"{avg_grade:.2f}/20"])
        writer.writerow(['Success Rate', f"{success_rate:.1f}%"])
        writer.writerow(['Failed Modules', failed])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'student_data_{datetime.now().strftime("%Y%m%d")}.csv'
        )

@app.route('/api/student_risk/<int:student_id>')
@admin_required
def api_student_risk(student_id):
    risk_level = get_student_risk_level(student_id)
    ranking, total_students, avg_grade = get_student_ranking(student_id)
    evolution_data = get_student_evolution(student_id)
    
    return jsonify({
        'risk_level': risk_level,
        'ranking': ranking,
        'total_students': total_students,
        'avg_grade': avg_grade,
        'evolution_data': evolution_data
    })

@app.route('/api/performance_evolution')
@admin_required
def api_performance_evolution():
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()
    
    # Get performance evolution by semester
    cursor.execute('''
        SELECT academic_year, semester, 
               AVG(grade) as avg_grade,
               COUNT(CASE WHEN grade >= 10 THEN 1 END) as passed,
               COUNT(*) as total
        FROM grades
        GROUP BY academic_year, semester
        ORDER BY academic_year, semester
    ''')
    
    performance_data = cursor.fetchall()
    conn.close()
    
    result = []
    for year, semester, avg_grade, passed, total in performance_data:
        success_rate = (passed / total * 100) if total > 0 else 0
        result.append({
            'period': f"{year} S{semester}",
            'avg_grade': round(avg_grade, 2) if avg_grade else 0,
            'success_rate': round(success_rate, 1)
        })
    
    return jsonify(result)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)