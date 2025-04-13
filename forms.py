from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    name = StringField("Emri", validators=[DataRequired()])
    role = SelectField("Fermer apo konsumator?", choices=("Fermer", 'Konsumator'), default="Konsumator")
    submit = SubmitField("Sign Up")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class AddProductForm(FlaskForm):
    name = StringField("Emri i produktit", validators=[DataRequired()])
    description = StringField("Pershkrimi i produktit", validators=[DataRequired()])
    price = IntegerField("Çmimi", validators=[DataRequired()])
    category = SelectField("Kategoria", choices=("Produkte bulmeti", "Produkte shtazore", "Fruta", "Perime", "Pije", "Të tjera"))
    submit = SubmitField("Shto")
