import csv
import io
import json
import unicodedata
import openpyxl
from functools import wraps
from datetime import datetime

from flask import (
    Flask, flash, jsonify, redirect, render_template,
    request, session, url_for,
)
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache                          # ← MỚI
from werkzeug.security import check_password_hash, generate_password_hash

# ─── App Config ───────────────────────────────────────────

app = Flask(__name__)
app.secret_key = 'super_secret_premium_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vocabulary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── [MỚI] Cache config — dùng SimpleCache (RAM).
#    Production: đổi CACHE_TYPE thành 'RedisCache' và thêm CACHE_REDIS_URL.
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300   # 5 phút

# ── [MỚI] Pagination defaults
app.config['PAGE_SIZE_DEFAULT'] = 20
app.config['PAGE_SIZE_MAX'] = 100

db = SQLAlchemy(app)
cache = Cache(app)                                       # ← MỚI


# ─── Models ───────────────────────────────────────────────

class Category(db.Model):
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vocabularies = db.relationship(
        'Vocabulary', backref='category', lazy='dynamic',   # ← lazy='dynamic' thay vì True
        cascade='all, delete-orphan',
    )


class Vocabulary(db.Model):
    __tablename__ = 'vocabulary'

    # ── [MỚI] Index để tăng tốc query lọc và sắp xếp
    __table_args__ = (
        db.Index('ix_vocab_category', 'category_id'),
        db.Index('ix_vocab_word',     'word'),
    )

    id            = db.Column(db.Integer, primary_key=True)
    word          = db.Column(db.String(100), nullable=False)
    pos           = db.Column(db.String(50))
    pronunciation = db.Column(db.String(100))
    meaning       = db.Column(db.String(200), nullable=False)
    example       = db.Column(db.Text)
    category_id   = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)


class Question(db.Model):
    __tablename__ = 'question'

    # ── [MỚI] Index để tăng tốc lọc theo topic + level
    __table_args__ = (
        db.Index('ix_question_topic', 'topic'),
        db.Index('ix_question_level', 'level'),
        db.Index('ix_question_topic_level', 'topic', 'level'),
    )

    id             = db.Column(db.Integer, primary_key=True)
    question_text  = db.Column(db.Text, nullable=False)
    option_a       = db.Column(db.String(255), nullable=False)
    option_b       = db.Column(db.String(255), nullable=False)
    option_c       = db.Column(db.String(255), nullable=False)
    option_d       = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)
    explanation    = db.Column(db.Text)
    topic          = db.Column(db.String(100))
    level          = db.Column(db.String(50))


class GrammarTopic(db.Model):
    __tablename__ = 'grammar_topic'

    __table_args__ = (
        db.Index('ix_grammar_title', 'title'),
    )

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    content     = db.Column(db.Text)  # Nội dung chi tiết ngữ pháp
    level       = db.Column(db.String(50), default='Core')
    sort_order  = db.Column(db.Integer, default=0)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class User(db.Model):
    __tablename__ = 'user'

    # ── [MỚI] Index trên username (lookup khi login)
    __table_args__ = (
        db.Index('ix_user_username', 'username'),
    )

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=True) # Mới
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)      # Mới


# ─── [MỚI] Pagination helper ──────────────────────────────

def _paginate(query):
    """
    Áp dụng phân trang từ query params ?page=1&per_page=20.
    Trả về dict gồm items, meta (page, per_page, total, pages).
    """
    try:
        page     = max(1, int(request.args.get('page', 1)))
        per_page = min(
            int(request.args.get('per_page', app.config['PAGE_SIZE_DEFAULT'])),
            app.config['PAGE_SIZE_MAX'],
        )
    except (ValueError, TypeError):
        page, per_page = 1, app.config['PAGE_SIZE_DEFAULT']

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        'items': pagination.items,
        'meta': {
            'page':     pagination.page,
            'per_page': pagination.per_page,
            'total':    pagination.total,
            'pages':    pagination.pages,
        },
    }


# ─── [MỚI] Cache invalidation helpers ────────────────────

def _invalidate_vocab_cache(category_id=None):
    """Xóa cache liên quan đến vocabulary sau khi có thay đổi dữ liệu."""
    cache.delete('categories_list')
    cache.delete('vocab_all')
    if category_id:
        cache.delete(f'vocab_cat_{category_id}')


def _invalidate_question_cache():
    """Xóa cache liên quan đến questions sau khi có thay đổi dữ liệu."""
    cache.delete('question_topics')
    cache.delete('question_levels')
    # Xóa các cache key dạng questions_*
    cache.clear()   # SimpleCache không hỗ trợ pattern delete — dùng clear() toàn bộ


def _invalidate_grammar_cache():
    """Xóa cache liên quan đến grammar topics sau khi có thay đổi dữ liệu."""
    cache.delete('grammar_topics')


