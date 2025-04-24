from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    identifier = StringField('Username/Email/Phone', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Register')

class AddGreenhouseForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    location = StringField('Location')
    description = StringField('Description')
    submit = SubmitField('Add Greenhouse')

class AlertSettingsForm(FlaskForm):
    submit = SubmitField('Save Changes')