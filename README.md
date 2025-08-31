# School Management System

A Flask-based web application for managing student grades and absences with role-based access control.

## Features

### Authentication System
- **Admin Login**: Hardcoded credentials (email: "admin", password: "admin")
- **Student Registration**: Students can create new accounts
- **Student Login**: Registered students can login with their credentials
- **Session Management**: Flask sessions for secure authentication

### Admin Dashboard
- View all students with their grades and absences
- Add/update student grades for different modules
- Update student absence counts
- Automatic status calculation (Admis/Non Admis based on grade ≥ 10)
- **Advanced filtering** by academic year, module, teacher, and risk level
- **Risk detection** with configurable thresholds
- **Teacher and academic year tracking**
- **Export functionality** (CSV/Excel)

### Student Dashboard
- View personal grades and absence count
- See overall academic status
- Calculate average grade and modules passed
- **Class ranking** and position
- **Risk level assessment**
- **Performance tracking**
- Clean, responsive interface

## Database Schema

### Tables
1. **users** (id, name, email, password, role)
2. **grades** (id, student_id, module_name, grade, teacher_name, academic_year)
3. **absences** (id, student_id, count, total_hours)
4. **classes** (id, name, academic_year, teacher_name)
5. **student_class** (id, student_id, class_id)
6. **risk_thresholds** (id, min_grade, max_absences, risk_level)

## Installation & Setup

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Access the application**:
   - Open your browser and go to `http://localhost:5000`
   - The application will automatically create the SQLite database on first run

## Usage

### Admin Access
- Login with email: `admin` and password: `admin`
- Access the admin dashboard to manage all student data
- Add grades for different modules
- Update absence counts

### Student Access
- Register a new account on the registration page
- Login with your email and password
- View your personal academic performance

## Routes

- `/` - Redirects to login page
- `/login` - Login page (GET/POST)
- `/register` - Student registration (GET/POST)
- `/admin_dashboard` - Admin dashboard (GET/POST)
- `/student_dashboard` - Student dashboard (GET)
- `/analytics` - Analytics dashboard (GET)
- `/export_data` - Export data (CSV/Excel)
- `/api/student_risk/<id>` - Student risk API
- `/logout` - Logout and clear session

## Technical Details

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: Pure HTML, CSS, JavaScript (no frameworks)
- **Authentication**: Flask sessions with password hashing
- **Styling**: Custom CSS with responsive design
- **Data Export**: CSV and Excel (pandas, openpyxl)
- **Risk Analysis**: Configurable thresholds and algorithms

## Security Features

- Password hashing using SHA-256
- Session-based authentication
- Role-based access control
- SQL injection prevention with parameterized queries

## File Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html         # Base template with common styling
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   ├── admin_dashboard.html  # Admin dashboard
│   └── student_dashboard.html # Student dashboard
└── school.db             # SQLite database (created automatically)
```

## Advanced Features

### Analytics Dashboard
- **Global performance overview** with key metrics
- **Module performance analysis** with success rates
- **Student risk detection** with recommendations
- **Configurable risk thresholds** (grades and absences)
- **Real-time statistics** and trends

### Risk Management
- **Automatic risk assessment** based on grades and attendance
- **Three risk levels**: Low, Medium, High
- **Personalized recommendations** for each risk level
- **Early warning system** for at-risk students

### Data Export & Reporting
- **CSV export** for data analysis
- **Excel export** with formatted reports
- **Comprehensive student data** including grades, absences, and risk levels
- **Teacher and academic year tracking**

## Notes

- The application uses a simple grading system where grades ≥ 10 are considered "Admis" (Passed)
- All styling is custom CSS without external frameworks
- The database is automatically initialized when the app starts
- Admin credentials are hardcoded for simplicity
- Risk thresholds can be configured in the database 