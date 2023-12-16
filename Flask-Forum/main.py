from flask import redirect, url_for
from flask import Flask, render_template, redirect, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import bcrypt, Bcrypt
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin, AdminIndexView, expose

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///flask_auth.db"
db = SQLAlchemy(app)
app.secret_key = '12635675@^%@^&%7826'
bcrypt = Bcrypt(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, auto_increment=True)
    username = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False, default='user')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)


class Forum(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False, unique=True)
    description = db.Column(db.String, nullable=True)
    topics = db.relationship('Topic', backref='forum',
                             lazy=True, cascade='all, delete-orphan')


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=True)
    forum_id = db.Column(db.Integer, db.ForeignKey('forum.id'), nullable=False)
    posts = db.relationship('Post', backref='topic',
                            lazy=True, cascade='all, delete-orphan')


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='posts', lazy=True)


with app.app_context():
    db.create_all()


@app.route('/')
def home():
    users = User.query.all()

    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return render_template('home.html', users=users, current_user=current_user)
    else:
        return render_template('home.html', users=users)


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if len(username) >= 4 and len(password) >= 8:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return render_template('register.html', error="Username already exists")

            hashed_password = bcrypt.generate_password_hash(password)
            user = User(username=username, password=hashed_password)
            db.session.add(user)
            db.session.commit()

            session['user_id'] = user.id

            return redirect('/')

    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return render_template('register.html', current_user=current_user)
    else:
        return render_template('register.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        search_user = User.query.filter_by(username=username).first()

        if 'user_id' in session:
            return redirect('/profile')

        if search_user and search_user.check_password(password):
            session['user_id'] = search_user.id
            return redirect('/')

    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return render_template('login.html', current_user=current_user)
    else:
        return render_template('login.html')


@app.route('/profile')
def profile():
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return render_template('profile.html', current_user=current_user, )
    else:
        return redirect('/login')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        if current_user.role == 'admin':
            user_to_delete = User.query.get(user_id)
            if user_to_delete:
                Post.query.filter_by(user_id=user_to_delete.id).delete()
                db.session.delete(user_to_delete)
                db.session.commit()
    return redirect('/')


@app.route('/forums')
def forums():
    forums_list = Forum.query.all()
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return render_template('forums.html', current_user=current_user, forums_list=forums_list)
    else:
        return redirect('/login')


@app.route('/add_forum', methods=['GET', 'POST'])
def add_forum():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']

        forum = Forum(name=name, description=description)
        db.session.add(forum)
        db.session.commit()

        return redirect('forums')

    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return render_template('add_forum.html', current_user=current_user)
    else:
        return redirect('/login')


@app.route('/delete_forum/<int:forum_id>', methods=['POST'])
def delete_forum(forum_id):
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        if current_user.role == 'admin':
            forum_to_delete = Forum.query.get(forum_id)
            if forum_to_delete:
                db.session.delete(forum_to_delete)
                db.session.commit()
    return redirect('/forums')


@app.route('/topics/<int:forum_id>')
def topics(forum_id):
    forum = Forum.query.get(forum_id)
    topics_list = Topic.query.filter_by(forum_id=forum_id).all()
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return render_template('topics.html', current_user=current_user, forum=forum, topics_list=topics_list)
    else:
        return redirect('/login')


@app.route('/add_topic/<int:forum_id>', methods=['GET', 'POST'])
def add_topic(forum_id):
    forum = Forum.query.get(forum_id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        topic = Topic(title=title, content=content, forum_id=forum_id)
        db.session.add(topic)
        db.session.commit()

        return redirect(url_for('topics', forum_id=forum.id))

    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return render_template('add_topic.html', current_user=current_user, forum=forum)
    else:
        return redirect('/login')


@app.route('/delete_topic/<int:topic_id>', methods=['POST'])
def delete_topic(topic_id):
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        if current_user.role == 'admin':
            topic_to_delete = Topic.query.get(topic_id)
            if topic_to_delete:
                db.session.delete(topic_to_delete)
                db.session.commit()
    return redirect(url_for('topics', forum_id=topic_to_delete.forum_id))


@app.route('/discussion/<int:topic_id>')
def discussion(topic_id):
    topic = Topic.query.get(topic_id)
    posts_list = Post.query.filter_by(topic_id=topic_id).all()

    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return render_template('discussion.html', current_user=current_user, topic=topic, posts_list=posts_list)
    else:
        return redirect('/login')


@app.route('/add_post/<int:topic_id>', methods=['POST'])
def add_post(topic_id):
    topic = Topic.query.get(topic_id)

    if request.method == 'POST':
        content = request.form['content']

        post = Post(content=content, topic_id=topic_id,
                    user_id=session['user_id'])
        db.session.add(post)
        db.session.commit()

        return redirect(url_for('discussion', topic_id=topic.id))

    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return render_template('add_post.html', current_user=current_user, topic=topic)
    else:
        return redirect('/login')


@app.route('/delete_post/<int:post_id>/<int:topic_id>', methods=['POST'])
def delete_post(post_id, topic_id):
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        post_to_delete = Post.query.get(post_id)

        if current_user.role == 'admin' or current_user.id == post_to_delete.user_id:
            db.session.delete(post_to_delete)
            db.session.commit()

    return redirect(url_for('discussion', topic_id=topic_id))


class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        return self.render('admin/home.html')


admin = Admin(app, name='Admin Panel', template_mode='bootstrap4',
              index_view=MyAdminIndexView())


class UserAdmin(ModelView):
    column_list = ['id', 'username', 'role']

    def on_model_change(self, form, model, is_created):
        if 'password' in form.data:
            model.password = bcrypt.generate_password_hash(
                form.data['password']).decode('utf-8')


admin.add_view(UserAdmin(User, db.session))


class ForumAdmin(ModelView):
    column_list = ['id', 'name', 'description']


admin.add_view(ForumAdmin(Forum, db.session))


class TopicAdmin(ModelView):
    column_list = ['id', 'title', 'content', 'forum']

    def on_model_change(self, form, model, is_created):
        if model.forum_id is None:
            model.forum_id = 1


admin.add_view(TopicAdmin(Topic, db.session))


class PostAdmin(ModelView):
    column_list = ['id', 'content', 'topic', 'user']


admin.add_view(PostAdmin(Post, db.session))


@app.route('/admin')
def admin_panel():

    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        if current_user.role == 'admin':
            return redirect(url_for('admin.index'))
        else:
            return redirect('/')
    else:
        return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)
