from django import forms
from .models import UserProfile

class RegistrationForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['login', 'password', 'tabel_raqami']
        widgets = {
            'password': forms.PasswordInput(), # Parol yulduzcha bo'lib ko'rinishi uchun
        }