# ─── Text Helpers ─────────────────────────────────────────

def _normalize_vn(text):
    """Bỏ dấu tiếng Việt, chuyển lowercase — dùng để so khớp header."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def _decode_bytes(raw):
    for enc in ('utf-8-sig', 'utf-8', 'cp1252'):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return None


def _strip_bom(text):
    return text.lstrip('\ufeff')


def _detect_csv_delimiter(text):
    first = text.split('\n')[0]
    return ';' if first.count(';') > first.count(',') else ','


def _detect_text_separator(first_line):
    if '\t' in first_line:  return '\t'
    if '|'  in first_line:  return '|'
    if ':'  in first_line:  return ':'
    if ' - ' in first_line: return ' - '
    if '-'  in first_line:  return '-'
    return None


def _parse_plain_text(text):
    lines = [
        l.strip() for l in text.splitlines()
        if l.strip() and not l.strip().startswith('#')
    ]
    if not lines:
        return []

    sep = _detect_text_separator(lines[0])
    if sep is None:
        raise ValueError(
            'Không tìm thấy dấu phân cách trong file TXT.\n'
            'Sử dụng Tab, |, :, hoặc " - " để tách các trường.\n\n'
            'Ví dụ:\n'
            '  hello - xin chào\n'
            '  book\t/bʊk/\tnoun\tsách\n'
            '  apple | noun | /ˈæp.əl/ | quả táo'
        )

    return [[p.strip() for p in line.split(sep)] for line in lines]


# ─── Header Mapping ───────────────────────────────────────

KEY_MAP = {
    'word':          ['word', 'tu vung', 'tu', 'english', 'from'],
    'pos':           ['part of speech', 'pos', 'loai tu', 'word type'],
    'pronunciation': ['ipa', 'pronunciation', 'phat am'],
    'meaning':       ['vietnamese meaning', 'meaning', 'nghia', 'vietnamese', 'to', 'definition'],
    'example':       ['example', 'vi du', 'sentence'],
}

KEY_MAP_NORM = {
    field: [_normalize_vn(c) for c in cands]
    for field, cands in KEY_MAP.items()
}


def _has_header(rows):
    if not rows or not rows[0]:
        return False
    headers_norm = [_normalize_vn(h) for h in rows[0]]
    return any(
        cand in headers_norm
        for cands in KEY_MAP_NORM.values()
        for cand in cands
    )


def _build_header_index(headers):
    headers_norm = [_normalize_vn(h) for h in headers]
    index = {}
    for field, candidates in KEY_MAP_NORM.items():
        for i, hn in enumerate(headers_norm):
            if hn in candidates:
                index[field] = i
                break
    return index


def _extract_from_row_by_index(row, header_index):
    def _get(field):
        idx = header_index.get(field)
        if idx is not None and idx < len(row):
            return (row[idx] or '').strip()
        return ''

    word = _get('word')
    if not word:
        return None
    return {
        'word': word, 'pos': _get('pos'),
        'pronunciation': _get('pronunciation'),
        'meaning': _get('meaning'), 'example': _get('example'),
    }


def _extract_from_row_by_position(row):
    n = len(row)
    if n >= 6:
        word = (row[1] or '').strip()
        if not word: return None
        return {'word': word, 'pronunciation': (row[2] or '').strip(),
                'pos': (row[3] or '').strip(), 'meaning': (row[4] or '').strip(),
                'example': (row[5] or '').strip()}
    if n >= 5:
        word = (row[0] or '').strip()
        if not word: return None
        return {'word': word, 'pos': (row[1] or '').strip(),
                'pronunciation': (row[2] or '').strip(),
                'meaning': (row[3] or '').strip(), 'example': (row[4] or '').strip()}
    if n >= 4:
        word = (row[0] or '').strip()
        if not word: return None
        return {'word': word, 'pronunciation': (row[1] or '').strip(),
                'meaning': (row[2] or '').strip(), 'example': (row[3] or '').strip()}
    if n >= 3:
        word = (row[0] or '').strip()
        if not word: return None
        return {'word': word, 'pronunciation': (row[1] or '').strip(),
                'meaning': (row[2] or '').strip(), 'example': ''}
    if n >= 2:
        word = (row[0] or '').strip()
        if not word: return None
        return {'word': word, 'pos': '', 'pronunciation': '',
                'meaning': (row[1] or '').strip(), 'example': ''}
    return None


# ─── Auth Helpers ─────────────────────────────────────────

def is_ajax():
    return request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

def is_admin_logged_in():
    return session.get('admin_logged_in') is True

def is_user_logged_in():
    return session.get('user_logged_in') is True

def is_any_logged_in():
    return is_admin_logged_in() or is_user_logged_in()

def get_current_username():
    return session.get('username', '')


def require_login(view):
    """Yêu cầu user đã đăng nhập (không tính admin panel)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not is_user_logged_in():
            if is_ajax():
                return jsonify({'success': False, 'message': 'Vui lòng đăng nhập.'}), 401
            flash('Vui lòng đăng nhập để tiếp tục.')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not is_admin_logged_in():
            if is_ajax():
                return jsonify({'success': False, 'message': 'Chưa đăng nhập admin!'}), 401
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper


