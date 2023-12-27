
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify,abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from flask_migrate import Migrate
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os
import uuid  
from flask import send_from_directory
import plotly.express as px
import plotly.graph_objects as go
from plotly.io import to_html
import pandas as pd











# create the extension
db = SQLAlchemy()
# create the app
app = Flask(__name__)

base_dir = os.path.abspath(os.path.dirname(__file__))
countries_df = pd.read_csv(os.path.join(base_dir, 'static/csv/countries.csv'), usecols=['id', 'name'])
states_df = pd.read_csv(os.path.join(base_dir, 'static/csv/states.csv'), usecols=['id', 'name', 'country_id'])
cities_df = pd.read_csv(os.path.join(base_dir, 'static/csv/cities.csv'), usecols=['id', 'name', 'state_name'])
country_codes_df = pd.read_csv(os.path.join(base_dir, 'static/csv/country-codes.csv'), usecols=['Country', 'Code'])





app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"



upload_folder = os.path.join(app.root_path, 'static', 'profile pic')
app.config['UPLOAD_FOLDER'] = upload_folder     
app.static_folder = 'static'


UPLOAD_FOLDER = 'static/profile_pic'  # Folder to store uploaded profile pictures



UPLOAD_FILE_FOLDER = os.path.join(app.root_path, 'static', 'upload_file')
app.config['UPLOAD_FILE_FOLDER'] = UPLOAD_FILE_FOLDER
ALLOWED_FILE_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'ogg', 'mp4', 'avi', 'mkv', 'doc', 'docx'}


def allowed_file_upload(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FILE_EXTENSIONS
# Initialize the app with the extension
db.init_app(app)
migrate = Migrate(app, db)



class users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True,nullable=False)
    password = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user')
    uuid = db.Column(db.String(36), unique=True, nullable=False, server_default=str(uuid.uuid4()))
    profile_picture = db.Column(db.String(255), default='avatar.avif')
    status = db.Column(db.String(20), default='active')
    deactivated_at = db.Column(db.DateTime, default=None)

    def __repr__(self):
        return f"User(id={self.id}, username={self.username}, email={self.email}, role={self.role}, profile_picture={self.profile_picture})"


 


class Form(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    form_title = db.Column(db.String(100), nullable=False)
    form_description = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(255), nullable=False)
    uuid = db.Column(db.String(36), unique=True, nullable=False)
    form_link = db.Column(db.String(255))
    form_header = db.Column(db.String(255))
    created_by = db.Column(db.String(100))
    creator = db.Column(db.String(100))
    edited = db.Column(db.String(3), default='No')  
    edited_at = db.Column(db.DateTime) 
    questions = db.relationship('Question', backref='form', lazy=True, cascade='all, delete-orphan')
    responses = db.relationship('FormResponse', backref='form', lazy=True, cascade='all, delete-orphan')

    


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(255), nullable=False)
    question_type = db.Column(db.String(20), nullable=False)
    char_limit = db.Column(db.Integer)  
    mandatory = db.Column(db.String(10), default='non_mandatory', nullable=False)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id', ondelete='CASCADE'), nullable=False)
    options = db.relationship('Option', backref='question', lazy=True, cascade='all, delete-orphan')




