# accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model, password_validation

User = get_user_model()

class PatientSignUpForm(UserCreationForm):
    """
    Public registration form: only creates patients.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class':'form-control','placeholder':'Email'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Username'})
    )
    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Password'}),
        help_text=password_validation.password_validators_help_text_html()
    )
    password2 = forms.CharField(
        label='Confirm Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Confirm Password'})
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'patient'
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """
    Email‐based login form.
    """
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class':'form-control','placeholder':'Email'})
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Password'})
    )