def _respond_error(message, fallback_render=None, **ctx):
    if is_ajax():
        return jsonify({'success': False, 'message': message})
    flash(message)
    if fallback_render:
        return fallback_render(**ctx)
    return None


def _respond_success(message, redirect_url=None):
    if is_ajax():
        return jsonify({'success': True, 'message': message})
    flash(message, 'success')
    if redirect_url:
        return redirect(redirect_url)
    return None


class PasswordError(Exception):
    pass


def validate_new_password(current_pw, new_pw, confirm_pw, verify_fn):
    if not verify_fn(current_pw):
        raise PasswordError('Mật khẩu hiện tại không đúng.')
    if len(new_pw) < 6:
        raise PasswordError('Mật khẩu mới phải có ít nhất 6 ký tự.')
    if new_pw != confirm_pw:
        raise PasswordError('Mật khẩu nhập lại không khớp.')


# ─── DB Init ──────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin',
                                password_hash=generate_password_hash('123456')))
        if not User.query.filter_by(username='user').first():
            db.session.add(User(username='user',
                                password_hash=generate_password_hash('123456')))

        if not Category.query.first():
            cats = [
                Category(name='1000 Từ Thông Dụng'),
                Category(name='Tiếng Anh Giao Tiếp'),
                Category(name='3000 Từ Oxford'),
            ]
            db.session.add_all(cats)
            db.session.flush()

            db.session.add_all([
                Vocabulary(word='Serendipity', pos='noun',
                           pronunciation='/ˌser.ənˈdɪp.ə.ti/',
                           meaning='Sự tình cờ, may mắn',
                           example='We found this place by serendipity.',
                           category_id=cats[0].id),
                Vocabulary(word='Hello', pos='exclamation',
                           pronunciation='/həˈloʊ/',
                           meaning='Xin chào',
                           example='Hello, how are you?',
                           category_id=cats[1].id),
                Vocabulary(word='Ubiquitous', pos='adjective',
                           pronunciation='/juːˈbɪk.wɪ.təs/',
                           meaning='Có mặt ở khắp nơi',
                           example='Smartphones are ubiquitous nowadays.',
                           category_id=cats[2].id),
            ])

        if not GrammarTopic.query.first():
            db.session.add_all([
                GrammarTopic(
                    title='Present Simple',
                    description='Diễn tả sự thật hiển nhiên và thói quen hằng ngày.',
                    level='Basic',
                    sort_order=1,
                ),
                GrammarTopic(
                    title='Past Continuous',
                    description='Mô tả hành động đang diễn ra tại một thời điểm trong quá khứ.',
                    level='Basic',
                    sort_order=2,
                ),
                GrammarTopic(
                    title='Future Perfect',
                    description='Diễn tả hành động sẽ hoàn thành trước một mốc tương lai.',
                    level='Intermediate',
                    sort_order=3,
                ),
                GrammarTopic(
                    title='Conditionals Type 2',
                    description='Dùng cho giả định không có thật ở hiện tại.',
                    level='Intermediate',
                    sort_order=4,
                ),
            ])

        db.session.commit()


# ═══════════════════════════════════════════════════════════
#  VOCABULARY IMPORT
# ═══════════════════════════════════════════════════════════

def _import_vocab_from_file(raw_data, category_id, filename=''):
    fname = filename.lower()
    rows  = []

    if fname.endswith('.xlsx') or raw_data[:4] == b'PK\x03\x04':
        wb   = openpyxl.load_workbook(io.BytesIO(raw_data), data_only=True)
        rows = [
            [str(c) if c is not None else '' for c in r]
            for r in wb.active.iter_rows(values_only=True)
        ]
    elif fname.endswith('.txt'):
        text = _decode_bytes(raw_data)
        if text is None:
            raise ValueError('Không nhận diện được bảng mã file TXT.')
        rows = _parse_plain_text(_strip_bom(text))
    else:
        text = _decode_bytes(raw_data)
        if text is None:
            raise ValueError('Không nhận diện được bảng mã file CSV.')
        text = _strip_bom(text)
        rows = list(csv.reader(
            io.StringIO(text, newline=None),
            delimiter=_detect_csv_delimiter(text),
        ))

    if len(rows) <= 1:
        raise ValueError('File không có dữ liệu hoặc cấu trúc không hợp lệ.')

    count = _import_vocab_from_rows(rows, category_id)
    _invalidate_vocab_cache(category_id)                # ← [MỚI] xóa cache
    return count


