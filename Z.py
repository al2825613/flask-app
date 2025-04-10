from flask import Flask, request, redirect, url_for, session, flash, get_flashed_messages, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import sys
import io
import subprocess
from datetime import datetime, timedelta
import json
from werkzeug.security import generate_password_hash, check_password_hash
import requests, re, uuid, random, time

app = Flask(__name__)
app.secret_key = 'سر_مخصوص_للأمان'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CACHE_TYPE'] = 'simple'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True

db = SQLAlchemy(app)
cache = Cache(app)
limiter = Limiter(get_remote_address, app=app)

# تعريف نماذج قاعدة البيانات
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class CodeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.String(80), nullable=False)
    code = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text, nullable=False)

class InstalledLibrary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    library_name = db.Column(db.String(120), nullable=False)

class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    sample_code = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()
    if not Challenge.query.first():
        chal1 = Challenge(
            title="تحدي الطباعة",
            description="اكتب كودًا يطبع 'Hello, World!'",
            sample_code="print('Hello, World!')",
            solution="print('Hello, World!')"
        )
        db.session.add(chal1)
        db.session.commit()

# الدروس التعليمية
lessons = {
    '1': {
        'title': 'مقدمة إلى الطباعة في بايثون',
        'description': 'تعرف على كيفية استخدام الدالة print لطباعة النصوص والأرقام.',
        'code': "print('مرحبا بكم في درس بايثون')",
        'explanation': 'الدالة print تعرض النصوص والأرقام على الشاشة.'
    },
    '2': {
        'title': 'المتغيرات في بايثون',
        'description': 'تعرف على كيفية تعريف المتغيرات وتخزين البيانات فيها.',
        'code': "message = 'أهلا وسهلا'\nprint(message)",
        'explanation': 'المتغير هو مساحة لتخزين البيانات.'
    },
    '3': {
        'title': 'الحلقات التكرارية (for loop)',
        'description': 'تعلم كيفية استخدام الحلقات لتكرار تنفيذ الأوامر.',
        'code': "for i in range(5):\n    print('الرقم:', i)",
        'explanation': 'حلقة for تكرر الكود داخلها لعدد مرات محدد.'
    },
    '4': {
        'title': 'الشروط (if statement)',
        'description': 'استخدام الشروط لاتخاذ قرارات في الكود.',
        'code': "x = 10\nif x > 5:\n    print('x أكبر من 5')\nelse:\n    print('x أقل أو يساوي 5')",
        'explanation': 'تستخدم if لتحديد ما إذا كانت العبارة صحيحة وتنفيذ الكود المناسب.'
    },
    '5': {
        'title': 'الدوال في بايثون',
        'description': 'تعرف على كيفية تعريف الدوال واستخدامها في تنظيم الكود.',
        'code': "def greet(name):\n    return f'أهلا {name}!'\n\nprint(greet('فارس'))",
        'explanation': 'الدوال تساعدك في إعادة استخدام الكود وتنظيمه.'
    }
}