class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    option_text = db.Column(db.String(255), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    file_type = db.Column(db.String(50)) 
    max_file_size = db.Column(db.Integer)

    

class FormResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id', ondelete='CASCADE'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.relationship('ResponseAnswer', backref='form_response', lazy=True, cascade='all, delete-orphan')

class ResponseAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    response_id = db.Column(db.Integer, db.ForeignKey('form_response.id', ondelete='CASCADE'), nullable=False)
    answer = db.Column(db.String(255))
    file_path = db.Column(db.String(255))
    question = db.relationship('Question', backref='response_answers')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()

app.secret_key = 'secret_key'


@app.route('/')
def home():
    user=get_current_user
    return render_template('index.html',user=user)


@app.route('/form_responses/<int:form_id>', methods=['GET'])
def form_responses(form_id):
    form = Form.query.get_or_404(form_id)
    responses = FormResponse.query.filter_by(form_id=form_id).all()
    return render_template('form_responses.html', form=form, responses=responses)



@app.route('/response_details/<int:response_id>', methods=['GET'])
def response_details(response_id):
    response = FormResponse.query.get_or_404(response_id)

    # Fetch data using a join between ResponseAnswer and Question
    questions_and_answers = (
        db.session.query(ResponseAnswer, Question.question_text, Question.question_type)
        .join(Question, ResponseAnswer.question_id == Question.id)
        .filter(ResponseAnswer.response_id == response.id)
        .all()
    )

    return render_template('response_details.html', response=response, questions_and_answers=questions_and_answers)




def get_option_text(response, question):
    if question.question_type in ['multiple_choice', 'dropdown', 'checkboxes']:
        option = Option.query.get(response)
        if option:
            return option.option_text
    return response




@app.route('/view_pie_chart/<int:form_id>/<string:question_type>', methods=['GET'])
def view_pie_chart(form_id, question_type):
    form = Form.query.get_or_404(form_id)

    # Fetch questions of the specified question type
    questions = Question.query.filter(Question.form_id == form_id, Question.question_type == question_type).all()

    # Check if there is a "gender" question in the form
    gender_question = next((q for q in form.questions if q.question_type == 'gender'), None)

    # Prepare data for the pie chart
    labels = []
    values = []

    for question in questions:
        options = Option.query.filter_by(question_id=question.id).all()
        for option in options:
            option_text = get_option_text(option.id, question)
            # Add a check for non-empty option text before appending to labels
            if option_text:
                labels.append(option_text)
                values.append(0)  # Initialize values to 0 for each option

    # Count occurrences of each option in responses
    total_responses = len(form.responses)
    for response in form.responses:
        for answer in response.answers:
            if answer.question_id in [q.id for q in questions]:
                # Check if answer is a comma-separated list for checkboxes
                if ',' in answer.answer:
                    option_ids = [int(option_id) for option_id in answer.answer.split(',')]
                    for option in options:
                        if option.id in option_ids:
                            option_text = get_option_text(option.id, question)
                            # Add a check for non-empty option text before incrementing values
                            if option_text:
                                values[labels.index(option_text)] += 1
                else:
                    # Single option answer
                    option_text = get_option_text(answer.answer, question)
                    # Add a check for non-empty option text before incrementing values
                    if option_text:
                        values[labels.index(option_text)] += 1

    # Calculate percentages
    percentages = [(value / total_responses) * 100 if total_responses > 0 else 0 for value in values]

    # Create pie chart using Plotly
    fig = px.pie(names=labels, values=values, title=f'Responses for {question_type.capitalize()} Questions')

    # Update the hover text to include percentages
    hover_info = [f'{label}: {value} ({percentage:.2f}%)' for label, value, percentage in zip(labels, values, percentages)]
    fig.update_traces(textinfo='percent+label', hoverinfo='text', text=hover_info)

    # Convert the Plotly figure to HTML
    plot_html = to_html(fig, full_html=False)

    # Check if there is a "gender" question in the form
    show_gender_filter = False
    gender_chart_html = ''
    gender_options = []

    if gender_question:
        show_gender_filter = True

        # Retrieve gender responses from the database
        gender_responses = []
        for response in form.responses:
            answer = ResponseAnswer.query.filter_by(response_id=response.id, question_id=gender_question.id).first()
            if answer:
                gender_responses.append(answer.answer)

        # Create a dictionary to count gender responses
        gender_counts = {
            'Male': gender_responses.count('Male'),
            'Female': gender_responses.count('Female'),
            'Rather Not Say': gender_responses.count('Rather Not Say')
        }

        # Create a Plotly pie chart for gender distribution
        gender_fig = px.pie(
            values=list(gender_counts.values()),
            names=list(gender_counts.keys()),
            title=f'Gender Distribution for Form {form_id}'
        )

        # Convert the Plotly figure to HTML
        gender_chart_html = to_html(gender_fig, full_html=False)

        # Get the options for the gender filter
        gender_options = list(gender_counts.keys())

    return render_template(
        'view_pie_chart.html',
        plot_html=plot_html,
        form=form,
        show_gender_filter=show_gender_filter,
        gender_chart_html=gender_chart_html,
        gender_options=gender_options
    )
    
    



@app.route('/view_bar_chart/<int:form_id>/<string:question_type>', methods=['GET'])
def view_bar_chart(form_id, question_type):
    form = Form.query.get_or_404(form_id)

    # Fetch questions of the specified question type
    questions = Question.query.filter(Question.form_id == form_id, Question.question_type == question_type).all()

    # Prepare data for the bar chart
    labels = []
    values = []

    for question in questions:
        options = Option.query.filter_by(question_id=question.id).all()
        for option in options:
            option_text = get_option_text(option.id, question)
            # Add a check for non-empty option text before appending to labels
            if option_text:
                labels.append(option_text)
                values.append(0)  # Initialize values to 0 for each option

    # Count occurrences of each option in responses
    total_responses = len(form.responses)
    for response in form.responses:
        for answer in response.answers:
            if answer.question_id in [q.id for q in questions]:
                # Check if answer is a comma-separated list for checkboxes
                if ',' in answer.answer:
                    # Handle multiple options
                    option_ids = [int(option_id) for option_id in answer.answer.split(',')]
                    for option in options:
                        if option.id in option_ids:
                            option_text = get_option_text(option.id, question)
                            # Add a check for non-empty option text before incrementing values
                            if option_text:
                                values[labels.index(option_text)] += 1
                else:
                    # Single option answer
                    option_text = get_option_text(answer.answer, question)
                    # Add a check for non-empty option text before incrementing values
                    if option_text:
                        values[labels.index(option_text)] += 1

    # Create a bar chart using Plotly
    fig = go.Figure(data=[go.Bar(x=labels, y=values)])
    fig.update_layout(
        title=f'Responses for {question_type.capitalize()} Questions',
        xaxis_title='Options',
        yaxis_title='Frequency',
    )

    # Convert the Plotly figure to HTML
    bar_chart_html = fig.to_html(full_html=False)

    return render_template(
        'view_bar_chart.html',
        bar_chart_html=bar_chart_html,
        form=form
    )






    




@app.route('/fill_form/<int:form_id>', methods=['GET', 'POST'])
def fill_form(form_id):
    # Retrieve the form based on the form_id
    form = Form.query.get_or_404(form_id)
    countries = countries_df.to_dict(orient='records')
    states = states_df.to_dict(orient='records')
    cities = cities_df.to_dict(orient='records')
    country_codes_df = pd.read_csv(os.path.join(base_dir, 'static/csv/country-codes.csv'), usecols=['Country', 'Code'])
    country_codes = country_codes_df.to_dict(orient='records')

    form_response = FormResponse(form_id=form.id)  # Initialize form_response here

    if request.method == 'POST':
        # Handle form submission
        answers = {}  # Store user's answers here, where keys are question IDs
        if not os.path.exists(app.config['UPLOAD_FILE_FOLDER']):
            os.makedirs(app.config['UPLOAD_FILE_FOLDER'])
        for question in form.questions:
            field_name = f'question_{question.id}'

            if question.question_type == 'file_upload':
                file = request.files.get(field_name)

                if file and allowed_file_upload(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FILE_FOLDER'], filename)
                    file.save(file_path)
                    

                    file_path = filename  # Store only the filename, not the entire path

    # Create a ResponseAnswer instance with file_path
                    response_answer = ResponseAnswer(question_id=question.id, file_path=file_path)
                    form_response.answers.append(response_answer)
                else:
                    flash('Invalid file format. Allowed formats are: txt, pdf, png, jpg, jpeg, gif', 'danger')
                    return redirect(url_for('fill_form', form_id=form_id))
            elif question.question_type == 'multiple_choice':
                # Handle multiple-choice questions
                selected_option_id = request.form.get(field_name)
                answers[question.id] = selected_option_id
            elif question.question_type == 'checkboxes':
                # Handle checkbox questions with multiple options
                selected_option_ids = request.form.getlist(field_name)
                # Store selected option IDs as a comma-separated string
                answers[question.id] = ','.join(selected_option_ids)
            elif question.question_type == 'dropdown':
                # Handle dropdown questions
                selected_option_id = request.form.get(field_name)
                answers[question.id] = selected_option_id
            elif question.question_type in ['short_answer', 'paragraph', 'text']:
                # Handle text-based input questions
                answer_text = request.form.get(field_name)
                answers[question.id] = answer_text
            elif question.question_type == 'gender':
                # Handle gender dropdown questions
                selected_gender = request.form.get(f'question_{question.id}')
                answers[question.id] = selected_gender
            elif question.question_type == 'email':
                # Handle email input questions
                email_value = request.form.get(f'question_{question.id}')
                answers[question.id] = email_value
            elif question.question_type == 'tel':
        # Handle telephone input questions
                selected_country_code = request.form.get('country_code')
                phone_number = request.form.get('phone')
    
                if selected_country_code and phone_number:
                   full_phone_number = f'{phone_number}'
                   answers[question.id] = full_phone_number
                else:
                   answers[question.id] = None
            elif question.question_type == 'cnic':
                # Handle CNIC input questions
                cnic_value = request.form.get(f'question_{question.id}')
                answers[question.id] = cnic_value
            elif question.question_type == 'rating':
                # Handle rating questions
                rating_value = request.form.get(field_name)
                answers[question.id] = rating_value
            elif question.question_type in ['date', 'time']:
                # Handle date and time questions
                date_time_value = request.form.get(field_name)
                answers[question.id] = date_time_value
            # Inside the loop where you handle different question types
            elif question.question_type == 'address':
            # Handle address input questions
                country_id = request.form.get('country')
                selected_country = next((country['name'] for country in countries if country['id'] == int(country_id)), None)
                country = selected_country if selected_country is not None else ''

                state = request.form.get('state')
                city = request.form.get('city')
                postal_code = request.form.get('postal_code')

    # Check if city, state, and postal code are None or empty, and replace them with 'null'
                city = city if city else 'null'
                state = state if state else 'null'
                postal_code = postal_code if postal_code else 'null'

    # Concatenate address components with labels
                address_string = f'Country: {country}, State: {state}, City: {city}, Postal Code: {postal_code}' \
                     if country or state or city or postal_code else None

    # Store the address string in the answer field
                answers[question.id] = address_string

        # Iterate through the user's answers and create ResponseAnswer instances
        for question_id, answer in answers.items():
            if question_id not in form_response.answers:
                if isinstance(answer, str):
                    response_answer = ResponseAnswer(question_id=question_id, answer=answer)
                elif isinstance(answer, int):  # Assuming IDs are integers
                    response_answer = ResponseAnswer(question_id=question_id, option_id=answer)
                else:
                    response_answer = ResponseAnswer(question_id=question_id, file_path=answer)
                form_response.answers.append(response_answer)

        # Add and commit the form response and answers to the database
        try:
    # Add and commit the form response and answers to the database
         db.session.add(form_response)
         db.session.commit()

         flash('Form submitted successfully!', 'success')

        except Exception as e:
    # Rollback changes in case of an error
         db.session.rollback()
         flash('Error submitting the form. Please try again.', 'danger')

        # Render the same template with the success message
        return render_template('fill_form.html', form=form, success_message='Form submitted successfully!', show_submit_another=True,
                               countries=countries,
                               states=states,
                               cities=cities,
                               country_codes=country_codes)

    return render_template('fill_form.html', form=form, show_submit_another=False, countries=countries, states=states,country_codes=country_codes, cities=cities)

@app.route('/country_codes')
def get_country_codes():
    # Read the country-codes.csv file
    country_codes_df = pd.read_csv(os.path.join(base_dir, 'static/csv/country-codes.csv'), usecols=['Country', 'Code'])

    # Convert the DataFrame to a list of dictionaries
    country_codes_list = country_codes_df.to_dict(orient='records')

    # Return the list of country codes as JSON
    return jsonify({'country_codes': country_codes_list})


@app.route('/profile_redirect')
def profile_redirect():
    user = get_current_user()
    if user:
        # User is logged in, redirect to their profile
        return redirect(url_for('profile', uuid=user.uuid))
    else:
        # User is not logged in, redirect to login page
        return redirect(url_for('login'))

def get_current_user():
    if 'user_id' in session:
        user_id = session['user_id']
        user = users.query.get(user_id)  # Assuming you have a User model with an 'id' field

        if user:
            return user
    return None
    


@app.route('/view_responses/<int:form_id>', methods=['GET'])
def view_responses(form_id):
    # Retrieve the form based on the form_id
    form = Form.query.get_or_404(form_id)

    # Get all responses for the given form
    responses = FormResponse.query.filter_by(form_id=form_id).all()

    # Create a dictionary to store responses for each question
    question_responses = {}

    # Define the get_option_text function to fetch option_text based on response
    def get_option_text(response, question):
        if question.question_type in ['multiple_choice', 'dropdown', 'checkboxes']:
            option = Option.query.get(response)
            if option:
                return option.option_text
        return response

    # Iterate through the questions associated with the form
    for question in form.questions:
        question_responses[question] = []

    # Iterate through the responses and their answers
    for response in responses:
        for answer in response.answers:
            question = Question.query.get(answer.question_id)
            question_responses[question].append(answer)  # Store the raw answers

    return render_template('view_responses.html', form=form, question_responses=question_responses, get_option_text=get_option_text)



@app.route('/download_file/<filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FILE_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)  # or return a custom error page
    except Exception as e:
        # Log the exception and return an appropriate error response
        print(f"Error during file download: {e}")
        abort(500)  # or return a custom error page







# Modify your Flask route to include the response count for each form
@app.route('/analytics', methods=['GET', 'POST'])
def analytics():
    # Get the current user
    current_user = get_current_user()

    if current_user is None:
        return redirect(url_for('login'))  # Redirect to the login page if the user is not logged in

    # Get all forms created by the currently logged-in user
    user_forms = Form.query.filter_by(uuid=current_user.uuid).all()

    # Calculate the response count for each form
    for user_form in user_forms:
        user_form.response_count = FormResponse.query.filter_by(form_id=user_form.id).count()

    form = None
    form_fill_count = None

    if request.method == 'POST':
        # Handle form submission to view analytics for a specific form
        selected_form_id = request.form.get('selected_form')
        if selected_form_id is not None:
            # Redirect to the analytics page for the selected form
            return redirect(url_for('analytics', form_id=selected_form_id))

    # Check if the URL contains a form_id parameter (indicating a specific form's analytics)
    form_id = request.args.get('form_id')

    # If no form_id is provided, load analytics for the first form by default
    if not form_id and user_forms:
        form_id = user_forms[0].id

    if form_id:
        # Get the form for which you want to display analytics
        form = Form.query.get_or_404(form_id)

        # Ensure that the form belongs to the current user
        if form.username != current_user.username:
            return "Unauthorized"  

        # Count the number of times the form has been filled out
        form_fill_count = FormResponse.query.filter_by(form_id=form_id).count()

        # You can add more analytics here based on your requirements

    return render_template('analytics.html', user_forms=user_forms, form=form, form_fill_count=form_fill_count, form_id=form_id)



@app.route('/gender_pie_chart/<int:form_id>')
def gender_pie_chart(form_id):
    current_user = get_current_user()

    if current_user is None:
        return redirect(url_for('login'))  # Redirect to the login page if the user is not logged in
    
    # Check if the form contains a "gender" question
    form = Form.query.get_or_404(form_id)
    gender_question = next((q for q in form.questions if q.question_type == 'gender'), None)

    if gender_question:
        # Query the database to get real data for the "gender" question
        gender_responses = []
        form_responses = FormResponse.query.filter_by(form_id=form_id).all()
        for response in form_responses:
            answer = ResponseAnswer.query.filter_by(
                response_id=response.id, question_id=gender_question.id).first()
            if answer:
                gender_responses.append(answer.answer)

        # Create a dictionary to count gender responses
        gender_counts = {
            'Male': gender_responses.count('Male'),
            'Female': gender_responses.count('Female'),
            'Rather Not Say': gender_responses.count('Rather Not Say')
        }

        # Create a Plotly pie chart
        fig = px.pie(
            values=list(gender_counts.values()),
            names=list(gender_counts.keys()),
            title=f'Gender Distribution for Form {form_id}'
        )

        # Convert the Plotly figure to HTML
        chart_html = fig.to_html()
    else:
        chart_html = 'No data available for gender question.'

    return render_template('gender_pie_chart.html', chart_html=chart_html)





@app.route('/address_pie_chart/<int:form_id>')
def address_pie_chart(form_id):
    current_user = get_current_user()

    if current_user is None:
        return redirect(url_for('login'))

    # Check if the form contains an "address" question
    form = Form.query.get_or_404(form_id)
    address_question = next((q for q in form.questions if q.question_type == 'address'), None)

    chart_type = request.args.get('chart_type', 'country')  # Initialize chart_type with a default value

    if address_question:
        # Query the database to get real data for the "address" question
        address_responses = []
        form_responses = FormResponse.query.filter_by(form_id=form_id).all()
        for response in form_responses:
            answer = ResponseAnswer.query.filter_by(
                response_id=response.id, question_id=address_question.id).first()
            if answer and answer.answer:  # Check if answer is not None and not an empty string
                address_responses.append(answer.answer)

        # Create a Plotly pie chart based on the selected chart type
        if chart_type == 'country':
            chart_data = []
            for response in address_responses:
                if response:
                    parts = response.split(', ')
                    if len(parts) >= 1:
                        country_info = parts[0].split(': ')
                        if len(country_info) == 2:
                            country = country_info[1]
                            chart_data.append(country)
            title = 'Country Distribution'
        elif chart_type == 'state':
            chart_data = []
            for response in address_responses:
                if response:
                    parts = response.split(', ')
                    if len(parts) >= 2:
                        state_info = parts[1].split(': ')
                        if len(state_info) == 2:
                            state = state_info[1]
                            chart_data.append(state)
            title = 'State Distribution'
        elif chart_type == 'city':
            chart_data = []
            for response in address_responses:
                if response:
                    parts = response.split(', ')
                    if len(parts) >= 3:
                        city_info = parts[2].split(': ')
                        if len(city_info) == 2:
                            city = city_info[1]
                            chart_data.append(city)
            title = 'City Distribution'
        else:
            chart_html = 'Invalid chart type.'
            return render_template('address_pie_chart.html', chart_html=chart_html, chart_type=chart_type, form=form)

        # Create a Plotly pie chart
        fig = px.pie(
            values=[chart_data.count(value) for value in set(chart_data)],
            names=list(set(chart_data)),
            title=title
        )

        # Convert the Plotly figure to HTML
        chart_html = fig.to_html()
    else:
        chart_html = 'No data available for address question.'

    # Pass 'form' along with other variables to the template
    return render_template('address_pie_chart.html', chart_html=chart_html, chart_type=chart_type, form=form)





@app.route('/recent_forms_activity/<int:form_id>')
def recent_forms_activity(form_id):
    # Your route logic here, using the form_id parameter

    # Get the current user
    current_user = get_current_user()

    if current_user is None:
        return redirect(url_for('login'))  # Redirect to the login page if the user is not logged in

    # Calculate the date range for the last 10 days
    today = datetime.utcnow().date()
    date_range = [(today - timedelta(days=i)) for i in range(10)]

    # Query the database to get the number of times the specific form has been filled out for each of the last 10 days
    form_counts = []
    for date in date_range:
        count = FormResponse.query.filter(FormResponse.form_id == form_id, FormResponse.submitted_at >= date, FormResponse.submitted_at < date + timedelta(days=1)).count()
        form_counts.append(count)

    # Create a DataFrame to store the data
    df = pd.DataFrame({'Date': date_range, 'Forms Filled': form_counts})

    # Create a Plotly bar chart
    fig = px.bar(df, x='Date', y='Forms Filled', title=f'Forms Filled for Form {form_id} in the Last 10 Days')

    # You can customize the appearance of the chart if needed

    return fig.to_html()






def generate_form_link(form_id):
    return f"http://127.0.0.1:5000/fill_form/{form_id}"










@app.route('/admin_users')
def admin_users():
    user = get_current_user()
    if user is None:
        return redirect(url_for('login'))

    # Check if the user has the 'admin' role
    if user.role != 'admin':
        flash('You do not have permission to access the admin dashboard.', 'error')
        return redirect(url_for('login'))  # Redirect to a different page if not an admin
    # Fetch and display the list of users from the database
   
    users_list = users.query.all()
    return render_template('admin_users.html', users_list=users_list)





@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = users.query.get_or_404(user_id)

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        role = request.form['role']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password == confirm_password:
            user.username = username
            user.email = email
            user.role = role

            # Check if a new password was provided and update it
            if password:
                user.password = password  

            db.session.commit()

            flash('User details updated successfully.', 'success')
            return redirect(url_for('admin_users'))
        else:
            flash('Password and confirm password do not match.', 'error')

    return render_template('edit_user.html', user=user)


@app.route('/deactivate_user/<int:user_id>', methods=['GET', 'POST'])
def deactivate_user(user_id):
     # Check if the user is logged in
    user = get_current_user()
    if user is None:
        return redirect(url_for('login'))

    # Check if the user has the 'admin' role
    if user.role != 'admin':
        flash('You do not have permission to access the admin dashboard.', 'error')
        return redirect(url_for('login'))  # Redirect to a different page if not an admin
    # Retrieve the user with the given user_id from the database
    user = users.query.get_or_404(user_id)

    if request.method == 'POST':
        # Check the user's status and toggle it
        if user.status == 'active':
            user.status = 'deactive'
            user.deactivated_at = datetime.now()  # Save the deactivation time
            flash('User account deactivated successfully.', 'success')
        else:
            user.status = 'active'
            flash('User account activated successfully.', 'success')

        db.session.commit()

        # Redirect back to the user management page
        return redirect(url_for('deactivate_user', user_id=user.id))
    # Calculate the time difference
    time_difference = datetime.now() - user.deactivated_at if user.deactivated_at else None

    # Pass the current time to the template
    current_time = datetime.now()

    return render_template('deactivate_user.html', user=user, time_difference=time_difference, current_time=current_time)



@app.route('/admin/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    # Retrieve the user with the given user_id from the database
    user = users.query.get_or_404(user_id)

    if request.method == 'POST':
        # Update user details and role based on form submission
        username = request.form['username']
        email = request.form['email']
        role = request.form['role']

        # Update the user's details and role in the database
        user.username = username
        user.email = email
        user.role = role
        db.session.commit()

        flash('User details updated successfully.', 'success')

        # Redirect back to the user management page
        return redirect(url_for('manage_users'))

    return render_template('edit_user.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    username_message = None
    email_message = None
    password_message = None
    registration_message = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        # Check if username or email already exists
        existing_user = users.query.filter_by(username=username).first()
        existing_email = users.query.filter_by(email=email).first()

        if existing_user:
            username_message = 'Username already taken. Please choose a different username.'
        elif existing_email:
            email_message = 'Email already in use. Please use a different email address.'
       
        else:
            # Add the new user to the database with the default 'user' role
            new_user = users(username=username, password=password, email=email, role='user', uuid=str(uuid.uuid4()))
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful. You can now log in.', 'success')
            # Set a success message in the session for the login page
            session['registration_success'] = 'Registration successful. You can now log in.'
            # Redirect to the login page
            return redirect(url_for('login'))

    return render_template('register.html', username_message=username_message, email_message=email_message, password_message=password_message, registration_message=registration_message)




@app.route('/login', methods=['GET', 'POST'])
def login():
    deactivation_message = request.args.get('deactivation_message')
    success_message = session.pop('registration_success', None)
    invalid_credentials_message = None  # New message for invalid email/username or password

    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']

        user = users.query.filter(or_(users.username == identifier, users.email == identifier)).first()

        if user:
            if user.status == 'deactive':
                deactivation_time = user.deactivated_at.strftime('%Y-%m-%d %I:%M %p')
                deactivation_message = f'Your account is deactivated. Time was {deactivation_time}.'
                return redirect(url_for('login', deactivation_message=deactivation_message))
            else:
                if user.password == password:
                    session['user_id'] = user.id
                    session['username'] = user.username
                    success_message = 'Login successful.'
                    flash(success_message, 'success')

                    if user.role == 'admin':
                        session['role'] = 'admin'
                        return redirect(url_for('admin_dashboard'))
                    else:
                        return redirect(url_for('profile',  uuid=user.uuid, success_message=success_message))
                else:
                    invalid_credentials_message = 'Invalid email/username or password. Please try again.'
        else:
            invalid_credentials_message = 'Invalid email/username or password. Please try again.'

    return render_template('login.html', deactivation_message=deactivation_message,
                           registration_success_message=success_message,
                           invalid_credentials_message=invalid_credentials_message)






    




@app.route('/uploads/<filename>')
def get_uploaded_image(filename):
    
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    





@app.route('/admin_dashboard')
def admin_dashboard():
    # Your admin dashboard logic here
    return render_template('admin_dashboard.html')










@app.route('/profile/<uuid>')
def profile(uuid):
    success_message = request.args.get('success_message')
    
    # Retrieve the user based on the provided username
    current_user = users.query.filter_by(uuid=uuid).first()

    if current_user:
        # Check if the user has a profile picture
        if current_user.profile_picture:
            profile_picture_url = url_for('get_uploaded_image', filename=current_user.profile_picture)
        else:
            # Use the default avatar image URL when there's no profile picture
            profile_picture_url = url_for('static', filename='images/avatar.avif')

        return render_template('profile.html', user=current_user, profile_picture_url=profile_picture_url, success_message=success_message)

    else:
        flash('User not found.', 'error')
        return redirect(url_for('login'))




@app.route('/edit_form/<int:form_id>', methods=['GET', 'POST'])
def edit_form(form_id):
    # Get the currently logged-in user
    current_user = get_current_user()

    if current_user is None:
        return redirect(url_for('login'))  # Redirect to the login page if the user is not logged in

    # Load the existing form to edit
    form = Form.query.get(form_id)

    if form is None:
        # Handle the case where the form doesn't exist
        return render_template('error.html', message='Form not found.')

    if form.username != current_user.username:
        # Handle the case where the user is not the owner of the form
        return render_template('error.html', message='You do not have permission to edit this form.')

    if request.method == 'POST':
        # Handle form submission to update the form and questions
        form_title = request.form['form_title']
        creator = request.form['creator']
        form_description = request.form['form_description']
        category = request.form['category']
        form_header = request.form['form_header']

        # Update the form's attributes
        form.form_title = form_title
        form.creator = creator
        form.form_description = form_description
        form.category = category
        form.form_header = form_header
        
        # Set 'edited' to 'Yes' and update 'edited_at'
        form.edited = 'Yes'
        form.edited_at = datetime.utcnow()

        # Handle updating or deleting existing questions and their options
        existing_question_ids = [q.id for q in form.questions]
        updated_question_ids = []

        for question in form.questions:
            question_id = question.id
            question_text = request.form.get(f'question_text_{question_id}')
            question_type = request.form.get(f'question_type_{question_id}')
            mandatory = request.form.get(f'mandatory_{question_id}')
            char_limit = request.form.get(f'char_limit_{question_id}')

            # Check if the question is being deleted
            if question_id not in updated_question_ids and question_id not in existing_question_ids:
                db.session.delete(question)
            else:
                # Update the question's attributes
                question.question_text = question_text
                question.question_type = question_type
                question.mandatory = mandatory
                if question_type in ["short_answer", "paragraph"]:
                    question.char_limit = int(char_limit) if char_limit else None

                updated_question_ids.append(question_id)

            # Handle updating options for multiple-choice, dropdown, and checkboxes questions
            if question_type in ["multiple_choice", "dropdown", "checkboxes"]:
                existing_option_ids = [opt.id for opt in question.options]
                updated_option_ids = []

                # Process existing options
                for option in question.options:
                    option_id = option.id
                    option_text = request.form.get(f'option_text_{question_id}_{option_id}')
                    new_option_text = request.form.get(f'new_option_text_{question_id}_{option_id}')

                    # Check if the option is being deleted
                    if option_id not in updated_option_ids and option_id not in existing_option_ids:
                        db.session.delete(option)
                    else:
                        # Update the option's text
                        if new_option_text:
                            option_text = new_option_text
                        option.option_text = option_text
                        updated_option_ids.append(option_id)

                # Handle adding new options for this question
                options = request.form.getlist(f'new_option_text_{question_id}')
                for option_text in options:
                    if option_text:
                        option = Option(option_text=option_text, question_id=question.id)
                        db.session.add(option)

        # Handle adding new questions (Here we are adding the code to handle new questions)
        questions_data = request.form.getlist('questions[]')
        question_types = request.form.getlist('question_types[]')

        for i in range(len(questions_data)):
            question_data = questions_data[i]
            question_type = question_types[i]
            question = Question(question_text=question_data,
                                question_type=question_type, form_id=form.id)

            # Add character limit for Short Answer and Paragraph questions
            if question_type in ["short_answer", "paragraph"]:
                char_limit_key = f'char_limit_{i + 1}'
                char_limit = request.form.get(char_limit_key)
                if char_limit:
                    question.char_limit = int(char_limit)

            db.session.add(question)
            db.session.flush()  # Ensure the question gets an ID immediately

            if question_type in ["multiple_choice", "dropdown", "checkboxes"]:
                options_data = request.form.getlist(f'options_{i + 1}[]')
                for option_text in options_data:
                    option = Option(option_text=option_text,
                                    question_id=question.id)
                    db.session.add(option)

        db.session.commit()

     

    return render_template('edit_form.html',form=form, user_role=current_user.role, user=current_user)











@app.route('/remove_question/<int:form_id>/<int:question_id>', methods=['DELETE'])
def remove_question(form_id, question_id):
    # Step 1: Retrieve the form and question objects
    form = Form.query.get(form_id)
    question = Question.query.get(question_id)

    # Step 2: Check if the form and question exist
    if not form or not question:
        return jsonify({"message": "Form or question not found."}), 404

    # Step 3: Verify user permissions (assuming you have a user object available)
    current_user = get_current_user()  # Use your authentication method
    if not current_user or current_user.username != form.username:
        return jsonify({"message": "Permission denied."}), 403

    # Step 4: Remove the question and commit changes
    db.session.delete(question)
    db.session.commit()

    flash('Question removed successfully', 'success')
    return jsonify({"message": "Question removed successfully."}), 200




@app.route('/remove_option/<int:form_id>/<int:question_id>/<int:option_id>', methods=['DELETE'])
def remove_option(form_id, question_id, option_id):
    # Step 2: Retrieve the form, question, and option objects
    form = Form.query.get(form_id)
    question = Question.query.get(question_id)
    option = Option.query.get(option_id)

    # Step 3: Check if the form, question, and option exist
    if not form or not question or not option:
        return jsonify({"message": "Form, question, or option not found."}), 404

    # Step 4: Verify user permissions (assuming you have a user object available)
    current_user = get_current_user()  # Use your authentication method
    if not current_user or current_user.username != form.username:
        return flash('Permission denied.', 'success')
    

    # Step 5: Remove the option from the question and commit changes
    question.options.remove(option)
    db.session.delete(option)
    db.session.commit()

    flash('Option removed successfully', 'success')
    return jsonify({"message": "Option removed successfully."}), 200










@app.route('/create_form', methods=['GET', 'POST'])
def create_form():
    # Get the currently logged-in user
    current_user = get_current_user()

    if current_user is None:
        return redirect(url_for('login'))  # Redirect to the login page if the user is not logged in

    if request.method == 'POST':
        form_title = request.form['form_title']
        form_description = request.form['form_description']
        category = request.form['category']  # Get the selected category
        created_at = datetime.utcnow()
        form_header = request.form['form_header']  # Get the form_header value
        creator_username = request.form['creator']
        # Check if at least one question is marked as mandatory
        if not any('mandatory' in question for question in request.form.getlist('mandatory[]')):
    
            flash('At least one question must be marked as mandatory.', 'error')
            return redirect(url_for('create_form'))
        # Create a new Form associated with the current user
        form = Form(username=current_user.username, form_title=form_title,
                    form_description=form_description, category=category,
                    created_at=created_at, form_header=form_header,creator=creator_username,
            uuid=current_user.uuid)

        # Check the role of the current user and set "created_by" accordingly
        if current_user.role == "admin":
            form.created_by = "admin"
        elif current_user.role == "user":
            form.created_by = "user"

        db.session.add(form)
        db.session.flush()  # This ensures the form gets an ID immediately

        # Generate the form link and set it in the form
        form.form_link = generate_form_link(form.id)

        questions_data = request.form.getlist('questions[]')
        question_types = request.form.getlist('question_types[]')
        mandatory_values = request.form.getlist('mandatory[]')  # Get the list of mandatory values

        for i in range(len(questions_data)):
            question_data = questions_data[i]
            question_type = question_types[i]
            mandatory = mandatory_values[i]  # Get the mandatory value for the question

            question = Question(
                question_text=question_data,
                question_type=question_type,
                form_id=form.id,
                mandatory=mandatory  # Set the mandatory value for the question
            )

            # Add character limit for Short Answer and Paragraph questions
            if question_type in ["short_answer", "paragraph"]:
                char_limit_key = f'char_limit_{i + 1}'
                char_limit = request.form.get(char_limit_key)
                if char_limit:
                    question.char_limit = int(char_limit)

            db.session.add(question)
            db.session.flush()  # Ensure the question gets an ID immediately

            if question_type in ["multiple_choice", "dropdown", "checkboxes"]:
                options_data = request.form.getlist(f'options_{i + 1}[]')
                for option_text in options_data:
                    option = Option(option_text=option_text,
                                    question_id=question.id)
                    db.session.add(option)

            # Handle file upload options
            elif question_type == "file_upload":
                file_type_key = f'file_types_{i + 1}'
                max_file_size_key = f'max_file_size_{i + 1}'

                file_type = request.form.get(file_type_key)
                max_file_size = request.form.get(max_file_size_key)

                option = Option(
                    option_text="File Upload Option",  # You can customize this as needed
                    question_id=question.id,
                    file_type=file_type,
                    max_file_size=int(max_file_size) if max_file_size else None
                )

                db.session.add(option)

        db.session.commit()

        return redirect(url_for('preview_form', form_id=form.id))

    return render_template('create_form.html', user_role=current_user.role)










@app.route('/saved_forms', methods=['GET', 'POST'])
def saved_forms():
    # Get the currently logged-in user
    current_user = get_current_user()

    if current_user is None:
        return redirect(url_for('login'))  # Redirect to the login page if the user is not logged in

    if request.method == 'POST':
        # Retrieve the form_id from query parameters
        form_id = request.args.get('form_id')
        form_to_delete = Form.query.get(form_id)

        if form_to_delete:
            # Check if the form belongs to the current user before deleting
            if form_to_delete.uuid == current_user.uuid:
                db.session.delete(form_to_delete)
                db.session.commit()
                flash('Form deleted successfully', 'success')
            else:
                flash('You are not authorized to delete this form', 'error')
        else:
            flash('Form not found', 'error')

        # Redirect to the saved_forms page after deletion
        return redirect(url_for('saved_forms'))

    category_filter = request.args.get('category_filter')

    if category_filter:
        # Retrieve forms filtered by category and owned by the current user (who is a "user")
        saved_forms = Form.query.filter_by(
            category=category_filter, uuid=current_user.uuid, created_by="user").order_by(Form.id.desc()).all()
    else:
        # Retrieve all forms owned by the current user (who is a "user")
        saved_forms = Form.query.filter_by(
            uuid=current_user.uuid, created_by="user").order_by(Form.id.desc()).all()

    # Check if any of the forms are being edited5
    for form in saved_forms:
        if form.edited == 'Yes':
        # You may want to take some specific action or display an indicator for recently edited forms
           form.recently_edited = True
        else:
           form.recently_edited = False


    return render_template('saved_forms.html', user=current_user, saved_forms=saved_forms, category_filter=category_filter)


@app.route('/form_templates', methods=['GET', 'POST'])
def form_templates():
    # Get the currently logged-in user
    current_user = get_current_user()

    if current_user is None:
        return redirect(url_for('login'))  # Redirect to the login page if the user is not logged in

    if request.method == 'POST':
        # Retrieve the form_id from query parameters
        form_id = request.args.get('form_id')
        form_to_delete = Form.query.get(form_id)

        if form_to_delete:
            # Check if the form belongs to the current user before deleting
            if form_to_delete.username == current_user.username:
                db.session.delete(form_to_delete)
                db.session.commit()
                flash('Form deleted successfully', 'success')
            else:
                flash('You are not authorized to delete this form', 'error')
        else:
            flash('Form not found', 'error')

        # Redirect to the admin_saved_forms page after deletion
        return redirect(url_for('form_templates'))

    category_filter = request.args.get('category_filter')

    if category_filter:
        # Retrieve forms filtered by category and owned by the current user (who is an "admin")
        saved_forms = Form.query.filter_by(
            category=category_filter, created_by="admin").order_by(Form.id.desc()).all()
    else:
        # Retrieve all forms owned by the current user (who is an "admin")
        saved_forms = Form.query.filter_by(
            created_by="admin").order_by(Form.id.desc()).all()

    return render_template('form_templates.html', saved_forms=saved_forms, category_filter=category_filter, current_user=current_user)

@app.route('/copy_template/<int:template_id>', methods=['POST'])
def copy_template(template_id):
    current_user = get_current_user()

    if current_user is None:
        return redirect(url_for('login'))

    template_to_copy = Form.query.get(template_id)

    if template_to_copy is None or template_to_copy.created_by != 'admin':
        flash('Template not found or you are not authorized to copy this template.', 'error')
        return redirect(url_for('form_templates'))

    try:
        # Copy the template data to create a new form
        new_form = Form(
            form_title=template_to_copy.form_title,
            form_description=template_to_copy.form_description,
            category=template_to_copy.category,
            uuid=current_user.uuid,
            form_header=template_to_copy.form_header,
            username=current_user.username,
            created_at=datetime.utcnow(),
            form_link=f"http://127.0.0.1:5000/fill_form/{template_id}",
            created_by=current_user.role,
            creator=current_user.username
        )

        db.session.add(new_form)
        db.session.commit()

        # Copy questions and options associated with the template
        for old_question in template_to_copy.questions:
            new_question = Question(
                question_text=old_question.question_text,
                question_type=old_question.question_type,
                char_limit=old_question.char_limit,
                mandatory=old_question.mandatory,
                form_id=new_form.id
            )

            db.session.add(new_question)
            db.session.commit()

            for old_option in old_question.options:
                new_option = Option(
                    option_text=old_option.option_text,
                    question_id=new_question.id,
                    file_type=old_option.file_type,
                    max_file_size=old_option.max_file_size
                )

                db.session.add(new_option)
                db.session.commit()

        flash('Template copied successfully.', 'success')

        # Redirect to the preview page of the newly created form
        return redirect(url_for('preview_form', form_id=new_form.id))

    except Exception as e:
        flash(f'Error copying template: {str(e)}', 'error')
        return redirect(url_for('form_templates'))



# Route to delete a form


@app.route('/delete_form/<int:form_id>', methods=['POST'])
def delete_form(form_id):
    form_to_delete = Form.query.get(form_id)
    if form_to_delete:
        # Delete associated questions (this should cascade to options as well)
        for question in form_to_delete.questions:
            db.session.delete(question)
        db.session.delete(form_to_delete)
        db.session.commit()
        flash('Form deleted successfully', 'success')
    else:
        flash('Form not found', 'error')

    return redirect(url_for('saved_forms'))


app.static_folder = 'static'


UPLOAD_FOLDER = 'static/profile_pic'  # Folder to store uploaded profile pictures


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'avif'}

@app.route('/account_settings', methods=['GET', 'POST'])
def account_settings():
    user = get_current_user()  # Implement a function to get the current user
    
    message = None  # Initialize the message variable
    
    if request.method == 'POST':
        action = request.form['action']
        
        if action == 'username':
            new_username = request.form['username']
            user.username = new_username
            db.session.commit()
            message = "Username updated successfully."

        elif action == 'password':
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            
            # Check if the current password matches the user's current password (not recommended)
            if user.password == current_password:
                user.password = new_password
                db.session.commit()
                message = "Password updated successfully."
            else:
                message = "Incorrect password. Password not changed."
        
        elif action == 'email':
            new_email = request.form['email']
            user.email = new_email
            db.session.commit()
            message = "Email updated successfully."
        
        elif action == 'profile_picture':
            if 'profile_picture' not in request.files:
               message = "No file part"
            else:
                file = request.files['profile_picture']
                
                if file.filename == '':
                   message = "No selected file"
                elif file and allowed_file(file.filename):
                  filename = secure_filename(file.filename)
            # Update the file path to use the updated UPLOAD_FOLDER
                  file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                  user.profile_picture = filename
                  db.session.commit()
                  message = "Profile picture updated successfully."
                else:
                  message = "Invalid file format"

    # Render the account settings page with the current user's data and the message
    return render_template('account_settings.html', user=user, message=message)

# Define the get_current_user() function as previously shown in the previous response

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to update the email
@app.route('/edit_email', methods=['POST'])
def edit_email():
    new_email = request.form['email']
    user = get_current_user()  # Implement a function to get the current user

    # Update the email in the database
    user.email = new_email

    try:
        db.session.commit()
        return "Email updated successfully."
    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}"

# Route to update the username
@app.route('/edit_username', methods=['POST'])
def edit_username():
    new_username = request.form['username']
    user = get_current_user()  # Implement a function to get the current user

    # Update the username in the database
    user.username = new_username

    try:
        db.session.commit()
        return "Username updated successfully."
    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}"
    
@app.route('/change_password', methods=['POST'])
def change_password():
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    user = get_current_user()  # Implement a function to get the current user

    # Check if the current password matches the user's current password (not recommended)
    if user.password == current_password:
        user.password = new_password
        db.session.commit()
        return "Password updated successfully."
    else:
        return "Incorrect password. Password not changed."

@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if 'profile_picture' not in request.files:
        return "No file part"

    file = request.files['profile_picture']

    if file.filename == '':
        return "No selected file"

    if file and allowed_file(file.filename):
        # Generate a unique filename for the uploaded file
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + '_' + filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        # Update the profile_picture column in the database with the unique filename
        user = get_current_user()  # Implement a function to get the current user
        user.profile_picture = unique_filename
        db.session.commit()

        return "Profile picture updated successfully."
    else:
        return "Invalid file format"


 
@app.route('/preview_form/<int:form_id>')
def preview_form(form_id):
    # Retrieve the most recently created form with its associated questions and options
    form = Form.query.filter_by(id=form_id).first()

    # Get the current user
    current_user = get_current_user()

    # Read the country codes CSV
    country_codes_df = pd.read_csv(os.path.join(base_dir, 'static/csv/country-codes.csv'), usecols=['Country', 'Code'])
    country_codes = country_codes_df.to_dict(orient='records')

    if form:
        return render_template(
            'preview_form.html',
            form=form,
            current_user=current_user,
            countries=countries_df.to_dict(orient='records'),
            states=states_df.to_dict(orient='records'),
            cities=cities_df.to_dict(orient='records'),
            country_codes=country_codes  # Pass country codes to the template
        )
    else:
        # Handle the case where the form with the specified ID does not exist
        return render_template('error.html', message='Form not found')


@app.route('/states/<country_id>')
def get_states(country_id):
    # Filter states based on the selected country
    filtered_states = states_df[states_df['country_id'] == int(country_id)].to_dict(orient='records')
    return {'states': filtered_states}

@app.route('/cities/<state_name>')
def get_cities(state_name):
    # Filter cities based on the selected state_name
    filtered_cities = cities_df[cities_df['state_name'] == state_name].to_dict(orient='records')
    return {'cities': filtered_cities}







# Route to handle the update user information form submission
@app.route('/update_user_info', methods=['POST'])
def update_user_info():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']

    # Check if the passwords match
    if password != confirm_password:
        flash('Passwords do not match. Please try again.', 'error')
        return redirect(url_for('edit_user_info'))

    # Update the user's information in the session (we will implement this properly)
    session['username'] = username
    session['email'] = email

    flash('User information updated successfully.', 'success')
    return redirect(url_for('user_info'))


@app.route('/guest_profile')
def guest_profile():
    return render_template('guest_profile.html')

@app.route('/submit_response/<int:form_id>', methods=['POST'])
def submit_response(form_id):
    if request.method == 'POST':
        # Retrieve form data from the request
        data = request.form.to_dict()
        
        # Process and store the form response data (e.g., in the database)
        # Replace this with your code to handle form responses

        # Redirect to the submission confirmation page
        return render_template('submit_response.html')
    






@app.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
def delete_user(user_id):
   user_to_delete = users.query.get(user_id)
   if user_to_delete:
        
        
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('user deleted successfully', 'success')
   else:
        flash('user not found', 'error')
    
   return redirect(url_for('admin_users'))

@app.route('/contact_us', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message_text = request.form['message']

        new_message = Message(name=name, email=email, message=message_text)
        db.session.add(new_message)
        db.session.commit()

        flash('Your message has been sent successfully!', 'success')
        flash(f'We will contact you soon through the given email: {email}', 'info')

        return redirect(url_for('contact_us'))

    return render_template('contact_us.html')
@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/view_messages')
def view_messages():
    messages = Message.query.order_by(Message.timestamp.desc()).all()
    return render_template('view_messages.html', messages=messages)

    
@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        session.pop('user_id')
        flash('You have been successfully logged out.', 'success')
    else:
        flash('You are not logged in.', 'info')
    return redirect(url_for('home'))
# we will add more routes for other features like form sharing options, user activity, etc.





if __name__ == '__main__':

    app.run(debug=True)