def _import_vocab_from_rows(rows, category_id):
    if not rows:
        raise ValueError('Không có dữ liệu để import.')

    use_header   = _has_header(rows)
    data_rows    = rows[1:] if use_header else rows
    header_index = _build_header_index(rows[0]) if use_header else None

    count = 0
    # ── [MỚI] Bulk insert thay vì add từng dòng một
    objects = []
    for row in data_rows:
        if not row or not any((cell or '').strip() for cell in row):
            continue
        data = (
            _extract_from_row_by_index(row, header_index)
            if header_index is not None
            else _extract_from_row_by_position(row)
        )
        if data is None:
            continue
        objects.append(Vocabulary(
            word=data['word'], pos=data.get('pos', ''),
            pronunciation=data.get('pronunciation', ''),
            meaning=data['meaning'], example=data.get('example', ''),
            category_id=category_id,
        ))
        count += 1

    if objects:
        db.session.bulk_save_objects(objects)           # ← [MỚI] bulk insert
        db.session.commit()

    return count


# ═══════════════════════════════════════════════════════════
#  PAGE ROUTES
# ═══════════════════════════════════════════════════════════

@app.route('/')
def home():
    return render_template('about.html')


@app.route('/about')
def about():
    return redirect(url_for('home'))


@app.route('/study')
@require_login
def index():
    user = User.query.filter_by(username=get_current_username()).first()
    return render_template('index.html', user=user)


# ─── Auth ─────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_user_logged_in():
        return redirect(url_for('index'))

    if request.method != 'POST':
        return render_template('user_auth.html', auth_mode='login')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password:
        resp = _respond_error('Vui lòng nhập đầy đủ thông tin.',
                              fallback_render=render_template,
                              template_name_or_list='user_auth.html',
                              auth_mode='login')
        return resp or render_template('user_auth.html', auth_mode='login')

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_logged_in']  = True
        session['username']        = user.username
        if is_ajax():
            return jsonify({'success': True, 'username': user.username})
        return redirect(url_for('index'))

    resp = _respond_error('Sai tên đăng nhập hoặc mật khẩu.',
                          fallback_render=render_template,
                          template_name_or_list='user_auth.html',
                          auth_mode='login')
    return resp or render_template('user_auth.html', auth_mode='login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_user_logged_in():
        return redirect(url_for('index'))

    if request.method != 'POST':
        return render_template('user_auth.html', auth_mode='register')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    confirm  = request.form.get('confirm_password', '')

    errors = []
    if len(username) < 3:
        errors.append('Tên đăng nhập phải có ít nhất 3 ký tự.')
    if len(password) < 6:
        errors.append('Mật khẩu phải có ít nhất 6 ký tự.')
    if password != confirm:
        errors.append('Mật khẩu nhập lại không khớp.')
    if User.query.filter_by(username=username).first():
        errors.append('Tên đăng nhập đã tồn tại.')

    if errors:
        flash(errors[0])
        return render_template('user_auth.html', auth_mode='register')

    db.session.add(User(username=username,
                        password_hash=generate_password_hash(password)))
    db.session.commit()
    flash('Tạo tài khoản thành công. Mời bạn đăng nhập.', 'success')
    return redirect(url_for('login'))


@app.route('/account', methods=['GET', 'POST'])
@require_login
def account():
    username = get_current_username()

    if request.method != 'POST':
        return render_template('account.html', username=username)

    user = User.query.filter_by(username=username).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))

    try:
        validate_new_password(
            request.form.get('current_password', ''),
            request.form.get('new_password', ''),
            request.form.get('confirm_password', ''),
            lambda pw: check_password_hash(user.password_hash, pw),
        )
    except PasswordError as e:
        resp = _respond_error(str(e), fallback_render=render_template,
                              template_name_or_list='account.html', username=username)
        return resp or render_template('account.html', username=username)

    user.password_hash = generate_password_hash(request.form.get('new_password', ''))
    db.session.commit()
    resp = _respond_success('Đổi mật khẩu thành công.', redirect_url=url_for('account'))
    return resp or render_template('account.html', username=username)


@app.route('/logout')
def logout():
    session.pop('user_logged_in', None)
    session.pop('username', None)
    return redirect(url_for('home'))


# ─── Quiz ─────────────────────────────────────────────────

@app.route('/quiz/topics')
@require_login
def quiz_topics():
    return render_template('quiz_topics.html')


@app.route('/quiz/take')
@require_login
def quiz_take():
    return render_template('quiz_take.html')


@app.route('/quiz/results')
@require_login
def quiz_results():
    return render_template('quiz_results.html')