# قوالب HTML
templates = {
    "base": '''
<!doctype html>
<html lang="ar">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{{ title }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet" crossorigin="anonymous"/>
  <style>
    body { background: #f8f9fa; }
    .ace_editor { height: 300px; width: 100%; }
    .navbar { margin-bottom: 20px; }
    .result-box { border: 1px solid #ccc; background: #fff; padding: 15px; border-radius: 5px; min-height: 100px; }
    .lib-list { margin-top: 20px; }
    .home-sections {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 20px;
    }
    .section-item {
      flex: 1 1 180px;
      padding: 20px;
      border: 1px solid #ccc;
      background: #fff;
      border-radius: 8px;
      text-align: center;
    }
    .section-item a {
      text-decoration: none;
      color: #000;
      font-size: 1.2rem;
    }
    .tools-section {
      margin-top: 30px;
      padding: 20px;
      background: #fff;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
  </style>
  {% block head %}{% endblock %}
</head>
<body dir="rtl">
<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
  <div class="container-fluid">
    <a class="navbar-brand" href="{{ url_for('home') }}">موقع متكامل</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="تبديل التنقل">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav me-auto">
        <li class="nav-item"><a class="nav-link" href="{{ url_for('home') }}">الرئيسية</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('lessons_page') }}">الدروس</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('code_runner') }}">تشغيل الأكواد</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('libraries') }}">المكتبات</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('challenges') }}">التحديات</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('terminal') }}">التيرمنال</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('tools_page') }}">الأدوات</a></li>
        {% if session.get('username') %}
          <li class="nav-item"><a class="nav-link" href="{{ url_for('profile') }}">الملف الشخصي</a></li>
        {% endif %}
      </ul>
      <ul class="navbar-nav">
        {% if session.get('username') %}
          <li class="nav-item">
            <span class="navbar-text">مرحباً {{ session.get('username') }}</span>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('logout') }}">تسجيل خروج</a>
          </li>
        {% else %}
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('login') }}">تسجيل دخول</a>
          </li>
        {% endif %}
      </ul>
    </div>
  </div>
</nav>
<div class="container my-4">
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="alert alert-info">
        {% for message in messages %}
          <p>{{ message }}</p>
        {% endfor %}
      </div>
    {% endif %}
  {% endwith %}
  {% block content %}{% endblock %}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js" crossorigin="anonymous"></script>
{% block scripts %}{% endblock %}
</body>
</html>
''',

    "home": '''
{% extends "base" %}
{% block content %}
<h1 class="text-center mb-4">مرحباً في الموقع المتكامل</h1>
<div class="home-sections">
  <div class="section-item">
    <a href="{{ url_for('lessons_page') }}">الدروس</a>
  </div>
  <div class="section-item">
    <a href="{{ url_for('code_runner') }}">تشغيل الأكواد</a>
  </div>
  <div class="section-item">
    <a href="{{ url_for('libraries') }}">المكتبات</a>
  </div>
  <div class="section-item">
    <a href="{{ url_for('challenges') }}">التحديات</a>
  </div>
  <div class="section-item">
    <a href="{{ url_for('terminal') }}">التيرمنال</a>
  </div>
  <div class="section-item">
    <a href="{{ url_for('tools_page') }}">الأدوات</a>
  </div>
</div>
{% endblock %}
''',

    "tools": '''
{% extends "base" %}
{% block content %}
<h1 class="text-center mb-4">أدوات متنوعة</h1>

<div class="tools-section">
    <!-- Instagram Info Tool -->
    <section class="mb-5">
        <h3>معلومات حساب إنستغرام</h3>
        <form method="post" action="{{ url_for('tools_page') }}">
            <input type="hidden" name="tool" value="instagram_info">
            <div class="input-group">
                <input type="text" name="insta_id" placeholder="ID إنستغرام" class="form-control" required>
                <button type="submit" class="btn btn-primary">جلب</button>
            </div>
        </form>
        {% if insta_result %}
        <div class="card mt-3 p-3">
            <p>الاسم: {{ insta_result.full_name }}</p>
            <p>اسم المستخدم: {{ insta_result.username }}</p>
            <p>المتابعين: {{ insta_result.follower_count }}</p>
            <img src="{{ insta_result.profile_pic_url_hd }}" class="img-fluid rounded">
        </div>
        {% endif %}
    </section>

    <!-- Meta AI Chat -->
    <section class="mb-5">
        <h3>دردشة Meta AI</h3>
        <form method="post" action="{{ url_for('tools_page') }}">
            <input type="hidden" name="tool" value="meta_ai">
            <div class="input-group">
                <input type="text" name="meta_question" placeholder="اكتب سؤالك" class="form-control" required>
                <button type="submit" class="btn btn-success">إرسال</button>
            </div>
        </form>
        {% if meta_result %}
        <div class="alert alert-info mt-3"><pre>{{ meta_result }}</pre></div>
        {% endif %}
    </section>

    <!-- TikTok Search -->
    <section class="mb-5">
        <h3>بحث TikTok</h3>
        <form method="post" action="{{ url_for('tools_page') }}">
            <input type="hidden" name="tool" value="tiktok_search">
            <div class="input-group">
                <input type="text" name="tiktok_user" placeholder="اسم المستخدم" class="form-control" required>
                <button type="submit" class="btn btn-dark">بحث</button>
            </div>
        </form>
        {% if tiktok_result %}
        <div class="card mt-3 p-3"><pre>{{ tiktok_result | tojson(indent=2, ensure_ascii=False) }}</pre></div>
        {% endif %}
    </section>

    <!-- حساب إنستغرام تلقائي -->
    <section class="mb-5">
        <h3>إنشاء حساب إنستغرام تلقائي</h3>
        <form method="post" action="{{ url_for('tools_page') }}">
            <input type="hidden" name="tool" value="generate_insta">
            <button type="submit" class="btn btn-warning">إنشاء</button>
        </form>
        {% if insta_gen %}
        <div class="alert alert-success mt-3"><pre>{{ insta_gen }}</pre></div>
        {% endif %}
    </section>

    <!-- التبليغ على فيديو TikTok -->
    <section class="mb-5">
        <h3>تبليغ على فيديو TikTok</h3>
        <form method="post" action="{{ url_for('tools_page') }}">
            <input type="hidden" name="tool" value="report_tiktok">
            <div class="input-group">
                <input type="text" name="video_url" placeholder="رابط الفيديو" class="form-control" required>
                <button type="submit" class="btn btn-danger">تبليغ</button>
            </div>
        </form>
        {% if report_result %}
        <div class="alert alert-secondary mt-3"><pre>{{ report_result }}</pre></div>
        {% endif %}
    </section>
</div>
{% endblock %}
''',

    # باقي القوالب كما هي في الكود الأصلي
    "lessons": '''
{% extends "base" %}
{% block content %}
<h2 class="mb-4">الدروس التفاعلية</h2>
<div class="accordion" id="lessonsAccordion">
  {% for id, lesson in lessons.items() %}
  <div class="accordion-item">
    <h2 class="accordion-header" id="heading{{ id }}">
      <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse{{ id }}" aria-expanded="false" aria-controls="collapse{{ id }}">
        {{ lesson.title }}
      </button>
    </h2>
    <div id="collapse{{ id }}" class="accordion-collapse collapse" aria-labelledby="heading{{ id }}" data-bs-parent="#lessonsAccordion">
      <div class="accordion-body">
        <p>{{ lesson.description }}</p>
        <h5>الكود:</h5>
        <pre class="bg-light p-3">{{ lesson.code }}</pre>
        <h5>الشرح:</h5>
        <p>{{ lesson.explanation }}</p>
        <a href="{{ url_for('lesson_detail', lesson_id=id) }}" class="btn btn-info">تجربة الكود</a>
      </div>
    </div>
  </div>
  {% endfor %}
</div>
{% endblock %}
''',

    "lesson_detail": '''
{% extends "base" %}
{% block head %}
<script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.14/ace.js" crossorigin="anonymous"></script>
{% endblock %}
{% block content %}
<h2>{{ lesson.title }}</h2>
<p>{{ lesson.description }}</p>
<form method="POST">
  <div id="editor">{{ lesson.code }}</div>
  <textarea name="code" id="code" hidden>{{ lesson.code }}</textarea>
  <button type="submit" class="btn btn-primary mt-3">تشغيل الكود ▶️</button>
</form>
{% if output %}
  <div class="mt-4">
    <h4>النتيجة:</h4>
    <pre class="bg-dark text-white p-3">{{ output }}</pre>
  </div>
{% endif %}
{% endblock %}
{% block scripts %}
<script>
  var editor = ace.edit("editor");
  editor.setTheme("ace/theme/monokai");
  editor.session.setMode("ace/mode/python");
  document.querySelector("form").addEventListener("submit", function(e) {
    document.getElementById("code").value = editor.getValue();
  });
</script>
{% endblock %}
''',

    "code_runner": '''
{% extends "base" %}
{% block head %}
<script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.14/ace.js" crossorigin="anonymous"></script>
{% endblock %}
{% block content %}
<h2>تشغيل كود بايثون</h2>
<form method="POST">
  <div id="editor">{{ code|default('print("أهلا وسهلا")') }}</div>
  <textarea name="code" id="code" hidden>{{ code|default('print("أهلا وسهلا")') }}</textarea>
  <button type="submit" class="btn btn-primary mt-3">تشغيل الكود ▶️</button>
</form>
{% if output %}
  <div class="mt-4">
    <h4>النتيجة:</h4>
    <pre class="bg-dark text-white p-3">{{ output }}</pre>
  </div>
{% endif %}
{% endblock %}
{% block scripts %}
<script>
  var editor = ace.edit("editor");
  editor.setTheme("ace/theme/monokai");
  editor.session.setMode("ace/mode/python");
  document.querySelector("form").addEventListener("submit", function(e) {
    document.getElementById("code").value = editor.getValue();
  });
</script>
{% endblock %}
''',

    "login": '''
{% extends "base" %}
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-6">
    <h2 class="text-center">تسجيل الدخول</h2>
    <form method="POST">
      <div class="mb-3">
        <label for="username" class="form-label">اسم المستخدم</label>
        <input type="text" class="form-control" id="username" name="username" placeholder="ادخل اسم المستخدم" required>
      </div>
      <div class="mb-3">
        <label for="password" class="form-label">كلمة المرور</label>
        <input type="password" class="form-control" id="password" name="password" placeholder="ادخل كلمة المرور" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">دخول</button>
    </form>
  </div>
</div>
{% endblock %}
''',

    "profile": '''
{% extends "base" %}
{% block content %}
<h2>الملف الشخصي</h2>
<p>مرحباً {{ session.get('username') }}, هنا سجل الأكواد التي شغلتها:</p>
{% if history and history|length > 0 %}
  <ul class="list-group">
    {% for item in history %}
      <li class="list-group-item">
        <strong>التاريخ:</strong> {{ item.timestamp }}<br>
        <strong>الكود:</strong> <pre>{{ item.code }}</pre>
        <strong>النتيجة:</strong> <pre>{{ item.output }}</pre>
      </li>
    {% endfor %}
  </ul>
{% else %}
  <p>لا توجد أكواد مسجلة حتى الآن.</p>
{% endif %}
{% endblock %}
''',

    "libraries": '''
{% extends "base" %}
{% block content %}
<h2>إدارة المكتبات</h2>
<div class="row">
  <div class="col-md-6">
    <form method="POST">
      <div class="mb-3">
        <label for="library_name" class="form-label">اكتب اسم المكتبة</label>
        <input type="text" class="form-control" id="library_name" name="library_name" placeholder="مثال: requests" required>
      </div>
      <button type="submit" class="btn btn-success">تحميل المكتبة</button>
    </form>
    {% if install_result %}
      <div class="mt-3 result-box">
        <strong>نتيجة التحميل:</strong>
        <p>{{ install_result }}</p>
      </div>
    {% endif %}
  </div>
  <div class="col-md-6">
    <h4>المكتبات المثبتة</h4>
    {% if installed_libraries and installed_libraries|length > 0 %}
      <ul class="list-group lib-list">
        {% for lib in installed_libraries %}
          <li class="list-group-item">
            <a href="{{ url_for('library_detail', library_name=lib) }}">{{ lib }}</a>
          </li>
        {% endfor %}
      </ul>
    {% else %}
      <p>لا توجد مكتبات مثبتة حتى الآن.</p>
    {% endif %}
  </div>
</div>
{% endblock %}
''',

    "library_detail": '''
{% extends "base" %}
{% block content %}
<h2>تفاصيل المكتبة: {{ library_name }}</h2>
<p>تم تثبيت المكتبة بنجاح وتعتبر من المكتبات المهمة لتطوير تطبيقات بايثون.</p>
<a href="{{ url_for('libraries') }}" class="btn btn-secondary">رجوع لإدارة المكتبات</a>
{% endblock %}
''',

    "challenges": '''
{% extends "base" %}
{% block content %}
<h2>التحديات البرمجية</h2>
{% if challenges and challenges|length > 0 %}
  <div class="list-group">
    {% for chal in challenges %}
      <a href="{{ url_for('challenge_detail', challenge_id=chal.id) }}" class="list-group-item list-group-item-action">
        <h5 class="mb-1">{{ chal.title }}</h5>
        <p class="mb-1">{{ chal.description }}</p>
      </a>
    {% endfor %}
  </div>
{% else %}
  <p>لا توجد تحديات حالياً.</p>
{% endif %}
{% endblock %}
''',

    "challenge_detail": '''
{% extends "base" %}
{% block content %}
<h2>{{ challenge.title }}</h2>
<p>{{ challenge.description }}</p>
<h5>كود المثال:</h5>
<pre class="bg-light p-3">{{ challenge.sample_code }}</pre>
<a href="{{ url_for('challenges') }}" class="btn btn-secondary">رجوع للتحديات</a>
{% endblock %}
''',

    "terminal": '''
{% extends "base" %}
{% block head %}
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jquery.terminal/2.30.2/css/jquery.terminal.min.css" />
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery.terminal/2.30.2/js/jquery.terminal.min.js"></script>
<style>
  #terminal {
    width: 100%;
    height: 400px;
    direction: ltr;
    text-align: left;
  }
</style>
{% endblock %}
{% block content %}
<h2 class="mb-4">التيرمنال الجديد</h2>
<div id="terminal"></div>
<p class="text-muted mt-2">ملاحظه : الترمنال الجديد سيكون فيه بعض الاخطاء سيتم تحسينها قريبا 😶‍🌫️</p>
{% endblock %}
{% block scripts %}
<script>
  $('#terminal').terminal(function(command, term) {
    if (command.trim() !== '') {
      $.ajax({
        url: '{{ url_for("terminal_run") }}',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ command: command }),
        dataType: 'json',
        success: function(response) {
          term.echo(response.output);
        },
        error: function() {
          term.error('حدث خطأ أثناء تنفيذ الأمر');
        }
      });
    } else {
      term.echo('');
    }
  }, {
    greetings: 'مرحبا في التيرمنال الجديد!',
    prompt: '$ '
  });
</script>
{% endblock %}
'''
}

