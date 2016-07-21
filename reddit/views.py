#!venv/bin/python
from flask.ext.login import login_user, logout_user, current_user, login_required
from flask import request, render_template,redirect, url_for
from reddit import app, db, lm
from models import *
from datetime import datetime
from sqlalchemy import desc

@lm.user_loader
def load_user(id):
    return UserDB.query.get(int(id))

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        top_posts = PostDB.query.order_by(desc(PostDB.num_likes)).limit(50).all()
        if top_posts is None:
            return render_template('header.html')
        for x in top_posts:
            print vars(x)
        return render_template('header.html', posts=top_posts, TagDB=TagDB, PostTagDB=PostTagDB, front=True)
    if request.method == 'POST':
        
        return render_template('write.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        if request.form.get('login_or_signup') == 'signup': #signup
            user = UserDB.query.filter_by(email=email).first()
            if user is not None:
                return "email already exists.. pls no"
            user = UserDB.query.filter_by(username=username).first()
            if user is not None:
                return "username is already taken. pls die"
            user = UserDB(email=email, username=username, pass_hash=password)
            db.session.add(user)
            db.session.commit()
            login_user(user, True)
            print "user successfully added"
            return redirect(url_for('home'))

        else: #login
            user = UserDB.query.filter_by(username=username, pass_hash=password).first()
            if user is None:
                return "user doesnt exist"

            login_user(user, True)
            print "user successfully logged in"
            return redirect(url_for('home'))


@app.route('/tags/<tag_name>')
def tag(tag_name):
    tag = TagDB.query.filter_by(name=tag_name).first()
    if tag is None:
        return render_template('error.html')
    #get all items in PostTagDB that are of ___ tag
    post_tags = PostTagDB.query.filter_by(tag_id=tag.id).all()
    #get all post_ids of queried posts from above
    post_ids = map(lambda x: x.post_id, post_tags)
    #get all posts of the ids collected above
    posts = map(lambda x: PostDB.query.filter_by(id=x).all(), post_ids)
    posts = map(lambda x: x[0], posts)
    return render_template('tags.html', tag=tag_name, posts=posts)


@app.route('/write', methods=['GET', 'POST'])
def write():
    if request.method == 'GET':
        return render_template('write.html')
    if request.method == 'POST':
        # Get fields yo
        title = request.form.get('title')
        content = request.form.get('content')
        new_tag = request.form.get('tag')
        # Create and add post
        post = PostDB(title=title, author=current_user.username, content=content,num_likes=0, time=datetime.now())
        db.session.add(post)
        # Create and add tag
        tag = TagDB(name=new_tag)
        db.session.add(tag)
        db.session.commit()
        # Connect the post and the tag
        existing_tag = TagDB.query.filter_by(name=new_tag).first()
        if existing_tag is None:
            post_tag = PostTagDB(tag_id=tag.id, post_id=post.id)
        else:
            post_tag = PostTagDB(tag_id=existing_tag.id, post_id=post.id)

        db.session.add(post_tag)
        db.session.commit()
        return redirect(url_for('post', post_id=str(post.id)))


@app.route('/posts/<post_id>', methods=['GET', 'POST'])
def post(post_id):
    if request.method == 'GET':
        post = PostDB.query.filter_by(id=post_id).first()
        if post is None:
            return render_template('error.html')
        comments = CommentDB.query.filter_by(post_id=post_id).all()

        return render_template('post.html', post=post, comments=comments)
    if request.method == 'POST':
        #Adding to LikesDB
        selection = request.form.get('selection')
        content = request.form.get('content')
        if selection is not None and selection.startswith("post"):
            like_type=True
            if selection == 'post_dislike':
                like_type=False
            like = LikeDB.query.filter_by(username=current_user.username, post_id=post_id).first()
            if like is None:
                like = LikeDB(username=current_user.username, post_or_comment=1, post_id=post_id, like_type=like_type)
                db.session.add(like)
                db.session.commit()
            
            like.like_type = like_type
            db.session.add(like)
            db.session.commit()

            return redirect(url_for('post', post_id=post_id))
        # User wants to add a comment. Assume user is logged in
        if content is None and selection is None:
            return render_template('error.html')
        if content is not None:
            author = current_user.username
            time = datetime.now()
            comment = CommentDB(content=content, author=author, post_id=post_id, num_likes=0, time=time)
            db.session.add(comment)
            db.session.commit()

        if selection is not None:
            like_type=True
            if selection.startswith('comment_dislike'):
                like_type=False
            like = LikeDB.query.filter_by(username=current_user.username, comment_id=selection.split("_")[2]).first()
            if like is None:
                like = LikeDB(username=current_user.username, post_or_comment=0, comment_id=selection.split("_")[2], like_type=like_type)
                db.session.add(like)
                db.session.commit()
            
            like.like_type = like_type
            db.session.add(like)
            db.session.commit()

        return redirect(url_for('post', post_id=post_id))


@app.route('/users/<username>', methods=['GET', 'POST'])
def profile(username):
    if request.method == 'GET':
        user = UserDB.query.filter_by(username=username).first()
        if user is None:
            return render_template('profile.html')
        return render_template('profile.html')
        #return str("User is " + user.username + "\nMail is " + user.email + "\nPassword is" + user.pass_hash)
    if request.method == 'POST':
        selection = request.form['selection']

        if selection == 'posts':
            posts = PostDB.query.filter_by(author=username).all()
            if posts is None:
                return "No posts exist"
            return render_template('profile.html', posts=posts)

        if selection == 'comments':
            comments = CommentDB.query.filter_by(author=username).all()
            post_ids = map(lambda x: x.post_id, CommentDB.query.filter_by(author=username).all())
            posts = map(lambda x: PostDB.query.filter_by(id=x).all(), post_ids)
            for post in posts:
                print post[0].title
            return render_template('profile.html', comments=comments, posts=posts) #returns the list of all the comments that the current user has written

        if selection == 'likes':
            post_ids = map(lambda x: x.post_id, LikeDB.query.filter_by(username=username).all())
            print len(post_ids)
            if len(post_ids) is 0:
                return "No posts liked"
            posts = map(lambda x: PostDB.query.filter_by(id=x).all(), post_ids)
            return render_template('profile.html', posts=posts) #returns the list of all the posts that the current user has liked


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