@app.route('/quiz/review')
@require_login
def quiz_review():
    return render_template('quiz_take.html', review_mode=True)


# ─── Admin Panel ──────────────────────────────────────────

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password   = request.form.get('password', '')
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user and check_password_hash(admin_user.password_hash, password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        flash('Sai mật khẩu admin!')
        return render_template('login.html')

    if not is_admin_logged_in():
        return render_template('login.html')

    return render_template(
        'admin.html',
        categories=Category.query.all(),
        # ── [MỚI] Chỉ load 50 từ mới nhất trong admin preview (tránh load toàn bộ)
        vocabularies=Vocabulary.query.order_by(Vocabulary.id.desc()).limit(50).all(),
    )


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin'))


@app.route('/admin/grammar')
@require_admin
def admin_grammar():
    return render_template(
        'admin_grammar.html',
        grammar_topics=GrammarTopic.query.order_by(GrammarTopic.sort_order, GrammarTopic.id).all()
    )


@app.route('/admin/questions')
@require_admin
def admin_questions():
    return render_template('admin_questions.html')


@app.route('/admin/accounts')
@require_admin
def admin_accounts():
    users = User.query.all()
    # Tính số user mới trong tháng này (demo)
    from datetime import datetime, timedelta
    first_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_count = User.query.filter(User.created_at >= first_of_month).count()

    return render_template('admin_accounts.html',
                           users=users,
                           new_users_this_month=new_users_count)


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@require_admin
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('Không tìm thấy người dùng.', 'error')
        return redirect(url_for('admin_accounts'))

    if user.username == 'admin':
        flash('Không thể xoá tài khoản admin hệ thống!', 'error')
        return redirect(url_for('admin_accounts'))

    db.session.delete(user)
    db.session.commit()
    flash(f"Đã xoá tài khoản '{user.username}' thành công.", 'success')
    return redirect(url_for('admin_accounts'))


@app.route('/admin/add_category', methods=['POST'])
@require_admin
def add_category():
    name = request.form.get('name', '').strip()
    if name:
        db.session.add(Category(name=name))
        db.session.commit()
        _invalidate_vocab_cache()                       # ← [MỚI]
    return redirect(url_for('admin'))


@app.route('/admin/add_grammar_topic', methods=['POST'])
@require_admin
def add_grammar_topic():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    content = request.form.get('content', '').strip()
    level = request.form.get('level', 'Core').strip() or 'Core'

    if not title or not description:
        flash('Vui lòng nhập đủ tiêu đề và mô tả ngữ pháp!')
        return redirect(url_for('admin_grammar'))

    next_order = (db.session.query(db.func.max(GrammarTopic.sort_order)).scalar() or 0) + 1
    db.session.add(GrammarTopic(
        title=title,
        description=description,
        content=content,
        level=level,
        sort_order=next_order,
    ))
    db.session.commit()
    _invalidate_grammar_cache()
    flash('Đã thêm chủ điểm ngữ pháp mới.', 'success')
    return redirect(url_for('admin_grammar'))


@app.route('/admin/delete_grammar_topic/<int:topic_id>')
@require_admin
def delete_grammar_topic(topic_id):
    topic = GrammarTopic.query.get(topic_id)
    if topic:
        db.session.delete(topic)
        db.session.commit()
        _invalidate_grammar_cache()
        flash('Đã xóa chủ điểm ngữ pháp.', 'success')
    return redirect(url_for('admin_grammar'))


@app.route('/admin/edit_grammar_topic', methods=['POST'])
@require_admin
def edit_grammar_topic():
    topic_id = request.form.get('id')
    topic = GrammarTopic.query.get(topic_id)
    if not topic:
        flash('Không tìm thấy chủ điểm ngữ pháp cần sửa.', 'error')
        return redirect(url_for('admin_grammar'))

    topic.title = request.form.get('title', '').strip()
    topic.description = request.form.get('description', '').strip()
    topic.level = request.form.get('level', 'Core').strip()
    topic.content = request.form.get('content', '').strip()

    db.session.commit()
    _invalidate_grammar_cache()
    flash('Cập nhật chủ điểm ngữ pháp thành công.', 'success')
    return redirect(url_for('admin_grammar'))


@app.route('/admin/delete_category/<int:category_id>')
@require_admin
def delete_category(category_id):
    cat = Category.query.get(category_id)
    if cat:
        db.session.delete(cat)
        db.session.commit()
        _invalidate_vocab_cache(category_id)            # ← [MỚI]
    return redirect(url_for('admin'))


@app.route('/admin/clear_category/<int:category_id>')
@require_admin
def clear_category(category_id):
    cat = Category.query.get(category_id)
    if cat:
        Vocabulary.query.filter_by(category_id=category_id).delete()
        db.session.commit()
        _invalidate_vocab_cache(category_id)            # ← [MỚI]
        flash(f"Đã xóa toàn bộ từ vựng trong chủ đề '{cat.name}'!", 'success')
    return redirect(url_for('admin'))


@app.route('/admin/add_vocabulary', methods=['POST'])
@require_admin
def add_vocabulary():
    try:
        category_id = int(request.form.get('category_id'))
        db.session.add(Vocabulary(
            word=request.form.get('word', '').strip(),
            pos=request.form.get('pos', '').strip(),
            pronunciation=request.form.get('pronunciation', '').strip(),
            meaning=request.form.get('meaning', '').strip(),
            example=request.form.get('example', '').strip(),
            category_id=category_id,
        ))
        db.session.commit()
        _invalidate_vocab_cache(category_id)            # ← [MỚI]
    except Exception as error:
        flash(f'Lỗi thêm từ vựng: {error}')
    return redirect(url_for('admin'))


@app.route('/admin/delete_vocabulary/<int:vocab_id>')
@require_admin
def delete_vocabulary(vocab_id):
    vocab = Vocabulary.query.get(vocab_id)
    if vocab:
        cid = vocab.category_id
        db.session.delete(vocab)
        db.session.commit()
        _invalidate_vocab_cache(cid)                    # ← [MỚI]
    return redirect(url_for('admin'))


@app.route('/admin/import_csv', methods=['POST'])
@require_admin
def import_csv_route():
    file = request.files.get('file')
    if not file or not file.filename:
        flash('Vui lòng chọn file!')
        return redirect(url_for('admin'))

    category_id = request.form.get('category_id')
    if not category_id:
        flash('Vui lòng chọn chủ đề để import!')
        return redirect(url_for('admin'))

    try:
        count = _import_vocab_from_file(
            file.stream.read(), int(category_id), file.filename,
        )
        flash(f'Thành công! Đã thêm {count} từ vựng.', 'success')
    except ValueError as e:
        flash(str(e))
    except Exception as e:
        flash(f'Lỗi import: {e}')

    return redirect(url_for('admin'))


@app.route('/admin/import_text', methods=['POST'])
@require_admin
def import_text_route():
    category_id = request.form.get('category_id')
    if not category_id:
        flash('Vui lòng chọn chủ đề để import!')
        return redirect(url_for('admin'))

    text = (request.form.get('text_data') or '').strip()
    if not text:
        flash('Vui lòng dán nội dung cần import!')
        return redirect(url_for('admin'))

    try:
        rows = _parse_plain_text(text)
        if not rows:
            raise ValueError('Không có dữ liệu để import.')
        count = _import_vocab_from_rows(rows, int(category_id))
        _invalidate_vocab_cache(int(category_id))       # ← [MỚI]
        flash(f'Thành công! Đã thêm {count} từ vựng.', 'success')
    except ValueError as e:
        flash(str(e))
    except Exception as e:
        flash(f'Lỗi import: {e}')

    return redirect(url_for('admin'))


@app.route('/admin/import_grammar', methods=['POST'])
@require_admin
def import_grammar_route():
    text = (request.form.get('grammar_text') or '').strip()
    if not text:
        flash('Vui lòng nhập nội dung ngữ pháp!')
        return redirect(url_for('admin_grammar'))

    try:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        count = 0
        objects = []
        
        # Lấy order hiện tại cao nhất
        max_order = db.session.query(db.func.max(GrammarTopic.sort_order)).scalar() or 0

        for line in lines:
            # Xử lý trường hợp có | ở đầu hoặc cuối
            parts = [p.strip() for p in line.split('|')]
            if parts and not parts[0]: parts.pop(0)
            if parts and not parts[-1]: parts.pop()
            
            # Bỏ qua dòng tiêu đề nếu có
            if not parts or parts[0] == '#' or 'chủ đề' in parts[0].lower() or '---' in parts[0]:
                continue
                
            if len(parts) >= 4:
                # Định dạng mới: # | Chủ đề | Công thức | Ví dụ | Lưu ý
                # parts[0] = #
                # parts[1] = Chủ đề (Title)
                # parts[2] = Công thức (Formula)
                # parts[3] = Ví dụ (Example)
                # parts[4] = Lưu ý (Description) - nếu có
                
                title = parts[1]
                formula = parts[2]
                example = parts[3]
                desc = parts[4] if len(parts) > 4 else f"Bài học về {title}"
                
                # Tạo nội dung HTML
                content_html = ""
                if formula:
                    content_html += f'<h3>Cấu trúc & Công thức</h3><div class="formula-box">{formula}</div>'
                if example:
                    content_html += f'<h3>Ví dụ minh họa</h3>'
                    for ex_line in example.split('\n'):
                        if ex_line.strip():
                            content_html += f'<div class="example-card"><i class="fa-solid fa-check-circle"></i><div>{ex_line.strip()}</div></div>'
                
                if len(parts) > 4 and parts[4]:
                    content_html += f'<h3>Lưu ý</h3><p style="color: var(--text-secondary); line-height: 1.6;">{parts[4]}</p>'
                
                max_order += 1
                objects.append(GrammarTopic(
                    title=title,
                    level='Core', # Mặc định
                    description=desc,
                    content=content_html,
                    sort_order=max_order
                ))
                count += 1
        
        if objects:
            db.session.bulk_save_objects(objects)
            db.session.commit()
            _invalidate_grammar_cache()
            flash(f'Thành công! Đã thêm {count} bài học ngữ pháp.', 'success')
        else:
            flash('Không tìm thấy dữ liệu hợp lệ (định dạng: | # | Chủ đề | Công thức | Ví dụ | Lưu ý |).')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi import: {e}')

    return redirect(url_for('admin_grammar'))


# ═══════════════════════════════════════════════════════════
#  VOCABULARY API  — có Cache + Pagination
# ═══════════════════════════════════════════════════════════

@app.route('/api/categories')
@cache.cached(timeout=300, key_prefix='categories_list')   # ← [MỚI] cache 5 phút
def api_get_categories():
    return jsonify([
        {'id': c.id, 'name': c.name, 'count': c.vocabularies.count()}  # .count() cho lazy=dynamic
        for c in Category.query.all()
    ])


@app.route('/api/vocabulary')
def api_get_vocabulary():
    cid = request.args.get('category_id', type=int)

    # ── [MỚI] Cache key phụ thuộc vào category + page + per_page
    cache_key = f"vocab_{'cat_' + str(cid) if cid else 'all'}_p{request.args.get('page',1)}_pp{request.args.get('per_page', app.config['PAGE_SIZE_DEFAULT'])}"
    cached    = cache.get(cache_key)
    if cached:
        return jsonify(cached)

    base_query = (
        Vocabulary.query.filter_by(category_id=cid) if cid
        else Vocabulary.query
    )

    # ── [MỚI] Search filter (tùy chọn): ?search=hello
    search = request.args.get('search', '').strip()
    if search:
        base_query = base_query.filter(
            db.or_(
                Vocabulary.word.ilike(f'%{search}%'),
                Vocabulary.meaning.ilike(f'%{search}%'),
            )
        )

    result = _paginate(base_query.order_by(Vocabulary.id))
    data   = {
        'data': [
            {
                'id': v.id, 'word': v.word, 'pos': v.pos,
                'pronunciation': v.pronunciation, 'meaning': v.meaning,
                'example': v.example, 'category_id': v.category_id,
            }
            for v in result['items']
        ],
        'meta': result['meta'],
    }

    cache.set(cache_key, data, timeout=300)               # ← [MỚI]
    return jsonify(data)


# ═══════════════════════════════════════════════════════════
#  QUESTIONS API  — có Cache + Pagination
# ═══════════════════════════════════════════════════════════

def _question_dict(q):
    return {
        'id': q.id, 'question_text': q.question_text,
        'option_a': q.option_a, 'option_b': q.option_b,
        'option_c': q.option_c, 'option_d': q.option_d,
        'correct_option': q.correct_option, 'explanation': q.explanation,
        'topic': q.topic, 'level': q.level,
    }


@app.route('/api/questions')
def api_get_questions():
    topic  = request.args.get('topic')
    level  = request.args.get('level')
    page   = request.args.get('page',     1)
    pp     = request.args.get('per_page', app.config['PAGE_SIZE_DEFAULT'])

    # ── [MỚI] Cache key gồm tất cả filter params
    cache_key = f'questions_t{topic or ""}_l{level or ""}_p{page}_pp{pp}'
    cached    = cache.get(cache_key)
    if cached:
        return jsonify(cached)

    query = Question.query
    if topic: query = query.filter_by(topic=topic)
    if level: query = query.filter_by(level=level)

    result = _paginate(query.order_by(Question.id))       # ← [MỚI] pagination
    data   = {
        'data': [_question_dict(q) for q in result['items']],
        'meta': result['meta'],
    }

    cache.set(cache_key, data, timeout=300)
    return jsonify(data)


@app.route('/api/questions', methods=['POST'])
@require_admin
def api_add_question():
    d = request.json
    q = Question(
        question_text=d.get('question_text', ''),
        option_a=d.get('option_a', ''), option_b=d.get('option_b', ''),
        option_c=d.get('option_c', ''), option_d=d.get('option_d', ''),
        correct_option=d.get('correct_option', ''),
        explanation=d.get('explanation', ''),
        topic=d.get('topic', ''), level=d.get('level', ''),
    )
    db.session.add(q)
    db.session.commit()
    _invalidate_question_cache()                          # ← [MỚI]
    return jsonify({'success': True, 'id': q.id})


@app.route('/api/questions/<int:qid>', methods=['PUT'])
@require_admin
def api_edit_question(qid):
    q = Question.query.get_or_404(qid)
    d = request.json
    for field in ('question_text', 'option_a', 'option_b', 'option_c',
                  'option_d', 'correct_option', 'explanation', 'topic', 'level'):
        if d.get(field) is not None:
            setattr(q, field, d[field])
    db.session.commit()
    _invalidate_question_cache()                          # ← [MỚI]
    return jsonify({'success': True})


@app.route('/api/questions/<int:qid>', methods=['DELETE'])
@require_admin
def api_delete_question(qid):
    q = Question.query.get_or_404(qid)
    db.session.delete(q)
    db.session.commit()
    _invalidate_question_cache()                          # ← [MỚI]
    return jsonify({'success': True})


@app.route('/api/questions/import', methods=['POST'])
@require_admin
def api_import_questions():
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': 'Không có file!'}), 400

    try:
        raw = file.read()
        if not raw or not raw.strip():
            return jsonify({'success': False, 'message': 'File trống!'}), 400

        fname = (file.filename or '').lower()

        if fname.endswith('.json'):
            text = _strip_bom(raw.decode('utf-8-sig'))
            data = json.loads(text)
        elif fname.endswith('.csv'):
            text = _decode_bytes(raw)
            if text is None:
                return jsonify({'success': False, 'message': 'Không thể đọc file.'}), 400
            data = list(csv.DictReader(io.StringIO(_strip_bom(text))))
        else:
            return jsonify({'success': False,
                            'message': 'Chỉ chấp nhận .json hoặc .csv'}), 400

        if not data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu trong file!'}), 400

        # ── [MỚI] Bulk insert cho questions
        objects = []
        for item in data:
            correct = (item.get('correct_option') or item.get('correct_answer') or '').strip().upper()
            objects.append(Question(
                question_text=str(item.get('question_text', '')).strip(),
                option_a=str(item.get('option_a', '')).strip(),
                option_b=str(item.get('option_b', '')).strip(),
                option_c=str(item.get('option_c', '')).strip(),
                option_d=str(item.get('option_d', '')).strip(),
                correct_option=correct,
                explanation=str(item.get('explanation', '')).strip(),
                topic=str(item.get('topic', '')).strip(),
                level=str(item.get('level', '')).strip(),
            ))

        db.session.bulk_save_objects(objects)             # ← [MỚI] bulk insert
        db.session.commit()
        _invalidate_question_cache()                      # ← [MỚI]
        return jsonify({'success': True, 'imported': len(objects)})

    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'message': f'JSON không hợp lệ: {e}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi import: {e}'}), 500