def render_template(name, **context):
    from jinja2 import Environment, BaseLoader
    env = Environment(loader=BaseLoader())
    env.globals.update(url_for=url_for, session=session, get_flashed_messages=get_flashed_messages)
    def load_template(template_name):
        return templates.get(template_name, '')
    env.loader.get_source = lambda environment, template: (load_template(template), template, lambda: True)
    tmpl = env.from_string(templates[name])
    return tmpl.render(**context)

def execute_code(code):
    output = ''
    restricted_globals = {"__builtins__": {"print": print, "range": range}}
    try:
        old_stdout = sys.stdout
        redirected_output = sys.stdout = io.StringIO()
        exec(code, restricted_globals)
        output = redirected_output.getvalue()
    except Exception as e:
        output = f'خطأ: {e}'
    finally:
        sys.stdout = old_stdout
    if session.get('username'):
        user = User.query.filter_by(username=session.get('username')).first()
        if user:
            history = CodeHistory(
                user_id=user.id,
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                code=code,
                output=output
            )
            db.session.add(history)
            db.session.commit()
    return output

# مسارات قسم البرمجة التعليمي
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password, password):
                session.permanent = True
                session['username'] = username
                flash('تم تسجيل الدخول بنجاح')
                return redirect(url_for('home'))
            else:
                flash('كلمة المرور غير صحيحة')
                return redirect(url_for('login'))
        else:
            hashed = generate_password_hash(password)
            new_user = User(username=username, password=hashed)
            db.session.add(new_user)
            db.session.commit()
            session.permanent = True
            session['username'] = username
            flash('تم إنشاء الحساب وتسجيل الدخول بنجاح')
            return redirect(url_for('home'))
    return render_template("login", title="تسجيل الدخول")

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج')
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template("home", title="الرئيسية")

@app.route('/lessons')
def lessons_page():
    return render_template("lessons", title="الدروس", lessons=lessons)

@app.route('/lesson/<lesson_id>', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def lesson_detail(lesson_id):
    lesson = lessons.get(lesson_id)
    if not lesson:
        return redirect(url_for('lessons_page'))
    output = ''
    code = lesson['code']
    if request.method == 'POST':
        code = request.form['code']
        output = execute_code(code)
    return render_template("lesson_detail", title=lesson['title'], lesson=lesson, output=output)

@app.route('/code-runner', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def code_runner():
    output = ''
    code = request.form.get('code', 'print("أهلا وسهلا")')
    if request.method == 'POST':
        output = execute_code(code)
    return render_template("code_runner", title="تشغيل الأكواد", code=code, output=output)

@app.route('/profile')
def profile():
    if not session.get('username'):
        flash('يجب تسجيل الدخول للوصول للملف الشخصي')
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session.get('username')).first()
    history = CodeHistory.query.filter_by(user_id=user.id).all() if user else []
    return render_template("profile", title="الملف الشخصي", history=history)

@app.route('/libraries', methods=['GET', 'POST'])
def libraries():
    install_result = None
    user = None
    installed_libraries = []
    if session.get('username'):
        user = User.query.filter_by(username=session.get('username')).first()
        installed_libraries = [lib.library_name for lib in InstalledLibrary.query.filter_by(user_id=user.id).all()]
    if request.method == 'POST':
        lib_name = request.form.get('library_name')
        if lib_name and user:
            exists = InstalledLibrary.query.filter_by(user_id=user.id, library_name=lib_name).first()
            if not exists:
                new_lib = InstalledLibrary(user_id=user.id, library_name=lib_name)
                db.session.add(new_lib)
                db.session.commit()
                installed_libraries.append(lib_name)
                install_result = f'تم تثبيت المكتبة {lib_name} بنجاح!'
            else:
                install_result = f'المكتبة {lib_name} مثبتة بالفعل.'
    return render_template("libraries", title="المكتبات", install_result=install_result, installed_libraries=installed_libraries)

@app.route('/library/<library_name>')
def library_detail(library_name):
    return render_template("library_detail", title=f"تفاصيل {library_name}", library_name=library_name)

@app.route('/challenges')
def challenges():
    all_challenges = Challenge.query.all()
    return render_template("challenges", title="التحديات", challenges=all_challenges)

@app.route('/challenge/<int:challenge_id>')
def challenge_detail(challenge_id):
    chal = Challenge.query.get(challenge_id)
    if not chal:
        flash("التحدي غير موجود")
        return redirect(url_for('challenges'))
    return render_template("challenge_detail", title=chal.title, challenge=chal)

@app.route('/terminal')
def terminal():
    return render_template("terminal", title="التيرمنال")

@app.route('/terminal_run', methods=['POST'])
def terminal_run():
    data = request.get_json()
    command = data.get('command', '')
    try:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        output = result.stdout.decode() + result.stderr.decode()
    except Exception as e:
        output = f'خطأ: {e}'
    return jsonify({'output': output})

# مسارات قسم الأدوات
@app.route('/tools', methods=['GET', 'POST'])
def tools_page():
    insta_result = meta_result = tiktok_result = insta_gen = report_result = None

    if request.method == 'POST':
        tool = request.form.get('tool')

        if tool == 'instagram_info':
            user_id = request.form.get('insta_id')
            try:
                headers = {
                    'User-Agent': "Instagram 167.0.0.24.120 Android",
                    'Accept-Language': "ar"
                }
                r = requests.get(f"https://i.instagram.com/api/v1/users/{user_id}/info/", headers=headers)
                if r.status_code == 200:
                    insta_result = r.json()['user']
            except:
                pass

        elif tool == 'meta_ai':
            q = request.form.get('meta_question')
            try:
                res = requests.get("https://www.meta.ai", headers={'User-Agent': "Mozilla/5.0"})
                token = re.search(r'"token":"(.*?)"', res.text)
                if token:
                    meta_result = f"رد تجريبي (Token): {token.group(1)}\\nسؤالك: {q}"
                else:
                    meta_result = "لم يتم العثور على التوكن"
            except Exception as e:
                meta_result = str(e)

        elif tool == 'tiktok_search':
            username = request.form.get('tiktok_user')
            try:
                headers = {
                    'Host': "ttpub.linuxtech.io:5004",
                    'User-Agent': "Dart/3.5 (dart:io)",
                    'Content-Type': "application/json"
                }
                res = requests.post("https://ttpub.linuxtech.io:5004/api/search", data=json.dumps({"username": username}), headers=headers)
                tiktok_result = res.json()
            except Exception as e:
                tiktok_result = {"error": str(e)}

        elif tool == 'generate_insta':
            name = "user" + str(random.randint(1000, 9999))
            email = name + "@test.com"
            password = name + "@123"
            insta_gen = f"Email: {email}\\nPassword: {password}\\nUsername: {name}"

        elif tool == 'report_tiktok':
            url = request.form.get('video_url')
            report_result = f"تم إرسال بلاغ (تجريبي) إلى الرابط: {url}"

    return render_template("tools", title="الأدوات",
                         insta_result=insta_result,
                         meta_result=meta_result,
                         tiktok_result=tiktok_result,
                         insta_gen=insta_gen,
                         report_result=report_result)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