@app.route('/api/questions/export')
def api_export_questions():
    data = [_question_dict(q) for q in Question.query.all()]
    return app.response_class(
        response=json.dumps(data, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=questions.json'},
    )


@app.route('/api/questions/topics')
@cache.cached(timeout=600, key_prefix='question_topics')   # ← [MỚI] cache 10 phút
def api_get_topics():
    return jsonify([t[0] for t in db.session.query(Question.topic).distinct() if t[0]])


@app.route('/api/questions/levels')
@cache.cached(timeout=600, key_prefix='question_levels')   # ← [MỚI] cache 10 phút
def api_get_levels():
    return jsonify([l[0] for l in db.session.query(Question.level).distinct() if l[0]])


@app.route('/api/grammar')
@cache.cached(timeout=600, key_prefix='grammar_topics')
def api_get_grammar_topics():
    return jsonify([
        {
            'id': topic.id,
            'title': topic.title,
            'description': topic.description,
            'content': topic.content,
            'level': topic.level,
            'sort_order': topic.sort_order,
        }
        for topic in GrammarTopic.query.order_by(GrammarTopic.sort_order, GrammarTopic.id).all()
    ])


@app.route('/api/questions/preview', methods=['POST'])
def api_preview_question():
    d = request.json
    return jsonify({k: d.get(k, '') for k in (
        'question_text', 'option_a', 'option_b', 'option_c',
        'option_d', 'correct_option', 'explanation', 'topic', 'level',
    )})


@app.route('/api/questions/generate_ai', methods=['POST'])
def api_generate_ai_question():
    return jsonify({
        'question_text': 'Choose the correct answer.',
        'option_a': 'Option A', 'option_b': 'Option B',
        'option_c': 'Option C', 'option_d': 'Option D',
        'correct_option': 'A',
        'explanation': 'Đây là câu hỏi mẫu từ AI.',
        'topic': 'AI', 'level': 'Medium',
    })


# ─── Run ──────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
